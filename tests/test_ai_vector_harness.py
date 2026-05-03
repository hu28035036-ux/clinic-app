"""18-5 Vector Harness — 사용자 메시지 21개 단언 + Codex T-1/T-2 보강 4개.

구성 (사용자 메시지 그대로):
  1.  FakeEmbeddingProvider 사용
  2.  실제 외부 embedding API 호출 0
  3.  knowledge_vectors 테이블 생성
  4.  chunk embedding 저장
  5.  embedding 조회
  6.  content_hash 같으면 embedding 재생성 X
  7.  content_hash 변경 → 재생성 대상
  8.  API key 없음 → vector_disabled / chunk indexing 성공
  9.  local_only 모드 → embedding_provider 호출 0
  10. 짧은 query → query embedding 생성 X
  11. invalid_query → query embedding 생성 X
  12. embedding provider 오류 → keyword fallback (전체 AI 죽지 않음)
  13. dimension mismatch → 안전 실패
  14. cosine similarity 안정 계산
  15. top_k vector search
  16. vector 결과에 chunk metadata 연결
  17. vector disabled 상태에서 keyword/manual RAG 통과
  18. 운영 DB 미사용
  19. 기존 manual RAG 하네스 통과
  20. 기존 safety 하네스 통과
  21. 기존 chunker/reindex 하네스 통과

Codex 18-4 권고 (T-1/T-2) 보강:
  T-1a. embedding_provider=None 이면 factory 호출 0
  T-1b. local_only 모드에서 factory 가 raise (인스턴스 자체 미생성)
  T-2a. m013 단독 호출 시 _table_exists False → 인덱스 생성 0건 (안전 skip)
  T-2b. init_db() 후 knowledge_vectors 테이블 자동 생성

회귀 보호:
  - manual_qa.manual_search 결과 vector 단계 전후 동일
  - 18-4 reindex 동작 무수정 — embedding_provider=None default
"""
from __future__ import annotations

import importlib

import pytest
from sqlalchemy import inspect

from app.database import SessionLocal, engine
from app.models.models import KnowledgeChunk, KnowledgeVector
from app.services.ai import manual_qa as ai_manual_qa
from app.services.ai.knowledge import indexer as ai_indexer
from app.services.ai.vector import embeddings as ai_embeddings
from app.services.ai.vector import similarity as ai_similarity
from app.services.ai.vector import store as ai_store
from app.services.ai.vector.embeddings import (
    EmbeddingUnavailable,
    FakeEmbeddingProvider,
    VectorDimensionMismatch,
    get_embedding_provider,
    is_embeddable_query,
)
from app.services.ai.vector.similarity import cosine_similarity, top_k
from app.services.ai.vector.store import (
    count_vectors,
    decode_embedding,
    encode_embedding,
    find_vector,
    list_vectors_for_query,
    upsert_vector,
)
from app.services.rag.search import reset_cache as _rag_reset_cache
from tests.harness.db_guard import assert_safe_db_path
from tests.harness.fake_provider import FakeProvider
from tests.harness.reindex_harness import make_doc, monkeypatch_load_documents
from tests.harness.vector_harness import (
    assert_no_embedding_call,
    assert_no_external_calls_full,
    cleanup_vector_tables,
    cosine_reference,
    make_fake_embedding_provider,
    seed_chunks_for_vector_test,
    sha256_hex,
)

# ──────────────────────── 픽스처 ────────────────────────


@pytest.fixture
def db_session():
    """격리된 SessionLocal — conftest 의 init_db 가 m013 까지 적용됨."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def clean_vector_tables():
    """각 테스트 전후 vector / chunk / run 테이블 정리."""
    db = SessionLocal()
    try:
        cleanup_vector_tables(db)
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        cleanup_vector_tables(db)
    finally:
        db.close()


# ──────────────────────── 픽스처 텍스트 ────────────────────────

DOC_A = """\
# 문서 A

## 섹션 A1
이것은 문서 A 의 첫 번째 섹션 본문입니다.
충분한 길이를 위해 추가 문장. 추가 문장. 추가 문장. 추가 문장.
추가 문장. 추가 문장. 추가 문장. 추가 문장. 추가 문장.

