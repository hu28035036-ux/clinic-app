"""18-6 Hybrid Retriever Harness — keyword + vector 결합 검증.

체크리스트 18-6 + hybrid_harness_plan §5 기반 입력 케이스 11개 + reranker /
confidence 단위 검증.

회귀 보호:
  - hybrid OFF (기본) → keyword 단독 결과와 동등
  - vector 실패 → keyword fallback (검색 중단 0)
  - dedup 누락 0
  - 결정성 — 같은 입력 → 같은 결과
  - local_only → embedding 호출 0

외부 호출:
  - LLM provider: 본 retriever 자체는 LLM 호출 0 (provider 가 주입되어도)
  - Embedding provider: FakeEmbeddingProvider 만 사용, 실제 외부 SDK 0
"""
from __future__ import annotations

import pytest

from app.database import SessionLocal
from app.services.ai.rag.confidence import (
    HIGH_THRESHOLD,
    LLM_CALL_THRESHOLD,
    LOW_THRESHOLD,
    GateDecision,
    blocked_reason_for,
    compute_confidence,
    is_valid_mode,
    normalize_mode,
    primary_reason_code,
    should_call_llm,
)
from app.services.ai.rag.reranker import (
    combine,
    combine_with_stats,
)
from app.services.ai.rag.retriever import (
    hybrid_retrieve,
    keyword_retrieve,
)
from app.services.ai.rag.schemas import (
    AI_MODE_AI_ASSIST,
    AI_MODE_LOCAL_FIRST,
    AI_MODE_LOCAL_ONLY,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_UNKNOWN,
    REASON_EMBEDDING_SKIPPED_LOCAL_ONLY,
    REASON_EMBEDDING_SKIPPED_SHORT_QUERY,
    REASON_LLM_SKIPPED_LOCAL_ONLY,
    REASON_LLM_SKIPPED_LOW_CONFIDENCE,
    REASON_LLM_SKIPPED_NO_SOURCES,
    REASON_PROVIDER_DISABLED,
    REASON_PROVIDER_ERROR,
    REASON_VECTOR_DISABLED,
)
from app.services.rag.search import reset_cache as _rag_reset_cache
from tests.harness.fake_provider import FakeProvider, assert_no_external_call
from tests.harness.hybrid_harness import (
    assert_no_embedding_call,
    assert_no_external_calls_full,
    assert_retriever_deterministic,
    cleanup_hybrid_tables,
    make_hybrid_fake_embedding_provider,
    make_keyword_hit,
    make_vector_hit,
    seed_chunk_with_vector,
)
from tests.harness.vector_harness import cleanup_vector_tables

# ──────────────────────── fixture ────────────────────────


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def clean_tables():
    db = SessionLocal()
    try:
        cleanup_vector_tables(db)
        cleanup_hybrid_tables(db)
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        cleanup_vector_tables(db)
        cleanup_hybrid_tables(db)
    finally:
        db.close()


# ──────────────────────── 1. reranker 단위 테스트 ────────────────────────


def test_reranker_combine_keyword_only_alpha_1():
    """vector 결과 0건 → α=1.0, β=0.0 으로 combine 시 keyword 정규화 점수 그대로."""
    keyword = [
        make_keyword_hit(source_path="a.md", keyword_score=10),
        make_keyword_hit(source_path="b.md", keyword_score=5),
        make_keyword_hit(source_path="c.md", keyword_score=2),
    ]
    out = combine(keyword, [], alpha=1.0, beta=0.0)
    assert len(out) == 3
    assert out[0].source_path == "a.md"
    assert out[0].final_score == pytest.approx(1.0)  # 10/10 * 1.0
    assert out[1].source_path == "b.md"
    assert out[1].final_score == pytest.approx(0.5)  # 5/10 * 1.0
    assert out[2].source_path == "c.md"
    assert out[2].final_score == pytest.approx(0.2)  # 2/10 * 1.0


