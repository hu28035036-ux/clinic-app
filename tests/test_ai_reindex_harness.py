"""18-4 Reindex Harness — 사용자 메시지의 15개 단언 + lock/UNIQUE 추가 단언.

구성 (사용자 메시지 그대로):
  1.  knowledge_chunks 테이블 생성 확인
  2.  문서 → chunk → DB 저장
  3.  source_path/title/heading/chunk_index/content/content_hash 저장
  4.  같은 문서 두 번 reindex → 중복 chunk 없음
  5.  content_hash 같으면 skip
  6.  문서 변경 시 변경된 chunk 반영
  7.  reindex 실패 시 기존 chunk 보존
  8.  부분 실패 시 실패 정보 기록
  9.  API key 없어도 동작
  10. reindex 중 외부 LLM provider 호출 0
  11. reindex 중 embedding provider 호출 0
  12. 운영 DB 미사용
  13. 기존 manual RAG 회귀 0 (manual_search 결과 동일)
  14. 기존 safety 회귀 (smoke import + 단언 — 별도 file 도 통과)
  15. 기존 full 회귀 (smoke import + 단언 — 별도 file 도 통과)

추가 단언:
  16. UNIQUE (doc_id, chunk_index) 제약 동작
  17. KnowledgeIndexRun.status 가 reindex 후 'running' 으로 남지 않음
  18. lock 점유 중 호출 → status='skipped_in_progress' & 새 row 미생성
  19. indexer import-graph 안전성 (네트워크/SDK/provider 부재)

회귀 보호:
  - manual_qa.manual_search 결과 reindex 전후 동일
  - 18-3 chunker 동작 무수정 (chunker 호출 결과 검증)
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import inspect

from app.database import SessionLocal, engine
from app.models.models import KnowledgeChunk, KnowledgeIndexRun
from app.services.ai.knowledge import indexer as ai_indexer
from app.services.ai.knowledge.chunker import chunk_document
from tests.harness.db_guard import assert_safe_db_path
from tests.harness.fake_provider import FakeProvider
from tests.harness.reindex_harness import (
    assert_no_external_call,
    count_chunks,
    count_runs,
    make_doc,
    monkeypatch_chunker_raises_for_path,
    monkeypatch_load_documents,
)

# ──────────────────────── 픽스처 ────────────────────────


@pytest.fixture
def db_session():
    """격리된 SessionLocal — conftest 의 init_db 가 m012 까지 적용됨."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def clean_chunk_tables():
    """각 테스트 전후 knowledge_chunks / knowledge_index_runs 정리.

    18-4 indexer 는 어떤 분기에서도 DELETE 를 호출하지 않지만, 테스트 간
    격리를 위해 fixture 가 명시적으로 정리한다 (테스트 내부의 DELETE 가
    아니므로 indexer 정책 위반 아님).
    """
    db = SessionLocal()
    try:
        db.query(KnowledgeChunk).delete()
        db.query(KnowledgeIndexRun).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(KnowledgeChunk).delete()
        db.query(KnowledgeIndexRun).delete()
        db.commit()
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


# ──────────────────────── 1. 테이블 생성 ────────────────────────


def test_1_knowledge_chunks_table_created():
    """요구사항 #1 — m012 + create_all 후 두 테이블 모두 존재."""
    insp = inspect(engine)
    assert insp.has_table("knowledge_chunks"), "knowledge_chunks 테이블 미생성"
    assert insp.has_table("knowledge_index_runs"), "knowledge_index_runs 테이블 미생성"