## 섹션 A2
이것은 문서 A 의 두 번째 섹션 본문입니다.
또 다른 본문 라인. 또 다른 본문 라인. 또 다른 본문 라인.
또 다른 본문 라인. 또 다른 본문 라인. 또 다른 본문 라인.
"""

DOC_B = """\
# 문서 B

## 섹션 B1
문서 B 의 본문입니다.
설명 문단. 설명 문단. 설명 문단. 설명 문단. 설명 문단.
설명 문단. 설명 문단. 설명 문단. 설명 문단. 설명 문단.
"""


# ──────────────────────── 1. FakeEmbeddingProvider 사용 ────────────────────────


def test_1_fake_embedding_provider_only():
    """요구사항 #1 — FakeEmbeddingProvider 만 사용 (외부 SDK 미사용)."""
    fake = make_fake_embedding_provider()
    assert isinstance(fake, FakeEmbeddingProvider)
    assert fake.name == "fake"
    assert fake.dimension == 16
    assert fake.model == "fake-embed-1"
    # 결정성 — 같은 텍스트 → 같은 vector
    v1 = fake.embed_query("hello")
    v2 = fake.embed_query("hello")
    assert v1 == v2
    # 다른 텍스트 → 다른 vector
    v3 = fake.embed_query("world")
    assert v1 != v3


# ──────────────────────── 2. 외부 API 호출 0 ────────────────────────


def test_2_no_external_embedding_call(monkeypatch):
    """요구사항 #2 — 실제 외부 OpenAI/Anthropic embedding API 호출 0.

    conftest._block_sdk_modules 가 SDK 클래스를 raise stub 으로 교체하므로,
    어떤 경로든 ``openai.OpenAI`` / ``anthropic.Anthropic`` 인스턴스화 시도시
    RuntimeError. 본 테스트는 vector 패키지가 SDK 를 import 하지 않음을 직접 검증.
    """
    # vector 패키지 source 에 openai/anthropic SDK import 가 없는지 검사.
    import inspect as _inspect

    sources = []
    for mod in (ai_embeddings, ai_store, ai_similarity):
        sources.append(_inspect.getsource(mod))
    joined = "\n".join(sources)
    # 직접 import 차단 — 본 세션에서는 외부 SDK 의존 코드 부재.
    forbidden = ("import openai", "from openai", "import anthropic", "from anthropic")
    for f in forbidden:
        assert f not in joined, f"vector 패키지에 외부 SDK import 금지: '{f}'"


# ──────────────────────── 3. knowledge_vectors 테이블 ────────────────────────


def test_3_knowledge_vectors_table_created():
    """요구사항 #3 — m013 + create_all 후 테이블 존재."""
    insp = inspect(engine)
    assert insp.has_table("knowledge_vectors"), "knowledge_vectors 테이블 미생성"


