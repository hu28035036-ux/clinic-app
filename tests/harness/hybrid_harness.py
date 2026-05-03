"""Hybrid harness — 18-6 hybrid retriever 검증 helper.

기능:
  - ``hybrid_retriever()``      : ``hybrid_retrieve`` factory (alpha/beta/top_k 지정).
  - ``seed_chunk_with_vector``  : KnowledgeChunk + KnowledgeVector 동시 INSERT.
  - ``assert_retriever_deterministic`` : 같은 입력으로 두 번 호출해도 같은 결과.
  - ``assert_no_external_calls_full``  : LLM/Embedding provider 둘 다 호출 0.
  - ``make_keyword_hit`` / ``make_vector_hit`` : reranker 단위 테스트용 HybridHit.

상세 설계: ``docs/harnesses/hybrid_harness_plan.md``,
``docs/checklists/18-6_hybrid_retriever_checklist.md``.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.models.models import KnowledgeChunk, KnowledgeVector
from app.services.ai.rag.reranker import HybridHit
from app.services.ai.rag.retriever import HybridResult, hybrid_retrieve
from app.services.ai.vector.embeddings import (
    DEFAULT_FAKE_DIMENSION,
    FakeEmbeddingProvider,
)
from app.services.ai.vector.store import encode_embedding

# ──────────────────────── factory ────────────────────────


def hybrid_retriever_factory(
    *,
    alpha: float = 0.6,
    beta: float = 0.4,
    top_k: int = 5,
    category: str = "manuals",
    hybrid_enabled: bool = True,
    mode: str = "local_first",
) -> Callable[..., HybridResult]:
    """``hybrid_retrieve`` 부분 적용 factory.

    호출 시그니처:
      ``factory(query, db=..., embedding_provider=...)`` → ``HybridResult``.

    테스트가 같은 alpha/beta/top_k 로 여러 query 를 검사할 때 편의용.
    """
    def _call(
        query: str,
        *,
        db: Optional[Any] = None,
        embedding_provider: Optional[Any] = None,
        hybrid_enabled_override: Optional[bool] = None,
        mode_override: Optional[str] = None,
    ) -> HybridResult:
        return hybrid_retrieve(
            query,
            db=db,
            embedding_provider=embedding_provider,
            hybrid_enabled=(
                hybrid_enabled_override if hybrid_enabled_override is not None
                else hybrid_enabled
            ),
            mode=mode_override if mode_override is not None else mode,
            alpha=alpha,
            beta=beta,
            top_k=top_k,
            category=category,
        )

    return _call


# ──────────────────────── seed helper ────────────────────────


def seed_chunk_with_vector(
    db: Session,
    *,
    content: str,
    title: str = "테스트 매뉴얼",
    heading: str = "",
    chunk_index: int = 0,
    source_path: Optional[str] = None,
    category: str = "manuals",
    embedding_provider: Optional[FakeEmbeddingProvider] = None,
) -> tuple[KnowledgeChunk, Optional[KnowledgeVector]]:
    """단일 KnowledgeChunk + (옵션) KnowledgeVector 직접 INSERT.

    ``embedding_provider`` 가 주어지면 chunk content 를 임베딩해 KnowledgeVector
    도 함께 생성. 주어지지 않으면 chunk 만.

    각 호출마다 unique source_path (내부 카운터 X — caller 가 인덱스 다르게 줘야 함).
    """
    if source_path is None:
        # 내용 hash 로 path 고유화 — 테스트에서 같은 content 두 번 시드 방지.
        digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
        source_path = f"manuals/test_{digest}.md"

    doc_id = hashlib.sha1(source_path.encode("utf-8")).hexdigest()
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    chunk = KnowledgeChunk(
        doc_id=doc_id,
        source_path=source_path,
        category=category,
        title=title,
        heading=heading,
        section_path="",
        chunk_index=chunk_index,
        content=content,
        content_hash=content_hash,
        token_count=len(content),
        tags="",
        document_version="",
    )
    db.add(chunk)
    db.flush()

    vector_row: Optional[KnowledgeVector] = None
    if embedding_provider is not None:
        vec = embedding_provider.embed_documents([content])[0]
        vector_row = KnowledgeVector(
            chunk_id=chunk.id,
            provider=embedding_provider.name,
            model=embedding_provider.model,
            dimension=embedding_provider.dimension,
            embedding_json=encode_embedding(vec),
            embedding_blob=None,
            content_hash=content_hash,
        )
        db.add(vector_row)
        db.flush()

    db.commit()
    db.refresh(chunk)
    if vector_row is not None:
        db.refresh(vector_row)
    return chunk, vector_row


def cleanup_hybrid_tables(db: Session) -> None:
    """KnowledgeVector / KnowledgeChunk 비우기 — 각 테스트 fixture teardown."""
    db.query(KnowledgeVector).delete()
    db.query(KnowledgeChunk).delete()
    db.commit()


# ──────────────────────── 단언 helper ────────────────────────


def assert_retriever_deterministic(
    query: str,
    *,
    db: Any,
    embedding_provider: Optional[Any],
    hybrid_enabled: bool = True,
    mode: str = "local_first",
    alpha: float = 0.6,
    beta: float = 0.4,
    top_k: int = 5,
    runs: int = 2,
) -> HybridResult:
    """같은 입력으로 ``runs`` 번 호출 — 결과가 모두 같은지 단언.

    결정성 핵심: hits 의 (source_path, chunk_id, final_score, search_mode)
    튜플이 모든 run 에서 동일해야 함. 부동소수점 정확 비교 (FakeEmbeddingProvider
    는 결정적이므로 정확 일치).

    반환: 첫 번째 run 의 result (캐싱 검증용).
    """
    results: list[HybridResult] = []
    for _ in range(runs):
        r = hybrid_retrieve(
            query,
            db=db,
            embedding_provider=embedding_provider,
            hybrid_enabled=hybrid_enabled,
            mode=mode,
            alpha=alpha,
            beta=beta,
            top_k=top_k,
        )
        results.append(r)

    first = results[0]
    for i, r in enumerate(results[1:], start=2):
        first_keys = [
            (h.source_path, h.chunk_id, h.final_score, h.search_mode)
            for h in first.hits
        ]
        cur_keys = [
            (h.source_path, h.chunk_id, h.final_score, h.search_mode)
            for h in r.hits
        ]
        assert first_keys == cur_keys, (
            f"hybrid_retrieve non-deterministic at run #{i}\n"
            f"  first: {first_keys}\n"
            f"  curr:  {cur_keys}"
        )
        assert first.effective_mode == r.effective_mode
        assert first.reason_code == r.reason_code
    return first


def assert_no_external_calls_full(
    provider: Any | None = None,
    embedding_provider: Any | None = None,
) -> None:
    """LLM provider + Embedding provider 둘 다 호출 0 단언.

    18-6 hybrid retriever 자체는 LLM 호출 0 — provider 가 주입되었으면 호출 0.
    """
    if provider is not None:
        n = len(getattr(provider, "calls", []) or [])
        assert n == 0, f"expected len(provider.calls) == 0, got {n}"
    if embedding_provider is not None:
        en = len(getattr(embedding_provider, "calls", []) or [])
        assert en == 0, f"expected len(embedding_provider.calls) == 0, got {en}"


def assert_no_embedding_call(embedding_provider: Any, msg: str = "") -> None:
    """embedding_provider 호출 0 단언 — local_only / hybrid disabled 케이스용."""
    n = len(getattr(embedding_provider, "calls", []) or [])
    assert n == 0, msg or f"expected len(embedding_provider.calls) == 0, got {n}"


def assert_embedding_calls(embedding_provider: Any, expected: int, msg: str = "") -> None:
    n = len(getattr(embedding_provider, "calls", []) or [])
    assert n == expected, msg or (
        f"expected len(embedding_provider.calls) == {expected}, got {n}"
    )


# ──────────────────────── reranker 단위 테스트 helper ────────────────────────


def make_keyword_hit(
    *,
    source_path: str,
    keyword_score: float,
    title: str = "",
    snippet: str = "",
    chunk_id: Optional[int] = None,
) -> HybridHit:
    """reranker 단위 테스트용 keyword HybridHit."""
    return HybridHit(
        source_path=source_path,
        title=title or source_path,
        snippet=snippet or f"snippet for {source_path}",
        chunk_id=chunk_id,
        keyword_score=float(keyword_score),
        vector_score=0.0,
        search_mode="keyword",
    )


def make_vector_hit(
    *,
    source_path: str,
    vector_score: float,
    chunk_id: int,
    title: str = "",
    snippet: str = "",
    heading: str = "",
    chunk_index: int = 0,
) -> HybridHit:
    """reranker 단위 테스트용 vector HybridHit."""
    return HybridHit(
        source_path=source_path,
        title=title or source_path,
        snippet=snippet or f"snippet for {source_path}#{chunk_index}",
        chunk_id=int(chunk_id),
        heading=heading,
        chunk_index=chunk_index,
        keyword_score=0.0,
        vector_score=float(vector_score),
        search_mode="vector",
    )


# ──────────────────────── factory (FakeEmbeddingProvider) ────────────────────────


def make_hybrid_fake_embedding_provider(
    *,
    dimension: int = DEFAULT_FAKE_DIMENSION,
    model: str = "fake-embed-1",
    raise_on_call: bool = False,
) -> FakeEmbeddingProvider:
    """FakeEmbeddingProvider — vector_harness 와 동일하지만 hybrid 컨텍스트 명시."""
    return FakeEmbeddingProvider(
        dimension=dimension,
        model=model,
        raise_on_call=raise_on_call,
    )


__all__ = [
    "hybrid_retriever_factory",
    "seed_chunk_with_vector",
    "cleanup_hybrid_tables",
    "assert_retriever_deterministic",
    "assert_no_external_calls_full",
    "assert_no_embedding_call",
    "assert_embedding_calls",
    "make_keyword_hit",
    "make_vector_hit",
    "make_hybrid_fake_embedding_provider",
]