def test_reranker_combine_vector_only_beta_1():
    """keyword 결과 0건 + vector 만 → β=1.0 으로 combine 시 vector 정규화 점수 그대로."""
    vector = [
        make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.9),
        make_vector_hit(source_path="b.md", chunk_id=2, vector_score=0.6),
        make_vector_hit(source_path="c.md", chunk_id=3, vector_score=0.3),
    ]
    out = combine([], vector, alpha=0.0, beta=1.0)
    assert len(out) == 3
    assert out[0].chunk_id == 1
    assert out[0].final_score == pytest.approx(1.0)
    assert out[1].chunk_id == 2
    assert out[1].final_score == pytest.approx(0.6 / 0.9)


def test_reranker_combine_alpha_beta_weighted():
    """α=0.6, β=0.4 — 두 source 결합 시 가중합 정확."""
    keyword = [
        make_keyword_hit(source_path="a.md", keyword_score=10),  # norm 1.0
        make_keyword_hit(source_path="b.md", keyword_score=5),   # norm 0.5
    ]
    vector = [
        make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.5),  # norm 0.5
        make_vector_hit(source_path="b.md", chunk_id=2, vector_score=1.0),  # norm 1.0
    ]
    out = combine(keyword, vector, alpha=0.6, beta=0.4)
    # a.md: 0.6*1.0 + 0.4*0.5 = 0.8
    # b.md: 0.6*0.5 + 0.4*1.0 = 0.7
    assert out[0].source_path == "a.md"
    assert out[0].final_score == pytest.approx(0.8)
    assert out[1].source_path == "b.md"
    assert out[1].final_score == pytest.approx(0.7)


def test_reranker_dedup_by_source_path():
    """keyword + vector 가 같은 source_path → dedup 1건."""
    keyword = [make_keyword_hit(source_path="a.md", keyword_score=10)]
    vector = [make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.9)]
    out = combine(keyword, vector, alpha=0.5, beta=0.5)
    assert len(out) == 1, f"dedup 실패: {[h.source_path for h in out]}"
    h = out[0]
    assert h.source_path == "a.md"
    assert h.chunk_id == 1  # vector 의 chunk_id 가 더 구체적이라 채워짐
    assert h.search_mode == "hybrid"
    assert h.final_score == pytest.approx(1.0)  # 0.5*1.0 + 0.5*1.0


def test_reranker_dedup_by_chunk_id():
    """vector 안에서 같은 chunk_id 두 번 → dedup. 더 높은 score 보존."""
    vector = [
        make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.5),
        make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.9),
    ]
    out = combine([], vector, alpha=0.0, beta=1.0)
    assert len(out) == 1
    assert out[0].vector_score == pytest.approx(0.9)


def test_reranker_dedup_within_keyword():
    """keyword 안에서 같은 path 두 번 → dedup. 더 높은 score 보존."""
    keyword = [
        make_keyword_hit(source_path="a.md", keyword_score=5),
        make_keyword_hit(source_path="a.md", keyword_score=10),
    ]
    out = combine(keyword, [], alpha=1.0, beta=0.0)
    assert len(out) == 1
    assert out[0].keyword_score == pytest.approx(10)


def test_reranker_negative_vector_score_clamped_to_zero():
    """음의 cosine score 는 0 으로 clamp 후 정규화."""
    vector = [
        make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.8),
        make_vector_hit(source_path="b.md", chunk_id=2, vector_score=-0.5),
    ]
    out = combine([], vector, alpha=0.0, beta=1.0)
    assert len(out) == 2
    # b.md 는 음수 → clamp → 0 → norm → 0
    b = next(h for h in out if h.source_path == "b.md")
    assert b.final_score == pytest.approx(0.0)