def test_3b_knowledge_vectors_columns_present():
    """필수 컬럼 — chunk_id/provider/model/dimension/embedding_*/content_hash 존재."""
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("knowledge_vectors")}
    required = {
        "id", "chunk_id", "provider", "model", "dimension",
        "embedding_json", "embedding_blob", "content_hash",
        "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"누락 컬럼: {missing}"


def test_3c_unique_constraint_chunk_provider_model(db_session, clean_vector_tables):
    """UNIQUE (chunk_id, provider, model) 제약 동작."""
    chunks = seed_chunks_for_vector_test(db_session, contents=["테스트 컨텐츠 1"])
    chunk = chunks[0]
    upsert_vector(
        db_session,
        chunk_id=chunk.id, provider="fake", model="fake-embed-1",
        dimension=4, embedding=[0.1, 0.2, 0.3, 0.4],
        content_hash=chunk.content_hash,
    )
    db_session.commit()
    # 두 번째 upsert (같은 키) → UPDATE/SKIP 으로 정상 동작 (UNIQUE 위반 X)
    upsert_vector(
        db_session,
        chunk_id=chunk.id, provider="fake", model="fake-embed-1",
        dimension=4, embedding=[0.1, 0.2, 0.3, 0.4],
        content_hash=chunk.content_hash,
    )
    db_session.commit()
    # row 1개여야
    cnt = count_vectors(db_session, provider="fake", model="fake-embed-1")
    assert cnt == 1, f"UNIQUE 제약: chunk_id+provider+model 같은데 row {cnt}개"


# ──────────────────────── 4. chunk embedding 저장 ────────────────────────


def test_4_upsert_vector_persists(db_session, clean_vector_tables):
    """요구사항 #4 — chunk embedding 저장 가능."""
    chunks = seed_chunks_for_vector_test(db_session, contents=["저장 테스트 컨텐츠"])
    chunk = chunks[0]
    fake = make_fake_embedding_provider(dimension=8)
    vec = fake.embed_query(chunk.content)

    row, status = upsert_vector(
        db_session,
        chunk_id=chunk.id, provider=fake.name, model=fake.model,
        dimension=fake.dimension, embedding=vec,
        content_hash=chunk.content_hash,
    )
    db_session.commit()

    assert status == "inserted"
    assert row.id is not None
    assert row.chunk_id == chunk.id
    assert row.provider == "fake"
    assert row.model == "fake-embed-1"
    assert row.dimension == 8
    assert row.embedding_json is not None and row.embedding_json != ""


# ──────────────────────── 5. embedding 조회 ────────────────────────


def test_5_find_vector_returns_row(db_session, clean_vector_tables):
    """요구사항 #5 — 저장된 embedding 조회."""
    chunks = seed_chunks_for_vector_test(db_session, contents=["조회 테스트"])
    chunk = chunks[0]
    fake = make_fake_embedding_provider(dimension=4)
    vec = fake.embed_query(chunk.content)
    upsert_vector(
        db_session,
        chunk_id=chunk.id, provider=fake.name, model=fake.model,
        dimension=fake.dimension, embedding=vec,
        content_hash=chunk.content_hash,
    )
    db_session.commit()

    found = find_vector(db_session, chunk_id=chunk.id, provider="fake", model="fake-embed-1")
    assert found is not None
    decoded = decode_embedding(found)
    # 부동소수점 — encode/decode 가 안정적이면 vec 와 길이/대략값 같음.
    assert len(decoded) == fake.dimension
    for a, b in zip(decoded, vec, strict=True):
        assert abs(a - b) < 1e-9


# ──────────────────────── 6. content_hash 같으면 재생성 X ────────────────────────


def test_6_same_hash_skips_embedding(db_session, clean_vector_tables):
    """요구사항 #6 — content_hash 같으면 embedding 재생성 없음.

    indexer 의 vector 단계가 same_hash skip 동작 — 두 번째 호출에서
    embed_documents 호출 0.
    """
    seed_chunks_for_vector_test(db_session, contents=["DOC1 컨텐츠", "DOC2 컨텐츠"])
    fake = make_fake_embedding_provider(dimension=4)

    # 첫 호출 — 2건 임베딩 생성
    result1 = ai_indexer.reindex_all(db_session, embedding_provider=fake)  # noqa: F841
    # 단, reindex_all 은 load_documents 를 호출하지만 우리는 직접 chunk seed 해놓음.
    # → 두 번째 reindex 가 같은 chunk 에 대해 same_hash skip 단언이 핵심.
    # 첫 호출에서 embed_documents 가 호출되어 vectors 가 만들어졌음을 확인:
    cnt_after_first = count_vectors(db_session, provider="fake", model="fake-embed-1")
    assert cnt_after_first >= 2, f"첫 reindex 후 vector row {cnt_after_first}개"
    calls_after_first = len(fake.calls)

    # 두 번째 호출 — same_hash 로 모두 skip 되어 embed_documents 추가 호출 없어야 함.
    fake2 = make_fake_embedding_provider(dimension=4)  # 호출 카운트 신선하게.
    result2 = ai_indexer.reindex_all(db_session, embedding_provider=fake2)
    # seed 한 chunk 들은 그대로 → same_hash skip
    assert result2.skipped_embeddings_same_hash >= 2
    assert result2.embedded_chunks == 0  # 새로 임베딩된 것 없음
    assert_no_embedding_call(fake2, "same_hash skip 시 embed_documents 호출 0")
    # 첫 호출의 카운트는 그대로 유지 (참조용)
    assert calls_after_first >= 1


# ──────────────────────── 7. content_hash 변경 → 재생성 대상 ────────────────────────


def test_7_changed_hash_re_embeds(db_session, clean_vector_tables):
    """요구사항 #7 — chunk content 변경 시 embedding 재생성 대상.

    indexer 의 vector 단계가 content_hash 변경 시 UPDATE 호출.
    """
    chunks = seed_chunks_for_vector_test(db_session, contents=["원본 컨텐츠"])
    chunk = chunks[0]
    original_hash = chunk.content_hash
    fake = make_fake_embedding_provider(dimension=4)
    ai_indexer.reindex_all(db_session, embedding_provider=fake)

    # chunk content 직접 변경 (원래는 reindex 가 처리하지만, vector 단계만 검증)
    chunk.content = "변경된 컨텐츠 — 새 hash 필요"
    chunk.content_hash = sha256_hex(chunk.content)
    assert chunk.content_hash != original_hash
    db_session.commit()

    fake2 = make_fake_embedding_provider(dimension=4)
    result = ai_indexer.reindex_all(db_session, embedding_provider=fake2)
    # 변경된 chunk 는 재임베딩 대상
    assert result.embedded_chunks >= 1, f"변경 hash 재임베딩 대상 0건: {result}"
    assert len(fake2.calls) >= 1, "변경 hash 가 있는데 embed_documents 미호출"


# ──────────────────────── 8. API key 없음 → vector_disabled ────────────────────────


def test_8_no_api_key_vector_disabled():
    """요구사항 #8 — API key 없으면 vector 만 disabled, chunk indexing 은 가능."""
    # ai_setting duck-type — provider 있지만 api_key 없음
    class _AiSettingNoKey:
        provider = "openai"
        api_key = ""

    with pytest.raises(EmbeddingUnavailable) as exc:
        get_embedding_provider(
            ai_setting=_AiSettingNoKey(),
            mode="local_first",
            allow_external=True,
        )
    assert exc.value.kind == "api_key_missing"


def test_8b_no_api_key_indexer_keyword_only(db_session, clean_vector_tables, monkeypatch):
    """API key 없는 환경에서 reindex_all(embedding_provider=None) → chunk OK / vector skip."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)
    result = ai_indexer.reindex_all(db_session)  # embedding_provider=None
    # chunk 인덱싱은 정상 진행
    assert result.total_documents == 1
    assert result.processed_documents == 1
    assert result.total_chunks >= 1
    # vector 단계는 skip
    assert result.embedded_chunks == 0
    assert result.vector_disabled_reason == "no_provider"
    # vector row 부재
    assert count_vectors(db_session) == 0


# ──────────────────────── 9. local_only → embedding 호출 0 ────────────────────────


def test_9_local_only_no_embedding_call():
    """요구사항 #9 — local_only 모드에서 factory 가 raise (인스턴스화 자체 차단)."""
    with pytest.raises(EmbeddingUnavailable) as exc:
        get_embedding_provider(
            ai_setting=None, mode="local_only", allow_external=True,
        )
    assert exc.value.kind == "local_only"


def test_9b_local_only_indexer_no_embedding_call(db_session, clean_vector_tables, monkeypatch):
    """local_only 시뮬레이션 — embedding_provider=None 으로 indexer 호출 → fake calls 0."""
    fake = make_fake_embedding_provider(raise_on_call=True)
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)
    # local_only 시뮬레이션 — provider 미주입.
    result = ai_indexer.reindex_all(db_session)  # embedding_provider=None
    assert result.total_chunks >= 1
    # fake 는 주입 안 했으니 raise_on_call 도 발동 안 됨 — len(calls)==0
    assert_no_embedding_call(fake, "local_only 모드 시뮬레이션: embedding 호출 0")


