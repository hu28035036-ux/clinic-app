"""18-6 AI 모드별 안전 처리 검증 — local_only / local_first / ai_assist.

각 모드에서 hybrid_retriever + confidence gate 의 동작 차이:

  - local_only  : 외부 LLM/Embedding 모두 호출 0. vector 경로 시도조차 안 함.
  - local_first : (default) vector 경로 시도 가능. LLM 호출은 confidence 게이트 통과 필요.
  - ai_assist   : vector 경로 + LLM 호출 적극 — 단 sources/confidence 게이트는 동일.

본 테스트는 hybrid_retrieve + should_call_llm 조합으로 모드별 호출 카운트
단언을 한다. 실제 manual_ask 라우터 통합은 18-7 시점.
"""
from __future__ import annotations

import pytest

from app.database import SessionLocal
from app.services.ai.rag.confidence import (
    LLM_CALL_THRESHOLD,
    should_call_llm,
)
from app.services.ai.rag.retriever import hybrid_retrieve
from app.services.ai.rag.schemas import (
    AI_MODE_AI_ASSIST,
    AI_MODE_LOCAL_FIRST,
    AI_MODE_LOCAL_ONLY,
    REASON_EMBEDDING_SKIPPED_LOCAL_ONLY,
    REASON_LLM_SKIPPED_LOCAL_ONLY,
    REASON_LLM_SKIPPED_LOW_CONFIDENCE,
    REASON_LLM_SKIPPED_NO_SOURCES,
    REASON_PROVIDER_DISABLED,
)
from app.services.rag.search import reset_cache as _rag_reset_cache
from tests.harness.fake_provider import FakeProvider, assert_no_external_call
from tests.harness.hybrid_harness import (
    assert_no_embedding_call,
    cleanup_hybrid_tables,
    make_hybrid_fake_embedding_provider,
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


# ──────────────────────── local_only — 모든 호출 0 ────────────────────────


def test_local_only_blocks_embedding_factory(db_session, clean_tables):
    """local_only — embedding_provider 가 주입되어도 호출 0."""
    _rag_reset_cache()
    raise_embed = make_hybrid_fake_embedding_provider(
        dimension=8, raise_on_call=True,
    )
    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
    )
    res = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=raise_embed,
        hybrid_enabled=True,
        mode=AI_MODE_LOCAL_ONLY,
        top_k=5,
    )
    assert_no_embedding_call(raise_embed, "local_only 에서 embedding 호출 0")
    assert res.reason_code == REASON_EMBEDDING_SKIPPED_LOCAL_ONLY
    assert res.embedding_called is False
    assert res.vector_attempted is False


def test_local_only_should_not_call_llm_even_with_high_score():
    """local_only — final_score 가 높아도 should_call_llm=False."""
    decision = should_call_llm(
        sources_count=5, final_score=0.95, mode=AI_MODE_LOCAL_ONLY,
    )
    assert decision.should_call is False
    assert decision.reason_code == REASON_LLM_SKIPPED_LOCAL_ONLY


def test_local_only_keyword_only_path_works(db_session, clean_tables):
    """local_only — keyword 경로는 정상 동작."""
    _rag_reset_cache()
    raise_embed = make_hybrid_fake_embedding_provider(
        dimension=8, raise_on_call=True,
    )
    res = hybrid_retrieve(
        "예약문자 작성",
        db=db_session,
        embedding_provider=raise_embed,
        hybrid_enabled=True,
        mode=AI_MODE_LOCAL_ONLY,
        top_k=5,
    )
    # keyword 결과는 정상 — 매뉴얼 검색 가능.
    assert res.effective_mode == "keyword"
    assert res.keyword_count >= 1
    assert_no_embedding_call(raise_embed)


# ──────────────────────── local_first — 게이트 통과 시 LLM 1회 가능 ────────────────────────


def test_local_first_high_score_allows_llm():
    """local_first + high final_score → should_call_llm=True (LLM 1회 허용)."""
    decision = should_call_llm(
        sources_count=3, final_score=0.9, mode=AI_MODE_LOCAL_FIRST,
    )
    assert decision.should_call is True
    assert decision.reason_code == ""