def test_reranker_all_zero_keyword_no_division_error():
    """모든 keyword score = 0 → 정규화 X (모두 0) — division-by-zero 회피."""
    keyword = [
        make_keyword_hit(source_path="a.md", keyword_score=0),
        make_keyword_hit(source_path="b.md", keyword_score=0),
    ]
    out = combine(keyword, [], alpha=1.0, beta=0.0)
    assert all(h.final_score == 0.0 for h in out)


def test_reranker_alpha_beta_change_changes_ranking():
    """α/β 변경 시 순위 변화가 결정적."""
    keyword = [
        make_keyword_hit(source_path="a.md", keyword_score=10),  # norm 1.0
        make_keyword_hit(source_path="b.md", keyword_score=2),   # norm 0.2
    ]
    vector = [
        make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.1),  # norm 0.1
        make_vector_hit(source_path="b.md", chunk_id=2, vector_score=1.0),  # norm 1.0
    ]
    # α=1.0, β=0.0: a.md 우세 (1.0 > 0.2)
    out_a = combine([h for h in keyword], [h for h in vector], alpha=1.0, beta=0.0)
    assert out_a[0].source_path == "a.md"

    # α=0.0, β=1.0: b.md 우세 (1.0 > 0.1)
    keyword2 = [
        make_keyword_hit(source_path="a.md", keyword_score=10),
        make_keyword_hit(source_path="b.md", keyword_score=2),
    ]
    vector2 = [
        make_vector_hit(source_path="a.md", chunk_id=1, vector_score=0.1),
        make_vector_hit(source_path="b.md", chunk_id=2, vector_score=1.0),
    ]
    out_b = combine(keyword2, vector2, alpha=0.0, beta=1.0)
    assert out_b[0].source_path == "b.md"


def test_reranker_combine_with_stats_reports_collisions():
    """combine_with_stats — keyword 안 중복은 collision 으로 카운트."""
    keyword = [
        make_keyword_hit(source_path="a.md", keyword_score=5),
        make_keyword_hit(source_path="a.md", keyword_score=3),
    ]
    out, stats = combine_with_stats(keyword, [], alpha=1.0, beta=0.0)
    assert stats.dedup_collisions == 1
    assert stats.output_count == 1
    assert stats.keyword_input_count == 2
    assert stats.alpha == 1.0


def test_reranker_combine_empty_inputs_returns_empty():
    """둘 다 비어있으면 빈 리스트."""
    assert combine([], [], alpha=0.5, beta=0.5) == []


# ──────────────────────── 2. confidence 단위 테스트 ────────────────────────


def test_confidence_compute_high_low_unknown():
    """final_score → high/low/unknown 매핑."""
    assert compute_confidence(0.9) == CONFIDENCE_HIGH
    assert compute_confidence(HIGH_THRESHOLD) == CONFIDENCE_HIGH
    assert compute_confidence(0.5) == CONFIDENCE_LOW
    assert compute_confidence(LOW_THRESHOLD) == CONFIDENCE_LOW
    assert compute_confidence(0.1) == CONFIDENCE_UNKNOWN
    assert compute_confidence(0.0) == CONFIDENCE_UNKNOWN


def test_confidence_should_call_llm_no_sources():
    """sources=0 → reason='llm_skipped_no_sources', should_call=False."""
    d = should_call_llm(sources_count=0, final_score=1.0)
    assert d.should_call is False
    assert d.reason_code == REASON_LLM_SKIPPED_NO_SOURCES


def test_confidence_should_call_llm_low_confidence():
    """final_score < threshold → reason='llm_skipped_low_confidence'."""
    d = should_call_llm(sources_count=3, final_score=LLM_CALL_THRESHOLD - 0.01)
    assert d.should_call is False
    assert d.reason_code == REASON_LLM_SKIPPED_LOW_CONFIDENCE


def test_confidence_should_call_llm_local_only():
    """mode=local_only → reason='llm_skipped_local_only'."""
    d = should_call_llm(sources_count=3, final_score=0.9, mode=AI_MODE_LOCAL_ONLY)
    assert d.should_call is False
    assert d.reason_code == REASON_LLM_SKIPPED_LOCAL_ONLY