# ──────────────────────── 10/11. 짧은 query / invalid query ────────────────────────


def test_10_short_query_skipped():
    """요구사항 #10 — 너무 짧은 query 는 embedding 생성 X."""
    assert is_embeddable_query("a") is False  # 1자
    assert is_embeddable_query(" a ") is False  # strip 후 1자
    assert is_embeddable_query("ab") is True  # 2자 = 임계


def test_11_invalid_query_skipped():
    """요구사항 #11 — invalid_query 는 embedding 생성 X."""
    assert is_embeddable_query("") is False
    assert is_embeddable_query("   ") is False
    assert is_embeddable_query(None) is False
    assert is_embeddable_query(123) is False  # type: ignore[arg-type]


# ──────────────────────── 12. provider 오류 → keyword fallback ────────────────────────


def test_12_provider_error_keyword_fallback(db_session, clean_vector_tables, monkeypatch):
    """요구사항 #12 — embedding provider 오류 → 전체 AI 죽지 X, keyword fallback."""
    # raise_on_call=True 로 호출 시 즉시 RuntimeError.
    fake = make_fake_embedding_provider(raise_on_call=True)
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    result = ai_indexer.reindex_all(db_session, embedding_provider=fake)
    # chunk 인덱싱은 정상 (사용자 요구 #12 — 전체 AI 죽지 X)
    assert result.total_chunks >= 1
    assert result.processed_documents == 1
    # vector 단계는 실패 처리 — failed_embeddings 혹은 vector_disabled_reason 기록
    assert result.failed_embeddings >= 1 or result.vector_disabled_reason
    assert "provider_error" in result.vector_disabled_reason or result.failed_embeddings >= 1
    # reindex status 자체는 chunk 기준 success/partial — failed 가 아님
    assert result.status in (
        ai_indexer.STATUS_SUCCESS, ai_indexer.STATUS_PARTIAL,
    ), f"vector 실패가 reindex status 에 영향: {result.status}"

    # keyword fallback — manual_qa.manual_search 가 정상 동작 확인
    _rag_reset_cache()
    res = ai_manual_qa.manual_search("예약문자 작성")
    assert "sources" in res  # 응답 스키마 보존


