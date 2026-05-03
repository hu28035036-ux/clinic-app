"""Vector harness — 18-5 vector / embedding 검증 helper.

기능:
  - FakeEmbeddingProvider 팩토리 (`make_fake_embedding_provider`)
  - 호출 카운트 단언 헬퍼 (`assert_no_embedding_call`, `assert_embedding_calls`)
  - 외부 호출 0 통합 단언 (`assert_no_external_calls_full`)
  - chunk 직접 INSERT 헬퍼 (`seed_chunks_for_vector_test`) — chunker 호출 0
  - reference cosine (`cosine_reference`) — math.fsum 기반 비교용

상세 설계: ``docs/harnesses/vector_harness_plan.md``,
``docs/checklists/18-5_vector_embedding_checklist.md``.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import KnowledgeChunk
from app.services.ai.vector.embeddings import (
    DEFAULT_FAKE_DIMENSION,
    FakeEmbeddingProvider,
)

# ──────────────────────── factory ────────────────────────


def make_fake_embedding_provider(
    *,
    dimension: int = DEFAULT_FAKE_DIMENSION,
    model: str = "fake-embed-1",
    raise_on_call: bool = False,
) -> FakeEmbeddingProvider:
    """FakeEmbeddingProvider 팩토리.

    옵션:
      ``dimension``     : 출력 벡터 길이 (기본 16)
      ``model``         : 모델명 식별자 (KnowledgeVector.model 에 저장됨)
      ``raise_on_call`` : True 면 호출 시 RuntimeError — local_only 검증용
    """
    return FakeEmbeddingProvider(
        dimension=dimension,
        model=model,
        raise_on_call=raise_on_call,
    )


# ──────────────────────── 단언 ────────────────────────


def assert_no_embedding_call(
    embedding_provider: Any,
    msg: str = "",
) -> None:
    """``len(embedding_provider.calls) == 0`` 단언 — 사용자 요구 #2/#9 핵심."""
    n = len(getattr(embedding_provider, "calls", []) or [])
    assert n == 0, msg or f"expected len(embedding_provider.calls) == 0, got {n}"


def assert_embedding_calls(
    embedding_provider: Any,
    expected: int,
    msg: str = "",
) -> None:
    """호출 횟수 단언 — same_hash skip / 부분 호출 검증."""
    n = len(getattr(embedding_provider, "calls", []) or [])
    assert n == expected, msg or (
        f"expected len(embedding_provider.calls) == {expected}, got {n}"
    )


def assert_no_external_calls_full(
    provider: Any | None = None,
    embedding_provider: Any | None = None,
) -> None:
    """LLM provider + Embedding provider 둘 다 호출 0.

    18-5 의 모든 단위 테스트는 LLM 호출이 무관 — provider 가 주입되면 호출 0 단언.
    """
    if provider is not None:
        n = len(getattr(provider, "calls", []) or [])
        assert n == 0, f"expected len(provider.calls) == 0, got {n}"
    if embedding_provider is not None:
        en = len(getattr(embedding_provider, "calls", []) or [])
        assert en == 0, f"expected len(embedding_provider.calls) == 0, got {en}"


# ──────────────────────── chunk 직접 INSERT ────────────────────────


def seed_chunks_for_vector_test(
    db: Session,
    *,
    contents: list[str],
    category: str = "manuals",
    source_path_prefix: str = "manuals/test_",
    title: str = "테스트 매뉴얼",
) -> list[KnowledgeChunk]:
    """KnowledgeChunk 를 직접 INSERT — chunker 호출 0.

    각 ``content`` 마다 1 row. content_hash 는 ``sha256(content)`` 로 18-3
    chunker 와 동일 방식 (사용자 요구 #6 일관성).

    반환: 삽입된 ``KnowledgeChunk`` 리스트 (id 포함).
    """
    rows: list[KnowledgeChunk] = []
    for i, content in enumerate(contents):
        path = f"{source_path_prefix}{i}.md"
        doc_id = hashlib.sha1(path.encode("utf-8")).hexdigest()
        chunk_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        row = KnowledgeChunk(
            doc_id=doc_id,
            source_path=path,
            category=category,
            title=title,
            heading="",
            section_path="",
            chunk_index=0,
            content=content,
            content_hash=chunk_hash,
            token_count=len(content),
            tags="",
            document_version="",
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


# ──────────────────────── reference helpers ────────────────────────


def cosine_reference(a: list[float], b: list[float]) -> float:
    """reference cosine — similarity.cosine_similarity 검증용 비교 구현.

    ``similarity.py`` 와 의도적으로 별도 구현. 동일 결과면 구현 정합성 입증.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = math.fsum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(math.fsum(x * x for x in a))
    nb = math.sqrt(math.fsum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    sim = dot / (na * nb)
    if sim > 1.0:
        return 1.0
    if sim < -1.0:
        return -1.0
    return sim


def sha256_hex(text: str) -> str:
    """chunker.py:42 와 동일 — content_hash 비교용."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ──────────────────────── 정리 helper ────────────────────────


def cleanup_vector_tables(db: Session) -> None:
    """knowledge_vectors / knowledge_chunks / knowledge_index_runs 비우기.

    각 테스트 fixture teardown 에서 사용 — indexer 정책 위반 아님 (테스트 격리용).
    """
    from app.models.models import KnowledgeIndexRun, KnowledgeVector

    db.query(KnowledgeVector).delete()
    db.query(KnowledgeChunk).delete()
    db.query(KnowledgeIndexRun).delete()
    db.commit()


__all__ = [
    "make_fake_embedding_provider",
    "assert_no_embedding_call",
    "assert_embedding_calls",
    "assert_no_external_calls_full",
    "seed_chunks_for_vector_test",
    "cosine_reference",
    "sha256_hex",
    "cleanup_vector_tables",
]