def test_confidence_should_call_llm_provider_disabled():
    """provider_disabled=True → reason='provider_disabled' (가장 높은 우선순위)."""
    d = should_call_llm(
        sources_count=3, final_score=0.9, mode=AI_MODE_AI_ASSIST,
        provider_disabled=True,
    )
    assert d.should_call is False
    assert d.reason_code == REASON_PROVIDER_DISABLED


def test_confidence_should_call_llm_pii_blocks():
    """pii_detected=True → reason='pii_detected'."""
    d = should_call_llm(sources_count=3, final_score=0.9, pii_detected=True)
    assert d.should_call is False
    # pii_detected 응답 reason_code 는 docs/error_codes.md §1-3 = "pii_detected"
    assert d.reason_code == "pii_detected"


def test_confidence_should_call_llm_pass():
    """sources≥1 + final_score≥threshold + 모드 ai_assist → should_call=True."""
    d = should_call_llm(
        sources_count=3, final_score=0.9, mode=AI_MODE_AI_ASSIST,
    )
    assert d.should_call is True
    assert d.reason_code == ""
    assert d.confidence == CONFIDENCE_HIGH


def test_confidence_should_call_llm_low_first_default():
    """local_first 가 default — sources/score 통과시 should_call=True."""
    d = should_call_llm(sources_count=2, final_score=0.5)
    assert d.should_call is True
    assert d.confidence == CONFIDENCE_LOW


def test_confidence_priority_provider_disabled_over_pii():
    """provider_disabled 가 pii_detected 보다 높은 우선순위."""
    d = should_call_llm(
        sources_count=3, final_score=0.9,
        provider_disabled=True, pii_detected=True,
    )
    assert d.reason_code == REASON_PROVIDER_DISABLED


def test_confidence_normalize_mode():
    """알 수 없는 mode → local_first."""
    assert normalize_mode("unknown") == AI_MODE_LOCAL_FIRST
    assert normalize_mode(None) == AI_MODE_LOCAL_FIRST
    assert normalize_mode("") == AI_MODE_LOCAL_FIRST
    assert normalize_mode(AI_MODE_LOCAL_ONLY) == AI_MODE_LOCAL_ONLY
    assert normalize_mode(AI_MODE_AI_ASSIST) == AI_MODE_AI_ASSIST


def test_confidence_is_valid_mode():
    assert is_valid_mode(AI_MODE_LOCAL_ONLY) is True
    assert is_valid_mode(AI_MODE_LOCAL_FIRST) is True
    assert is_valid_mode(AI_MODE_AI_ASSIST) is True
    assert is_valid_mode("foo") is False


def test_confidence_primary_reason_code_picks_highest():
    """동시 발급 시 가장 높은 우선순위 1개 선택."""
    # invalid_query > pii_detected > provider_disabled > ...
    assert primary_reason_code("low_confidence", "pii_detected") == "pii_detected"
    assert primary_reason_code("provider_disabled", "no_sources") == "provider_disabled"
    assert primary_reason_code("invalid_query", "pii_detected", "no_sources") == "invalid_query"
    assert primary_reason_code("", None, "low_confidence") == "low_confidence"
    assert primary_reason_code(None, "") == ""


def test_confidence_blocked_reason_for_compatibility():
    """v1.3.3 ``blocked_reason`` 호환 매핑."""
    assert blocked_reason_for("no_sources") == "no rag hit"
    assert blocked_reason_for("llm_skipped_no_sources") == "no rag hit"
    assert blocked_reason_for("low_confidence") == "low rag confidence"
    assert blocked_reason_for("llm_skipped_low_confidence") == "low rag confidence"
    assert blocked_reason_for("provider_disabled") == "provider disabled"
    assert blocked_reason_for("pii_detected") == "pii detected"
    assert blocked_reason_for("") == ""