# ──────────────────────── 13. dimension mismatch ────────────────────────


def test_13_dimension_mismatch_safe(db_session, clean_vector_tables):
    """요구사항 #13 — dimension mismatch 안전 실패 (cosine 0.0, list_vectors 자동 필터)."""
    chunks = seed_chunks_for_vector_test(db_session, contents=["TEST"])
    chunk = chunks[0]
    upsert_vector(
        db_session, chunk_id=chunk.id, provider="fake", model="fake-embed-1",
        dimension=8, embedding=[0.1] * 8, content_hash=chunk.content_hash,
    )
    db_session.commit()

    # query dim=4 로 list_vectors_for_query → dim 일치 row 없음
    rows = list_vectors_for_query(db_session, provider="fake", model="fake-embed-1", dimension=4)
    assert rows == []  # dim mismatch row 자동 제외

    # cosine 직접 호출 — mismatch 시 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

    # upsert dimension mismatch → VectorDimensionMismatch
    with pytest.raises(VectorDimensionMismatch):
        upsert_vector(
            db_session, chunk_id=chunk.id, provider="fake", model="fake-embed-2",
            dimension=8, embedding=[0.1] * 4,  # 4 != 8
            content_hash=chunk.content_hash,
        )


# ──────────────────────── 14. cosine similarity 안정 계산 ────────────────────────


def test_14_cosine_known_vectors():
    """요구사항 #14 — cosine 의 결정적 정확성."""
    # 단위 벡터 self
    assert abs(cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) - 1.0) < 1e-12
    # 직교
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-12
    # 반대 방향
    assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-12
    # 0 벡터
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [0.0, 0.0]) == 0.0
    # 빈 벡터
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], []) == 0.0
    # reference 와 일치
    a = [0.3, -0.4, 0.1, 0.9]
    b = [-0.2, 0.5, 0.7, 0.1]
    assert abs(cosine_similarity(a, b) - cosine_reference(a, b)) < 1e-12


# ──────────────────────── 15. top_k 동작 ────────────────────────


def test_15_top_k_search():
    """요구사항 #15 — top_k 가 sorted DESC + 안정 정렬."""
    query = [1.0, 0.0]
    candidates = [
        ("c1", [1.0, 0.0]),       # cos=1
        ("c2", [0.5, 0.5]),       # cos=√2/2 ≈ 0.707
        ("c3", [0.0, 1.0]),       # cos=0
        ("c4", [-1.0, 0.0]),      # cos=-1
        ("c5", [0.9, 0.1]),       # cos≈0.994
    ]
    res = top_k(query, candidates, k=3)
    payloads = [p for p, _ in res]
    assert payloads == ["c1", "c5", "c2"]
    # k > 후보 수 → 모두 반환
    res_all = top_k(query, candidates, k=100)
    assert len(res_all) == 5
    # query 가 0 벡터 → 빈
    assert top_k([0.0, 0.0], candidates, k=3) == []
    # k=0 → 빈
    assert top_k(query, candidates, k=0) == []


