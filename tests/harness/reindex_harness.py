"""Reindex 하네스 — 18-4 indexer 검증 helper.

기능:
  - in-memory ``Document`` 팩토리 (loader 우회용)
  - chunk 카운트 헬퍼
  - loader monkeypatch 헬퍼
  - 외부 호출 0 단언
  - DELETE 발생 시 즉시 fail 하는 sentinel

상세 설계: ``docs/checklists/18-4_db_reindex_checklist.md``,
``docs/ai_rag_migration_plan.md`` §6.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from app.models.models import KnowledgeChunk, KnowledgeIndexRun
from app.services.ai.rag.schemas import Document

# ──────────────────────── 팩토리 ────────────────────────


def make_doc(
    path: str,
    raw_text: str,
    *,
    category: str = "manuals",
) -> Document:
    """인라인 Document 팩토리 — loader 를 거치지 않고 indexer 에 주입."""
    return Document(
        path=path,
        category=category,
        raw_text=raw_text,
        content_hash="",
        mtime=0.0,
    )


# ──────────────────────── 카운트 ────────────────────────


def count_chunks(db, *, doc_id: Optional[str] = None) -> int:
    """``knowledge_chunks`` row 수. ``doc_id`` 지정 시 해당 doc 만."""
    q = db.query(KnowledgeChunk)
    if doc_id is not None:
        q = q.filter(KnowledgeChunk.doc_id == doc_id)
    return q.count()


def count_runs(db, *, status: Optional[str] = None) -> int:
    """``knowledge_index_runs`` row 수. ``status`` 지정 시 해당 status 만."""
    q = db.query(KnowledgeIndexRun)
    if status is not None:
        q = q.filter(KnowledgeIndexRun.status == status)
    return q.count()


# ──────────────────────── monkeypatch helper ────────────────────────


def monkeypatch_load_documents(monkeypatch, docs: Iterable[Document]) -> None:
    """``indexer.load_documents`` 를 주어진 docs 반환하도록 patch.

    indexer 가 ``from .loader import load_documents`` 로 가져왔으므로 모듈
    attribute 를 patch 한다 (chunker/loader 자체는 무수정).
    """
    from app.services.ai.knowledge import indexer as _idx
    docs_list = list(docs)
    monkeypatch.setattr(_idx, "load_documents", lambda *a, **kw: list(docs_list))


def monkeypatch_chunker_raises(monkeypatch, error: Exception) -> None:
    """``indexer.chunk_document`` 를 매번 raise 하도록 patch — 실패 시뮬레이션."""
    from app.services.ai.knowledge import indexer as _idx

    def _raise(*_a, **_kw):
        raise error

    monkeypatch.setattr(_idx, "chunk_document", _raise)


def monkeypatch_chunker_raises_for_path(
    monkeypatch, *, fail_path: str, error: Exception
) -> None:
    """특정 ``doc.path`` 일 때만 raise — 부분 실패 시뮬레이션."""
    from app.services.ai.knowledge import indexer as _idx

    original = _idx.chunk_document

    def _conditional(doc, *a, **kw):
        if getattr(doc, "path", None) == fail_path:
            raise error
        return original(doc, *a, **kw)

    monkeypatch.setattr(_idx, "chunk_document", _conditional)


# ──────────────────────── 외부 호출 0 단언 ────────────────────────


def assert_no_external_call(
    provider: Any | None = None,
    embedding_provider: Any | None = None,
) -> None:
    """reindex 동작 중 LLM/Embedding 호출이 0 (사용자 요구 #10/#11).

    indexer 는 chunker 만 호출하므로 자동 0 — 통합 테스트 보조용.
    """
    if provider is not None:
        n = len(getattr(provider, "calls", []) or [])
        assert n == 0, f"expected len(provider.calls) == 0, got {n}"
    if embedding_provider is not None:
        en = len(getattr(embedding_provider, "calls", []) or [])
        assert en == 0, f"expected len(embedding_provider.calls) == 0, got {en}"


__all__ = [
    "make_doc",
    "count_chunks",
    "count_runs",
    "monkeypatch_load_documents",
    "monkeypatch_chunker_raises",
    "monkeypatch_chunker_raises_for_path",
    "assert_no_external_call",
]