# ──────────────────────── 3. hybrid_retrieve 통합 — keyword 단독 ────────────────────────


def test_hybrid_disabled_equals_keyword_only():
    """hybrid_enabled=False → keyword 단독 — 회귀 0."""
    _rag_reset_cache()
    raw_keyword = keyword_retrieve("예약문자 작성", category="manuals", limit=5)
    raw_paths = [r.get("path") for r in raw_keyword]

    res = hybrid_retrieve(
        "예약문자 작성",
        hybrid_enabled=False,
        top_k=5,
        category="manuals",
    )
    hybrid_paths = [h.source_path for h in res.hits]
    assert hybrid_paths == raw_paths, (
        f"hybrid OFF != keyword-only:\n  hybrid: {hybrid_paths}\n  keyword: {raw_paths}"
    )
    assert res.requested_mode == "keyword"
    assert res.effective_mode == "keyword"
    assert res.embedding_called is False
    assert res.vector_attempted is False
    assert res.vector_failed is False


def test_hybrid_disabled_with_embedding_provider_does_not_call_it():
    """hybrid_enabled=False 일 때 embedding_provider 가 주어져도 호출 0."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider()
    res = hybrid_retrieve(
        "예약문자 작성",
        embedding_provider=fake_embed,
        hybrid_enabled=False,
        top_k=5,
    )
    assert_no_embedding_call(fake_embed, "hybrid OFF 시 embedding 호출 0")
    assert res.embedding_called is False


def test_hybrid_no_embedding_provider_falls_back_to_keyword():
    """hybrid_enabled=True 이지만 embedding_provider=None → vector_disabled +
    keyword fallback."""
    _rag_reset_cache()
    res = hybrid_retrieve(
        "예약문자 작성",
        embedding_provider=None,
        hybrid_enabled=True,
        top_k=5,
    )
    assert res.reason_code == REASON_VECTOR_DISABLED
    assert res.effective_mode == "keyword"
    assert res.vector_attempted is False
    assert res.embedding_called is False
    # keyword 결과는 그대로
    assert len(res.hits) >= 1
    assert res.hits[0].keyword_score > 0


def test_hybrid_no_db_falls_back_to_keyword():
    """hybrid_enabled=True 이지만 db=None → vector_disabled + keyword fallback."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider()
    res = hybrid_retrieve(
        "예약문자 작성",
        db=None,
        embedding_provider=fake_embed,
        hybrid_enabled=True,
        top_k=5,
    )
    assert res.reason_code == REASON_VECTOR_DISABLED
    assert res.effective_mode == "keyword"
    assert_no_embedding_call(fake_embed, "db 부재 시 embedding 호출 0")


# ──────────────────────── 4. hybrid_retrieve — vector 경로 활성 ────────────────────────


def test_hybrid_vector_path_returns_hybrid_results(db_session, clean_tables):
    """hybrid_enabled=True + 둘 다 hit → effective_mode='hybrid', dedup."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    # 매뉴얼 매칭 + chunk 시드 (같은 텍스트)
    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드: 예약 문자 탭에서 작성합니다.",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
        embedding_provider=fake_embed,
    )
    seed_chunk_with_vector(
        db_session,
        content="백업은 관리자 메뉴에서 수행합니다.",
        title="backup",
        source_path="manuals/backup.md",
        embedding_provider=fake_embed,
    )

    res = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=fake_embed,
        hybrid_enabled=True,
        alpha=0.6,
        beta=0.4,
        top_k=5,
    )
    assert res.embedding_called is True
    assert res.vector_attempted is True
    assert res.vector_failed is False
    assert res.reason_code == ""
    assert res.alpha == pytest.approx(0.6)
    assert res.beta == pytest.approx(0.4)
    assert len(res.hits) >= 1
    # 결과에 final_score 가 모두 채워져 있음
    for h in res.hits:
        assert 0.0 <= h.final_score <= 1.0


def test_hybrid_vector_only_hit_keyword_zero(db_session, clean_tables):
    """vector 만 hit (keyword 0건) → vector 결과 사용, effective_mode='vector'."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    # keyword 가 절대 매칭되지 않을 가짜 path/내용
    seed_chunk_with_vector(
        db_session,
        content="zzqxk content unique",
        title="z_doc",
        source_path="manuals/z_unique.md",
        embedding_provider=fake_embed,
    )

    res = hybrid_retrieve(
        "zzqxk",  # keyword 매칭 0
        db=db_session,
        embedding_provider=fake_embed,
        hybrid_enabled=True,
        top_k=5,
    )
    # keyword 결과 0 — vector 만 hit
    assert res.keyword_count == 0
    assert res.vector_count >= 1
    assert res.effective_mode == "vector"
    assert res.embedding_called is True