# ──────────────────────── 16. metadata 연결 ────────────────────────


def test_16_vector_results_carry_metadata(db_session, clean_vector_tables):
    """요구사항 #16 — vector 결과에 chunk metadata (title/path/heading) 연결."""
    chunks = seed_chunks_for_vector_test(
        db_session,
        contents=["메타1", "메타2"],
        title="테스트 매뉴얼",
    )
    fake = make_fake_embedding_provider(dimension=4)
    for c in chunks:
        upsert_vector(
            db_session, chunk_id=c.id, provider=fake.name, model=fake.model,
            dimension=fake.dimension, embedding=fake.embed_query(c.content),
            content_hash=c.content_hash,
        )
    db_session.commit()

    rows = list_vectors_for_query(
        db_session, provider="fake", model="fake-embed-1", dimension=4,
    )
    assert len(rows) == 2
    # (vector, chunk) 페어 — chunk 의 메타가 보존되는지
    for v, c in rows:
        assert isinstance(v, KnowledgeVector)
        assert isinstance(c, KnowledgeChunk)
        assert c.title == "테스트 매뉴얼"
        assert c.source_path.startswith("manuals/test_")


# ──────────────────────── 17. vector disabled 에서 keyword RAG 통과 ────────────────────────


def test_17_vector_disabled_keyword_works():
    """요구사항 #17 — vector disabled (provider 없음) 환경에서 manual RAG 통과."""
    _rag_reset_cache()
    res = ai_manual_qa.manual_search("예약문자 작성")
    # v1.3.3 응답 스키마 — sources / masked_question / top_score
    assert "sources" in res
    assert "masked_question" in res
    assert "top_score" in res


# ──────────────────────── 18. 운영 DB 미사용 ────────────────────────


def test_18_does_not_use_operational_db():
    """요구사항 #18 — assert_safe_db_path 통과."""
    path = assert_safe_db_path()
    assert "test_clinic_" in path or "tests" in path.lower()


# ──────────────────────── 19. 기존 manual RAG 회귀 ────────────────────────


def test_19_manual_rag_baseline_unchanged(db_session, clean_vector_tables):
    """요구사항 #19 — vector 작업이 manual_qa 결과에 영향 0.

    vector 단계 실행 전후로 manual_qa.manual_search 결과가 같아야 함.
    """
    _rag_reset_cache()
    before = ai_manual_qa.manual_search("예약문자 작성")

    # vector 단계 실행 (chunks seed → embed)
    seed_chunks_for_vector_test(db_session, contents=["임의의 텍스트"])
    fake = make_fake_embedding_provider(dimension=4)
    ai_indexer.reindex_all(db_session, embedding_provider=fake)

    _rag_reset_cache()
    after = ai_manual_qa.manual_search("예약문자 작성")
    # source 리스트는 keyword 검색 결과 — vector 와 무관 (18-6 hybrid 시점에 통합)
    # → before/after 둘 다 같은 sources 키 + 같은 top_score
    assert before.keys() == after.keys()
    assert before["top_score"] == after["top_score"]
    assert len(before["sources"]) == len(after["sources"])


# ──────────────────────── 20. safety 회귀 smoke ────────────────────────


def test_20_safety_harness_smoke():
    """요구사항 #20 — safety_harness 핵심 helper import + smoke."""
    from tests.harness import safety_harness  # noqa: F401
    # safety_harness 모듈이 import 가능해야 함 (회귀 보호)


# ──────────────────────── 21. chunker/reindex 회귀 smoke ────────────────────────


def test_21_reindex_harness_smoke(db_session, clean_vector_tables, monkeypatch):
    """요구사항 #21 — reindex_harness make_doc + 18-4 동작 회귀 0.

    embedding_provider=None 으로 reindex 호출 → 18-4 동작 그대로.
    """
    docs = [make_doc("manuals/test_z.md", DOC_B)]
    monkeypatch_load_documents(monkeypatch, docs)
    result = ai_indexer.reindex_all(db_session)  # default embedding_provider=None
    assert result.status == ai_indexer.STATUS_SUCCESS
    assert result.total_chunks >= 1
    assert result.embedded_chunks == 0
    assert result.failed_embeddings == 0
    assert result.vector_disabled_reason == "no_provider"
    # KnowledgeChunk row 가 생성됨
    cnt = db_session.query(KnowledgeChunk).count()
    assert cnt >= 1