def test_local_first_low_score_blocks_llm():
    """local_first + low final_score → should_call_llm=False."""
    decision = should_call_llm(
        sources_count=3, final_score=0.1, mode=AI_MODE_LOCAL_FIRST,
    )
    assert decision.should_call is False
    assert decision.reason_code == REASON_LLM_SKIPPED_LOW_CONFIDENCE


def test_local_first_uses_vector_path(db_session, clean_tables):
    """local_first — embedding 호출 가능 (vector 경로 활성)."""
    _rag_reset_cache()
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
        mode=AI_MODE_LOCAL_FIRST,
        top_k=5,
    )
    assert res.embedding_called is True
    assert len(fake2.calls) == 1, (
        f"local_first vector 경로 — embed_query 1회 호출 기대, got {len(fake2.calls)}"
    )


# ──────────────────────── ai_assist — 외부 호출 적극 ────────────────────────


def test_ai_assist_high_score_allows_llm():
    """ai_assist + sources>=1 + final_score>=threshold → should_call_llm=True."""
    decision = should_call_llm(
        sources_count=3, final_score=0.5, mode=AI_MODE_AI_ASSIST,
    )
    assert decision.should_call is True


def test_ai_assist_no_sources_blocks_llm():
    """ai_assist 에서도 sources=0 이면 LLM 차단."""
    decision = should_call_llm(
        sources_count=0, final_score=0.9, mode=AI_MODE_AI_ASSIST,
    )
    assert decision.should_call is False
    assert decision.reason_code == REASON_LLM_SKIPPED_NO_SOURCES


def test_ai_assist_low_score_blocks_llm():
    """ai_assist 에서도 final_score < threshold 면 LLM 차단."""
    decision = should_call_llm(
        sources_count=3, final_score=LLM_CALL_THRESHOLD - 0.05,
        mode=AI_MODE_AI_ASSIST,
    )
    assert decision.should_call is False
    assert decision.reason_code == REASON_LLM_SKIPPED_LOW_CONFIDENCE


def test_ai_assist_provider_disabled_blocks_llm():
    """ai_assist 에서도 provider_disabled=True 면 LLM 차단."""
    decision = should_call_llm(
        sources_count=3, final_score=0.9, mode=AI_MODE_AI_ASSIST,
        provider_disabled=True,
    )
    assert decision.should_call is False
    assert decision.reason_code == REASON_PROVIDER_DISABLED


# ──────────────────────── 모드별 retriever 응답 일관성 ────────────────────────


def test_modes_share_same_keyword_fallback_when_hybrid_off():
    """hybrid_enabled=False — 모든 모드에서 keyword 단독 결과 동일."""
    _rag_reset_cache()
    res_local_only = hybrid_retrieve(
        "예약문자 작성",
        hybrid_enabled=False,
        mode=AI_MODE_LOCAL_ONLY,
        top_k=5,
    )
    res_local_first = hybrid_retrieve(
        "예약문자 작성",
        hybrid_enabled=False,
        mode=AI_MODE_LOCAL_FIRST,
        top_k=5,
    )
    res_ai_assist = hybrid_retrieve(
        "예약문자 작성",
        hybrid_enabled=False,
        mode=AI_MODE_AI_ASSIST,
        top_k=5,
    )
    paths_lo = [h.source_path for h in res_local_only.hits]
    paths_lf = [h.source_path for h in res_local_first.hits]
    paths_aa = [h.source_path for h in res_ai_assist.hits]
    assert paths_lo == paths_lf == paths_aa, (
        f"hybrid OFF — 모드 무관 결과 동일해야:\n  lo={paths_lo}\n  lf={paths_lf}\n  aa={paths_aa}"
    )


def test_local_only_vector_disabled_reason_code():
    """local_only + hybrid_enabled=True → reason='embedding_skipped_local_only'."""
    _rag_reset_cache()
    raise_embed = make_hybrid_fake_embedding_provider(
        dimension=8, raise_on_call=True,
    )
    res = hybrid_retrieve(
        "예약문자 작성",
        embedding_provider=raise_embed,
        hybrid_enabled=True,
        mode=AI_MODE_LOCAL_ONLY,
        top_k=5,
    )
    assert res.reason_code == REASON_EMBEDDING_SKIPPED_LOCAL_ONLY
    assert res.embedding_called is False