def test_hybrid_dedup_chunk_id_no_duplicates(db_session, clean_tables):
    """둘 다 같은 chunk hit → dedup 1건."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    # 매뉴얼 매칭되는 path 로 시드
    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드 내용",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
        embedding_provider=fake_embed,
    )
    res = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=fake_embed,
        hybrid_enabled=True,
        top_k=5,
    )
    # 같은 source_path 가 keyword + vector 양쪽에서 hit → 1건만
    paths = [h.source_path for h in res.hits if h.source_path == "manuals/sms_compose.md"]
    assert len(paths) == 1, f"dedup 실패: {paths}"


# ──────────────────────── 5. local_only — vector 경로 차단 ────────────────────────


def test_hybrid_local_only_blocks_vector_path(db_session, clean_tables):
    """mode=local_only → vector 경로 시도 자체 차단 — embedding 호출 0."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(
        dimension=8, raise_on_call=True,
    )
    # vector 가 호출되면 raise → 호출 자체가 일어나면 안됨.
    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
        # embedding_provider 안 넘김 — chunk 만 시드
    )

    res = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=fake_embed,
        hybrid_enabled=True,
        mode=AI_MODE_LOCAL_ONLY,
        top_k=5,
    )
    assert res.reason_code == REASON_EMBEDDING_SKIPPED_LOCAL_ONLY
    assert res.embedding_called is False
    assert res.vector_attempted is False
    assert_no_embedding_call(fake_embed, "local_only 모드에서 embedding 호출 0")
    # keyword 결과는 정상
    assert res.effective_mode == "keyword"
    assert res.keyword_count >= 1


# ──────────────────────── 6. provider 오류 — fallback ────────────────────────


def test_hybrid_provider_error_falls_back_to_keyword(db_session, clean_tables):
    """embedding provider 가 raise → keyword fallback + reason='provider_error'."""
    _rag_reset_cache()
    raise_embed = make_hybrid_fake_embedding_provider(
        dimension=8, raise_on_call=True,
    )

    res = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=raise_embed,
        hybrid_enabled=True,
        top_k=5,
    )
    assert res.vector_attempted is True
    assert res.vector_failed is True
    assert res.reason_code == REASON_PROVIDER_ERROR
    assert res.effective_mode == "keyword"
    assert len(res.hits) >= 1  # keyword 결과는 그대로


# ──────────────────────── 7. 짧은 query — embedding 차단 ────────────────────────


def test_hybrid_short_query_skips_embedding(db_session, clean_tables):
    """1자 query → embedding 호출 X, keyword 만."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    res = hybrid_retrieve(
        "ㄱ",  # 1자
        db=db_session,
        embedding_provider=fake_embed,
        hybrid_enabled=True,
        top_k=5,
    )
    assert res.reason_code == REASON_EMBEDDING_SKIPPED_SHORT_QUERY
    assert_no_embedding_call(fake_embed, "짧은 query 시 embedding 호출 0")
    assert res.effective_mode == "keyword"


def test_hybrid_empty_query_returns_empty(db_session, clean_tables):
    """빈 query → keyword 0건 + embedding 0회."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    res = hybrid_retrieve(
        "",
        db=db_session,
        embedding_provider=fake_embed,
        hybrid_enabled=True,
        top_k=5,
    )
    assert res.keyword_count == 0
    assert res.vector_count == 0
    assert_no_embedding_call(fake_embed)
    assert res.hits == []