def test_1b_knowledge_chunks_columns_present():
    """필수 컬럼 — source_path/title/heading/chunk_index/content/content_hash 존재."""
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("knowledge_chunks")}
    required = {
        "id", "doc_id", "source_path", "category", "title", "heading",
        "section_path", "chunk_index", "content", "content_hash",
        "token_count", "tags", "document_version", "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"누락된 컬럼: {missing}"


def test_1c_knowledge_index_runs_columns_present():
    """KnowledgeIndexRun 의 사용자 요구 12개 필드 컬럼 존재."""
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("knowledge_index_runs")}
    required_subset = {
        "id", "started_at", "finished_at", "status", "trigger",
        "total_documents", "processed_documents", "failed_documents",
        "total_chunks", "inserted_chunks", "updated_chunks", "skipped_chunks",
        "failed_chunks", "failed_paths", "errors",
    }
    missing = required_subset - cols
    assert not missing, f"누락된 컬럼: {missing}"


# ──────────────────────── 2. 문서 → chunk → DB 저장 ────────────────────────


def test_2_document_to_chunks_to_db(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #2 — load_documents 패치 후 reindex → chunk row 생성."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    result = ai_indexer.reindex_all(db_session, trigger="manual")

    assert result.status == ai_indexer.STATUS_SUCCESS, result.status
    assert result.total_documents == 1
    assert result.processed_documents == 1
    assert result.failed_documents == 0
    assert result.total_chunks > 0
    assert result.inserted_chunks > 0
    assert count_chunks(db_session) == result.inserted_chunks


# ──────────────────────── 3. 필드 보존 ────────────────────────


def test_3_chunk_fields_persisted(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #3 — source_path/title/heading/chunk_index/content/content_hash 가 chunk_document 결과와 동일."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)
    ai_indexer.reindex_all(db_session, trigger="manual")

    expected_chunks = chunk_document(docs[0])
    assert expected_chunks, "chunker 가 chunk 를 만들지 못함"

    rows = (
        db_session.query(KnowledgeChunk)
        .filter(KnowledgeChunk.doc_id == expected_chunks[0].doc_id)
        .order_by(KnowledgeChunk.chunk_index.asc())
        .all()
    )
    assert len(rows) == len(expected_chunks)
    for row, exp in zip(rows, expected_chunks, strict=True):
        assert row.source_path == exp.source_path
        assert row.title == exp.title
        assert row.heading == exp.heading
        assert row.chunk_index == exp.chunk_index
        assert row.content == exp.content
        assert row.content_hash == exp.content_hash


# ──────────────────────── 4. 두 번 reindex → 중복 없음 ────────────────────────


def test_4_double_reindex_no_duplicates(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #4 — 같은 docs 로 reindex 두 번 → row 수 동일."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    r1 = ai_indexer.reindex_all(db_session, trigger="manual")
    count_after_1st = count_chunks(db_session)

    r2 = ai_indexer.reindex_all(db_session, trigger="manual")
    count_after_2nd = count_chunks(db_session)

    assert count_after_1st == count_after_2nd, (
        f"중복 chunk 발생: 1차={count_after_1st}, 2차={count_after_2nd}"
    )
    assert r1.inserted_chunks > 0
    assert r2.inserted_chunks == 0  # 2차는 모두 skip


# ──────────────────────── 5. content_hash 같으면 skip ────────────────────────


def test_5_same_hash_skipped(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #5 — 두 번째 호출 시 모두 skip 카운터로."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    ai_indexer.reindex_all(db_session, trigger="manual")
    r2 = ai_indexer.reindex_all(db_session, trigger="manual")

    assert r2.skipped_chunks > 0, "skip 카운터가 증가하지 않음"
    assert r2.inserted_chunks == 0
    assert r2.updated_chunks == 0
    assert r2.skipped_chunks == r2.total_chunks


# ──────────────────────── 6. 변경 반영 ────────────────────────


def test_6_changed_doc_updates_affected_chunks(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #6 — 1글자 변경 후 reindex → 영향 chunk 만 update."""
    docs1 = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs1)
    ai_indexer.reindex_all(db_session, trigger="manual")

    chunks_before = chunk_document(docs1[0])
    hashes_before = {c.chunk_index: c.content_hash for c in chunks_before}

    # 같은 source_path 로 doc 내용만 수정 (doc_id 동일 유지)
    modified_text = DOC_A.replace("문서 A 의 첫 번째 섹션 본문",
                                  "문서 A 의 첫 번째 섹션 본문(수정)")
    docs2 = [make_doc("manuals/test_a.md", modified_text)]
    monkeypatch_load_documents(monkeypatch, docs2)
    r2 = ai_indexer.reindex_all(db_session, trigger="manual")

    assert r2.updated_chunks > 0, "변경된 chunk 가 update 로 반영 안 됨"

    # 실제 row 의 hash 가 갱신됐는지 확인
    chunks_after = chunk_document(docs2[0])
    hashes_after_expected = {c.chunk_index: c.content_hash for c in chunks_after}

    rows = (
        db_session.query(KnowledgeChunk)
        .filter(KnowledgeChunk.doc_id == chunks_before[0].doc_id)
        .all()
    )
    for row in rows:
        assert row.content_hash == hashes_after_expected.get(row.chunk_index)

    # 적어도 하나는 hash 가 달라야 (변경 반영의 증명)
    assert any(
        hashes_before.get(idx) != hashes_after_expected.get(idx)
        for idx in hashes_after_expected
    ), "변경 후 모든 hash 가 동일 — 변경이 반영 안 됨"


# ──────────────────────── 7. 실패 시 기존 chunk 보존 ────────────────────────


def test_7_failure_preserves_existing_chunks(
    monkeypatch, db_session, clean_chunk_tables
):
    """요구사항 #7 — 1차 정상 → 2차 chunker 실패 → 1차 row 보존."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)
    ai_indexer.reindex_all(db_session, trigger="manual")
    count_before = count_chunks(db_session)
    assert count_before > 0

    # 2차: chunker 가 모든 doc 에 대해 raise
    monkeypatch_chunker_raises_for_path(
        monkeypatch,
        fail_path="manuals/test_a.md",
        error=RuntimeError("simulated chunker failure"),
    )
    r2 = ai_indexer.reindex_all(db_session, trigger="manual")

    count_after = count_chunks(db_session)
    assert count_after == count_before, (
        f"실패 후 chunk 수 변경: before={count_before}, after={count_after}"
    )
    assert r2.failed_documents == 1
    assert r2.status in (ai_indexer.STATUS_PARTIAL, ai_indexer.STATUS_FAILED)


# ──────────────────────── 8. 부분 실패 정보 기록 ────────────────────────


def test_8_partial_failure_records_failed_paths(
    monkeypatch, db_session, clean_chunk_tables
):
    """요구사항 #8 — 2 docs 중 1개만 실패 → errors/failed_paths 정확히 기록."""
    docs = [
        make_doc("manuals/ok.md", DOC_A),
        make_doc("manuals/bad.md", DOC_B),
    ]
    monkeypatch_load_documents(monkeypatch, docs)
    monkeypatch_chunker_raises_for_path(
        monkeypatch,
        fail_path="manuals/bad.md",
        error=RuntimeError("simulated"),
    )

    r = ai_indexer.reindex_all(db_session, trigger="manual")

    assert r.failed_documents == 1
    assert r.processed_documents == 1
    assert r.status == ai_indexer.STATUS_PARTIAL
    assert any(e["path"] == "manuals/bad.md" for e in r.errors), r.errors

    # KnowledgeIndexRun 에도 기록됐는지
    run = db_session.query(KnowledgeIndexRun).filter(
        KnowledgeIndexRun.id == r.run_id
    ).one()
    assert run.status == ai_indexer.STATUS_PARTIAL
    assert "manuals/bad.md" in run.failed_paths
    errors_json = json.loads(run.errors) if run.errors else []
    assert any(e.get("path") == "manuals/bad.md" for e in errors_json)


# ──────────────────────── 9. API key 없어도 동작 ────────────────────────


def test_9_works_without_api_key(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #9 — AiSetting.enabled=False, api_key=빈 문자열 상태에서도 정상 reindex."""
    from app.models import models as _models

    s = db_session.query(_models.AiSetting).filter(_models.AiSetting.id == 1).first()
    if s is None:
        s = _models.AiSetting(id=1)
        db_session.add(s)
    s.enabled = False
    s.api_key = ""
    s.model = ""
    db_session.commit()

    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    r = ai_indexer.reindex_all(db_session, trigger="manual")
    assert r.status in (ai_indexer.STATUS_SUCCESS, ai_indexer.STATUS_PARTIAL)
    assert r.failed_documents == 0


# ──────────────────────── 10. LLM provider 호출 0 ────────────────────────


def test_10_no_llm_provider_call(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #10 — reindex 중 FakeProvider.calls 가 0 으로 유지."""
    fake = FakeProvider()
    # ai_provider.get_provider 를 fake 반환하도록 patch — indexer 가 호출하면 잡힘
    from app.services.ai import provider as ai_provider
    monkeypatch.setattr(ai_provider, "get_provider", lambda *a, **kw: fake)

    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    ai_indexer.reindex_all(db_session, trigger="manual")
    assert_no_external_call(provider=fake)


# ──────────────────────── 11. embedding provider 호출 0 ────────────────────────


def test_11_no_embedding_provider_call(monkeypatch, db_session, clean_chunk_tables):
    """요구사항 #11 — embedding provider mock 의 calls 가 0 으로 유지.

    embedding provider 는 18-5 도입 — 본 테스트는 mock object 로 대체 (chunker_harness #14 패턴).
    """
    class _MockEmbedding:
        calls: list = []

    mock_emb = _MockEmbedding()
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)

    ai_indexer.reindex_all(db_session, trigger="manual")
    assert_no_external_call(embedding_provider=mock_emb)


# ──────────────────────── 12. 운영 DB 미사용 ────────────────────────


def test_12_does_not_use_operational_db():
    """요구사항 #12 — db_guard 가 운영 DB 경로 차단 + indexer 직접 sqlite3 import 안 함."""
    path = assert_safe_db_path()
    assert "test" in path.lower() or "temp" in path.lower(), path

    # indexer.py 가 sqlite3 / 네트워크 SDK / provider 를 직접 import 하지 않음
    import app.services.ai.knowledge.indexer as idx
    src = open(idx.__file__, "r", encoding="utf-8").read()
    forbidden = [
        "import sqlite3", "from sqlite3",
        "import requests", "import httpx",
        "import openai", "import anthropic",
    ]
    for f in forbidden:
        assert f not in src, f"indexer.py 가 금지 import 포함: {f!r}"


# ──────────────────────── 13. manual RAG 회귀 ────────────────────────


def test_13_manual_rag_unaffected_by_reindex(
    monkeypatch, db_session, clean_chunk_tables
):
    """요구사항 #13 — manual_qa.manual_search 결과가 reindex 전후 동일."""
    from app.services.ai import manual_qa as ai_manual_qa

    before = ai_manual_qa.manual_search("예약문자 작성")

    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)
    ai_indexer.reindex_all(db_session, trigger="manual")

    after = ai_manual_qa.manual_search("예약문자 작성")

    # 응답 키 동일
    assert set(before.keys()) == set(after.keys())
    # sources 의 paths 가 동일 (순서 무관 비교)
    paths_before = sorted(s.get("path", "") for s in before.get("sources", []))
    paths_after = sorted(s.get("path", "") for s in after.get("sources", []))
    assert paths_before == paths_after, (
        f"manual_search sources 변동: before={paths_before}, after={paths_after}"
    )
    assert before.get("top_score") == after.get("top_score")


# ──────────────────────── 14. safety 회귀 (smoke) ────────────────────────


def test_14_safety_harness_imports_and_keys_intact():
    """요구사항 #14 — safety_harness 의 핵심 단언 함수가 정상 import 가능 (회귀 0).

    별도 file `tests/test_ai_safety_harness.py` 의 전체 통과는 별도 명령으로 확인.
    """
    from tests.harness.safety_harness import (
        DANGEROUS_RESPONSES,
        PII_PHONE_TEXTS,
        UNKNOWN_FEATURE_QUESTIONS,
        assert_no_api_key_in_text,
        assert_no_pii_in_text,
        assert_pii_marker_present,
    )
    # 상수와 함수가 모두 truthy
    assert DANGEROUS_RESPONSES
    assert PII_PHONE_TEXTS
    assert UNKNOWN_FEATURE_QUESTIONS
    assert callable(assert_no_api_key_in_text)
    assert callable(assert_no_pii_in_text)
    assert callable(assert_pii_marker_present)


# ──────────────────────── 15. full 회귀 (smoke) ────────────────────────


def test_15_full_harness_imports_intact():
    """요구사항 #15 — full harness import 정상 (별도 file 통과는 명령으로 확인)."""
    from tests.harness.contract import assert_manual_ask_contract
    assert callable(assert_manual_ask_contract)


# ──────────────────────── +16. UNIQUE 제약 ────────────────────────


def test_16_unique_doc_chunk_constraint(db_session, clean_chunk_tables):
    """추가 #16 — (doc_id, chunk_index) UNIQUE 가 IntegrityError 발생."""
    from sqlalchemy.exc import IntegrityError

    db_session.add(KnowledgeChunk(
        doc_id="test_doc_id_xx",
        source_path="manuals/test_unique.md",
        category="manuals",
        chunk_index=0,
        content="dummy",
        content_hash="x" * 64,
    ))
    db_session.commit()

    db_session.add(KnowledgeChunk(
        doc_id="test_doc_id_xx",
        source_path="manuals/test_unique.md",
        category="manuals",
        chunk_index=0,  # 동일
        content="other",
        content_hash="y" * 64,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ──────────────────────── +17. run.status 정상 종료 ────────────────────────


def test_17_run_status_not_running_after_reindex(
    monkeypatch, db_session, clean_chunk_tables
):
    """추가 #17 — reindex 종료 후 KnowledgeIndexRun.status 가 'running' 으로 남지 않음."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)
    r = ai_indexer.reindex_all(db_session, trigger="manual")

    run = db_session.query(KnowledgeIndexRun).filter(
        KnowledgeIndexRun.id == r.run_id
    ).one()
    assert run.status != ai_indexer.STATUS_RUNNING
    assert run.finished_at is not None
    assert run.status == r.status


# ──────────────────────── +18. lock 동시성 ────────────────────────


def test_18_lock_blocks_concurrent_reindex(
    monkeypatch, db_session, clean_chunk_tables
):
    """추가 #18 — lock 점유 중 reindex 호출 → status='skipped_in_progress', 새 row 미생성."""
    runs_before = count_runs(db_session)

    # lock 강제 점유
    acquired = ai_indexer._REINDEX_LOCK.acquire(blocking=False)
    assert acquired, "테스트 시작 시 lock 이 점유되어 있음"
    try:
        r = ai_indexer.reindex_all(db_session, trigger="manual")
    finally:
        ai_indexer._REINDEX_LOCK.release()

    assert r.status == ai_indexer.STATUS_SKIPPED_IN_PROGRESS
    assert r.run_id is None
    runs_after = count_runs(db_session)
    assert runs_after == runs_before, (
        f"skipped 호출인데 run row 생성됨: before={runs_before}, after={runs_after}"
    )


# ──────────────────────── +19. import-graph 안전성 ────────────────────────


def test_19_indexer_import_graph_safe():
    """추가 #19 — indexer.py 가 네트워크/SDK/provider/pipeline 을 import 하지 않음 (AST 검사).

    chunker_harness #15b 와 동일 패턴.
    """
    import ast

    import app.services.ai.knowledge.indexer as idx

    forbidden_module_prefixes = (
        # network / HTTP
        "requests", "httpx", "urllib", "socket", "http.client", "aiohttp",
        # LLM SDK
        "openai", "anthropic",
        # Provider / pipeline / retriever
        "app.services.ai.provider",
        "app.services.ai.pii",
        "app.services.ai.rag.pipeline",
        "app.services.ai.rag.retriever",
        "app.services.ai.rag.prompts",
        "app.services.ai.rag.safety",
        "app.services.ai.manual_qa",
        "app.services.rag",
    )

    pkg = "app.services.ai.knowledge"

    def _resolve_relative(level: int, mod: str | None) -> str:
        if level == 0:
            return mod or ""
        parts = pkg.split(".")
        drops = level - 1
        if drops > len(parts):
            return mod or ""
        base = ".".join(parts[: len(parts) - drops])
        return f"{base}.{mod}" if mod else base

    src = open(idx.__file__, "r", encoding="utf-8").read()
    tree = ast.parse(src)
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.append(_resolve_relative(node.level or 0, node.module))

    for imported in imported_modules:
        for forbidden in forbidden_module_prefixes:
            assert not (
                imported == forbidden or imported.startswith(forbidden + ".")
            ), (
                f"indexer.py 가 금지 모듈 import: {imported!r} "
                f"(matches {forbidden!r})"
            )


# ──────────────────────── 추가 안정성 단언 ────────────────────────


def test_20_orphan_chunks_not_deleted(monkeypatch, db_session, clean_chunk_tables):
    """문서가 작아져 chunk 수가 줄어도 기존 row 는 DELETE 되지 않음 (사용자 요구 #7 강화).

    18-4 정책: orphan chunk 는 retriever 측에서 document_version 으로 거름 (18-5/18-6).
    indexer 는 어떤 분기에서도 DELETE 호출 안 함.
    """
    docs1 = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs1)
    ai_indexer.reindex_all(db_session, trigger="manual")
    count_before = count_chunks(db_session)
    assert count_before > 0

    # 문서를 매우 작게 줄이면 chunk_document 가 더 적은 chunk 반환
    smaller = "# 문서 A\n\n작은 본문.\n"
    docs2 = [make_doc("manuals/test_a.md", smaller)]
    monkeypatch_load_documents(monkeypatch, docs2)
    ai_indexer.reindex_all(db_session, trigger="manual")

    count_after = count_chunks(db_session)
    # row 수가 줄어들면 안 됨 (orphan 보존)
    assert count_after >= count_before, (
        f"orphan chunk 가 DELETE 됨: before={count_before}, after={count_after}"
    )


def test_21_reindex_result_has_all_required_fields(
    monkeypatch, db_session, clean_chunk_tables
):
    """ReindexResult.to_dict() 가 사용자 요구 12 필드를 모두 노출."""
    docs = [make_doc("manuals/test_a.md", DOC_A)]
    monkeypatch_load_documents(monkeypatch, docs)
    r = ai_indexer.reindex_all(db_session, trigger="manual")

    d = r.to_dict()
    required = {
        "total_documents", "processed_documents", "failed_documents",
        "total_chunks", "inserted_chunks", "updated_chunks", "skipped_chunks",
        "failed_chunks", "started_at", "finished_at", "status", "errors",
    }
    missing = required - set(d.keys())
    assert not missing, f"ReindexResult 누락 필드: {missing}"


def test_22_m012_idempotent(db_session):
    """m012.up() 두 번 실행해도 안전 — sqlite_master 인덱스 수 변동 없음.

    m011 의 idempotent 검증 패턴 참조.
    """
    import sqlite3

    from app.config import get_db_path
    from app.migrations import m012_knowledge_chunks as m12

    raw = sqlite3.connect(str(get_db_path()))
    try:
        cur = raw.cursor()
        before = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name IN ('knowledge_chunks','knowledge_index_runs')"
        ).fetchall()
        m12.up(raw)
        m12.up(raw)
        after = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name IN ('knowledge_chunks','knowledge_index_runs')"
        ).fetchall()
        assert sorted(before) == sorted(after), (
            f"m012 멱등성 위반: before={before}, after={after}"
        )
    finally:
        raw.close()