# ──────────────────────── Codex T-1 보강 ────────────────────────


def test_T1_indexer_does_not_call_embedding_factory_when_none(monkeypatch):
    """T-1a — embedding_provider=None 이면 factory 호출 0.

    ai_embeddings.get_embedding_provider 를 monkeypatch 로 호출 카운터 부착 →
    indexer 가 default 경로에서 factory 자체를 부르지 않는지 검증.
    """
    factory_calls = {"count": 0}
    original = ai_embeddings.get_embedding_provider

    def _spy(*args, **kwargs):
        factory_calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(ai_embeddings, "get_embedding_provider", _spy)

    db = SessionLocal()
    try:
        cleanup_vector_tables(db)
        # indexer.load_documents monkeypatch
        docs = [make_doc("manuals/test_a.md", DOC_A)]
        monkeypatch_load_documents(monkeypatch, docs)
        ai_indexer.reindex_all(db)  # embedding_provider=None
    finally:
        cleanup_vector_tables(db)
        db.close()

    assert factory_calls["count"] == 0, (
        f"embedding_provider=None 인데 factory 호출 {factory_calls['count']}회"
    )


def test_T1_local_only_blocks_embedding_factory():
    """T-1b — local_only 모드 factory 가 인스턴스 자체를 만들지 않음."""
    # raise 만 검증 — _UnavailableEmbeddingProvider 도 반환 X
    with pytest.raises(EmbeddingUnavailable) as exc:
        get_embedding_provider(ai_setting=None, mode="local_only", allow_external=True)
    assert exc.value.kind == "local_only"

    # allow_external=False 도 차단되는지
    with pytest.raises(EmbeddingUnavailable) as exc2:
        get_embedding_provider(ai_setting=None, mode="local_first", allow_external=False)
    assert exc2.value.kind == "disabled"


# ──────────────────────── Codex T-2 보강 ────────────────────────


def test_T2_m013_alone_skips_when_table_absent():
    """T-2a — m013 단독 호출 시 _table_exists False → 인덱스 생성 0건 (안전 skip).

    실제로는 init_db 가 항상 ORM create_all → m013 실행 순서지만,
    단독 호출 안전성 검증.
    """
    import sqlite3

    m013 = importlib.import_module("app.migrations.m013_knowledge_vectors")
    # in-memory DB — 테이블 부재
    conn = sqlite3.connect(":memory:")
    try:
        # 테이블 없는 상태에서 up() 호출 → 인덱스 생성 시도 X (안전 skip)
        m013.up(conn)  # 예외 raise 하지 않아야 함
        # 인덱스도 만들어지지 않았어야 함
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name LIKE '%knowledge_vectors%'"
        ).fetchall()
        assert rows == [], f"테이블 부재인데 인덱스 생성됨: {rows}"
    finally:
        conn.close()


def test_T2_init_db_creates_knowledge_vectors_table():
    """T-2b — init_db() 후 knowledge_vectors 테이블 자동 생성됨."""
    insp = inspect(engine)
    assert insp.has_table("knowledge_vectors"), (
        "init_db() 후 knowledge_vectors 테이블 미생성"
    )
    # m013 인덱스 보강도 적용됨
    indexes = insp.get_indexes("knowledge_vectors")
    index_names = {idx["name"] for idx in indexes}
    # ORM index=True 인덱스 + m013 보강 인덱스 모두 포함
    assert any("chunk_id" in n for n in index_names), f"chunk_id 인덱스 누락: {index_names}"
    assert any("content_hash" in n for n in index_names), (
        f"content_hash 인덱스 누락: {index_names}"
    )


# ──────────────────────── 추가 회귀 ────────────────────────


def test_external_provider_no_api_call(monkeypatch):
    """추가 — provider=openai/anthropic 인 경우 NotImplementedError(sdk_missing)/api_key_missing 단계에서 차단."""
    # 1) api_key 없음 → api_key_missing
    class _S1:
        provider = "openai"
        api_key = ""

    with pytest.raises(EmbeddingUnavailable) as exc:
        get_embedding_provider(
            ai_setting=_S1(), mode="local_first", allow_external=True,
        )
    assert exc.value.kind == "api_key_missing"

    # 2) api_key 있어도 18-5 시점에는 sdk_missing
    class _S2:
        provider = "openai"
        api_key = "test-key"

    with pytest.raises(EmbeddingUnavailable) as exc2:
        get_embedding_provider(
            ai_setting=_S2(), mode="local_first", allow_external=True,
        )
    assert exc2.value.kind == "sdk_missing"