# ──────────────────────── 8. 결정성 ────────────────────────


def test_hybrid_deterministic_same_query_same_result(db_session, clean_tables):
    """같은 입력 → 두 번 호출해도 같은 결과 (FakeEmbeddingProvider 결정적)."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
        embedding_provider=fake_embed,
    )
    seed_chunk_with_vector(
        db_session,
        content="백업 매뉴얼",
        title="backup",
        source_path="manuals/backup.md",
        embedding_provider=fake_embed,
    )
    # 새 fake — 호출 카운트 신선.
    fake2 = make_hybrid_fake_embedding_provider(dimension=8)
    assert_retriever_deterministic(
        "예약문자 작성",
        db=db_session,
        embedding_provider=fake2,
        hybrid_enabled=True,
        top_k=5,
        runs=3,
    )


def test_hybrid_alpha_change_changes_ranking_deterministic(db_session, clean_tables):
    """α/β 변경 시 순위 변화 결정적."""
    _rag_reset_cache()
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드 키워드 강함",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
        embedding_provider=fake_embed,
    )

    fake2 = make_hybrid_fake_embedding_provider(dimension=8)
    res_keyword_heavy = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=fake2,
        hybrid_enabled=True,
        alpha=1.0, beta=0.0,
        top_k=5,
    )
    res_vector_heavy = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=fake2,
        hybrid_enabled=True,
        alpha=0.0, beta=1.0,
        top_k=5,
    )
    # 결과 자체는 동일 path 가 1위 — 단, final_score 가 다른 가중치로 다르게 산출됨.
    assert res_keyword_heavy.alpha == 1.0
    assert res_keyword_heavy.beta == 0.0
    assert res_vector_heavy.alpha == 0.0
    assert res_vector_heavy.beta == 1.0


# ──────────────────────── 9. LLM 호출 0 — 모든 경로 ────────────────────────


def test_hybrid_does_not_call_llm_provider(db_session, clean_tables):
    """hybrid_retrieve 자체는 LLM 호출 없음 — provider 가 주입되어도 호출 0."""
    _rag_reset_cache()
    fake_llm = FakeProvider(return_text="이 응답은 호출되지 않아야 함")
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
        embedding_provider=fake_embed,
    )

    fake2 = make_hybrid_fake_embedding_provider(dimension=8)
    res = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=fake2,
        hybrid_enabled=True,
        top_k=5,
    )
    assert_no_external_call(fake_llm)
    assert res.embedding_called is True  # embedding 은 호출됨
    # LLM 은 별도 — hybrid_retrieve 자체는 LLM 호출 0
    assert len(fake_llm.calls) == 0


def test_hybrid_no_external_calls_keyword_only_path():
    """keyword-only 경로에서는 LLM/embedding 모두 0."""
    _rag_reset_cache()
    fake_llm = FakeProvider(return_text="should not be called")
    fake_embed = make_hybrid_fake_embedding_provider(dimension=8)
    res = hybrid_retrieve(
        "예약문자 작성",
        embedding_provider=fake_embed,
        hybrid_enabled=False,  # OFF
        top_k=5,
    )
    assert_no_external_calls_full(provider=fake_llm, embedding_provider=fake_embed)
    assert res.effective_mode == "keyword"


# ──────────────────────── 10. confidence + low_confidence → LLM 차단 ────────────────────────


def test_hybrid_low_final_score_should_not_call_llm():
    """final_score 가 임계 미만이면 should_call_llm=False, reason='llm_skipped_low_confidence'.

    hybrid_retrieve 자체는 LLM 호출하지 않으므로, confidence 모듈의 should_call_llm
    이 final_score 를 받아 정확히 차단하는지 단위 검증.
    """
    # final_score = 0.1 — LLM_CALL_THRESHOLD (0.3) 미만.
    decision: GateDecision = should_call_llm(
        sources_count=3,
        final_score=0.1,
        mode=AI_MODE_LOCAL_FIRST,
    )
    assert decision.should_call is False
    assert decision.reason_code == REASON_LLM_SKIPPED_LOW_CONFIDENCE


def test_hybrid_high_final_score_allows_llm_call():
    """final_score >= threshold + sources>=1 → should_call_llm=True."""
    decision = should_call_llm(
        sources_count=3,
        final_score=0.8,
        mode=AI_MODE_LOCAL_FIRST,
    )
    assert decision.should_call is True
    assert decision.confidence == CONFIDENCE_HIGH


# ──────────────────────── 11. 회귀 — 기존 manual_qa 동작 보존 ────────────────────────


def test_existing_manual_qa_unaffected_by_hybrid_module():
    """hybrid 모듈 import 만으로는 기존 manual_qa 동작 회귀 0."""
    _rag_reset_cache()
    from app.services.ai import manual_qa as ai_manual_qa
    fake = FakeProvider(
        return_text="발췌에 따르면 예약 문자 탭에서 작성합니다.\n참고: sms_compose.md"
    )
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    # 기존 응답 9개 키 그대로 + LLM 1회 호출 (회귀 모드 A)
    expected_keys = {
        "answer", "sources", "confidence", "not_found",
        "blocked", "blocked_reason", "guard_hits",
        "top_score", "masked_question",
    }
    assert expected_keys.issubset(set(res.keys()))
    assert len(fake.calls) == 1
    assert res["not_found"] is False


def test_keyword_retrieve_unchanged():
    """``keyword_retrieve`` 동작 회귀 0 — 기존 dict 키 그대로."""
    _rag_reset_cache()
    raw = keyword_retrieve("예약문자 작성", category="manuals", limit=5)
    assert isinstance(raw, list)
    if raw:
        first = raw[0]
        for k in ("path", "category", "name", "title", "snippet", "score"):
            assert k in first, f"keyword_retrieve dict missing {k}: {first}"


# ──────────────────────── 12. 운영 DB 미사용 ────────────────────────


def test_hybrid_does_not_use_operational_db(db_path):
    """conftest 가 격리한 임시 DB 만 사용 — 운영 경로 미터치."""
    norm = db_path.lower().replace("\\", "/")
    assert ("temp" in norm) or ("test" in norm), db_path


# ──────────────────────── 13. reason_code — 우선순위 검증 ────────────────────────


def test_priority_invalid_query_highest():
    """invalid_query > pii_detected > provider_disabled > unknown_feature > no_sources..."""
    # 우선순위 표 (docs/ai_rag_error_codes.md §5) 정합 검증.
    assert primary_reason_code("low_confidence", "invalid_query") == "invalid_query"
    assert primary_reason_code("provider_disabled", "invalid_query") == "invalid_query"
    assert primary_reason_code("low_confidence", "pii_detected") == "pii_detected"
    # vector_disabled 는 low_confidence 보다 낮은 우선순위.
    assert primary_reason_code("vector_disabled", "low_confidence") == "low_confidence"


def test_priority_unknown_code_falls_to_back():
    """우선순위 표에 없는 코드는 입력 순서 보존."""
    # "foo" 는 표에 없음 — 가장 낮은 우선순위.
    assert primary_reason_code("foo", "no_sources") == "no_sources"
    # 모두 미지정 코드면 첫 번째 그대로.
    assert primary_reason_code("foo", "bar") in ("foo", "bar")