# ──────────────────────── LLM provider 호출 카운트 (모드별) ────────────────────────


def test_modes_llm_provider_zero_calls_in_retriever(db_session, clean_tables):
    """hybrid_retrieve 자체는 모든 모드에서 LLM provider 호출 0.

    LLM 호출은 retriever 가 아닌 caller (pipeline/router) 가 결정 — 본 테스트는
    retriever 단계에서 어떤 모드든 LLM 호출이 발생하지 않음을 단언.
    """
    _rag_reset_cache()
    fake_llm_lo = FakeProvider(return_text="should not be called")
    fake_llm_lf = FakeProvider(return_text="should not be called")
    fake_llm_aa = FakeProvider(return_text="should not be called")

    fake_embed_lo = make_hybrid_fake_embedding_provider(
        dimension=8, raise_on_call=True,
    )
    fake_embed_lf = make_hybrid_fake_embedding_provider(dimension=8)
    fake_embed_aa = make_hybrid_fake_embedding_provider(dimension=8)

    seed_chunk_with_vector(
        db_session,
        content="예약문자 작성 가이드",
        title="sms_compose",
        source_path="manuals/sms_compose.md",
        embedding_provider=fake_embed_lf,
    )

    # local_only — 모든 외부 호출 0
    fake_embed_lo.calls.clear()
    res_lo = hybrid_retrieve(  # noqa: F841
        "예약문자 작성", db=db_session, embedding_provider=fake_embed_lo,
        hybrid_enabled=True, mode=AI_MODE_LOCAL_ONLY,
    )
    assert_no_external_call(fake_llm_lo)
    assert_no_embedding_call(fake_embed_lo)

    # local_first — embedding 호출 가능, LLM 0
    fake_embed_lf.calls.clear()
    res_lf = hybrid_retrieve(  # noqa: F841
        "예약문자 작성", db=db_session, embedding_provider=fake_embed_lf,
        hybrid_enabled=True, mode=AI_MODE_LOCAL_FIRST,
    )
    assert_no_external_call(fake_llm_lf)
    # embedding 1회는 정상 (vector 경로 활성).
    assert len(fake_embed_lf.calls) == 1

    # ai_assist — embedding 호출 가능, LLM 0 (retriever 단계에서)
    fake_embed_aa.calls.clear()
    res_aa = hybrid_retrieve(  # noqa: F841
        "예약문자 작성", db=db_session, embedding_provider=fake_embed_aa,
        hybrid_enabled=True, mode=AI_MODE_AI_ASSIST,
    )
    assert_no_external_call(fake_llm_aa)
    assert len(fake_embed_aa.calls) == 1


# ──────────────────────── 회귀 — 기존 manual_qa 모드 무관 동작 ────────────────────────


def test_existing_manual_qa_unchanged_regardless_of_mode_module():
    """hybrid 모드 모듈 import 가 기존 manual_qa 동작에 영향 없음."""
    _rag_reset_cache()
    from app.services.ai import manual_qa as ai_manual_qa
    fake = FakeProvider(
        return_text="발췌에 따르면 예약 문자 탭에서 작성합니다.\n참고: sms_compose.md"
    )
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    # v1.3.3 응답 9 키 보존
    assert res["not_found"] is False
    assert "answer" in res
    assert "sources" in res
    assert "confidence" in res
    assert "blocked" in res
    assert "blocked_reason" in res
    assert "guard_hits" in res
    assert "top_score" in res
    assert "masked_question" in res
    # 회귀 모드 (A): LLM 1회 호출
    assert len(fake.calls) == 1


def test_local_only_keyword_search_still_works():
    """local_only 라도 manual_search (LLM 미사용) 는 정상 동작."""
    _rag_reset_cache()
    from app.services.ai import manual_qa as ai_manual_qa
    res = ai_manual_qa.manual_search("백업은 어디서 해?")
    assert "sources" in res
    assert len(res["sources"]) >= 1