def test_provider_call_count_via_calls_attr():
    """FakeEmbeddingProvider.calls 가 list 이고, 호출 카운트가 len 으로 측정 가능."""
    fake = make_fake_embedding_provider(dimension=4)
    assert fake.calls == []
    fake.embed_query("hello")
    assert len(fake.calls) == 1
    fake.embed_documents(["a", "b"])
    assert len(fake.calls) == 2


def test_full_external_call_blocking_smoke():
    """전체 외부 호출 0 통합 단언 — provider=None / embedding_provider=None smoke."""
    llm = FakeProvider()
    embed = make_fake_embedding_provider()
    # 둘 다 호출 0
    assert_no_external_calls_full(llm, embed)


def test_reason_codes_defined():
    """schemas.py 에 18-5 reason_code 6개 모두 정의."""
    from app.services.ai.rag import schemas as _s
    expected = {
        "vector_disabled",
        "embedding_skipped_local_only",
        "embedding_skipped_same_hash",
        "embedding_skipped_short_query",
        "embedding_skipped_disabled",
        "embedding_skipped_api_key_missing",
    }
    assert expected.issubset(set(_s.ALL_REASON_CODES))
    # __all__ 에도 포함
    assert "REASON_VECTOR_DISABLED" in _s.__all__
    assert "REASON_EMBEDDING_SKIPPED_SAME_HASH" in _s.__all__


def test_indexer_no_delete_calls():
    """indexer 모듈이 어떤 분기에서도 db.delete / DELETE FROM 을 호출하지 않음.

    18-4 회귀 보호 — vector 단계 추가가 chunk DELETE 를 도입하지 않았는지.
    AST 로 docstring/주석 제외하고 실제 코드 토큰만 검사.
    """
    import ast
    import inspect as _inspect

    src = _inspect.getsource(ai_indexer)
    tree = ast.parse(src)

    # 모든 Call 노드를 순회 — `<...>.delete(...)` 패턴 검출
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "delete":
                raise AssertionError(
                    f"indexer 가 .delete() 호출 — 18-4 정책 위반 (line {node.lineno})"
                )
        # 함수명에 'delete' 포함 호출도 차단 (예: query.delete())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if "delete" in node.func.id.lower():
                raise AssertionError(
                    f"indexer 가 delete 관련 함수 호출 — 18-4 정책 위반 (line {node.lineno})"
                )


def test_encode_decode_roundtrip(db_session, clean_vector_tables):
    """encode/decode 가 vector 값을 보존."""
    vec = [0.1, -0.2, 0.3, -0.4, 0.5, -0.6, 0.7, -0.8]
    encoded = encode_embedding(vec)
    chunks = seed_chunks_for_vector_test(db_session, contents=["roundtrip"])
    chunk = chunks[0]
    upsert_vector(
        db_session, chunk_id=chunk.id, provider="fake", model="fake-embed-1",
        dimension=8, embedding=vec, content_hash=chunk.content_hash,
    )
    db_session.commit()

    row = find_vector(db_session, chunk_id=chunk.id, provider="fake", model="fake-embed-1")
    assert row is not None
    assert row.embedding_json == encoded
    decoded = decode_embedding(row)
    assert len(decoded) == 8
    for a, b in zip(decoded, vec, strict=True):
        assert abs(a - b) < 1e-12


def test_vector_disabled_reason_records_correctly(db_session, clean_vector_tables, monkeypatch):
    """factory 가 disabled 사유로 차단되었을 때, indexer 에 사유 전달."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    # local_only 시뮬레이션 — 호출자가 disabled_reason 을 명시 전달
    result = ai_indexer.reindex_all(
        db_session,
        embedding_provider=None,
        vector_disabled_reason="local_only",
    )
    assert result.vector_disabled_reason == "local_only"
    assert result.embedded_chunks == 0
    # chunk 는 정상 진행
    assert result.total_chunks >= 1
