"""Vector store — knowledge_vectors 테이블 wrapper. 18-5.

기능:
  - ``upsert_vector``         : (chunk_id, provider, model) 키 upsert.
                               content_hash 동일 → SKIP (재생성 방지).
  - ``find_vector``           : 조회 (없으면 None).
  - ``get_vector_with_hash``  : content_hash 일치 row 만 반환 (same_hash 판정).
  - ``list_vectors_for_query``: top_k 검색 입력 — (KnowledgeVector, KnowledgeChunk) 페어.
                               dimension 일치 필터 (사용자 요구 #13 안전 실패).
  - ``delete_orphan_vectors`` : chunk 가 없는 vector row 정리 (FK CASCADE 보강).
  - ``decode_embedding``      : embedding_json/blob → list[float]. dim 검증.
  - ``encode_embedding``      : list[float] → embedding_json (저장용).

설계 원칙 (사용자 요구 + ai_rag_migration_plan §3/§7):
  - 외부 호출 0. 순수 DB wrapper.
  - dimension mismatch → ``VectorDimensionMismatch`` raise (caller 가 fallback).
  - content_hash 동일 → SKIP (사용자 요구 #5).
  - chunk 삭제 시 vector 정합성 — ON DELETE CASCADE 가 1차 보장 + 본 모듈에
    수동 정리 helper 도 제공.
"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from ....models.models import KnowledgeChunk, KnowledgeVector
from .embeddings import VectorDimensionMismatch


# ──────────────────────── encode/decode ────────────────────────


def encode_embedding(embedding: list[float]) -> str:
    """list[float] → JSON 문자열 (embedding_json 저장용).

    ascii=True 로 강제 — 한글/특수문자 입력 가능성 0 이지만 안전.
    """
    if not isinstance(embedding, list):
        raise TypeError(f"embedding must be list[float], got {type(embedding).__name__}")
    return json.dumps(embedding, ensure_ascii=True)


def decode_embedding(row: KnowledgeVector, *, expected_dim: Optional[int] = None) -> list[float]:
    """KnowledgeVector row → list[float].

    ``embedding_json`` 우선, 없으면 ``embedding_blob`` (struct 패킹) — 본 세션
    시점은 JSON 만 사용하지만 미래 호환을 위해 분기 유지.

    ``expected_dim`` 지정 시 길이 검증 — 불일치 ``VectorDimensionMismatch``.
    """
    if row.embedding_json:
        try:
            data = json.loads(row.embedding_json)
        except Exception as e:
            raise ValueError(f"vector#{row.id} embedding_json decode failed") from e
        if not isinstance(data, list):
            raise ValueError(f"vector#{row.id} embedding_json must be a JSON list")
        out = [float(x) for x in data]
    elif row.embedding_blob:
        # 18-5 시점은 BLOB 미사용 — 후일 struct.unpack 로 복원.
        raise NotImplementedError("embedding_blob decoding is reserved for future versions")
    else:
        raise ValueError(f"vector#{row.id} has neither embedding_json nor embedding_blob")

    # row.dimension 과 길이 검증 — DB 기록과 실제 데이터 정합성.
    if len(out) != row.dimension:
        raise VectorDimensionMismatch(
            expected=row.dimension, got=len(out),
            where=f"row#{row.id} stored",
        )
    if expected_dim is not None and len(out) != expected_dim:
        raise VectorDimensionMismatch(
            expected=expected_dim, got=len(out),
            where=f"row#{row.id} vs query",
        )
    return out


# ──────────────────────── upsert / find ────────────────────────


def upsert_vector(
    db: Session,
    *,
    chunk_id: int,
    provider: str,
    model: str,
    dimension: int,
    embedding: list[float],
    content_hash: str,
) -> tuple[KnowledgeVector, str]:
    """(chunk_id, provider, model) 키 upsert.

    동작:
      - 기존 row 없음               → INSERT (status="inserted")
      - 기존 row + 동일 content_hash → SKIP (status="skipped_same_hash")
      - 기존 row + 다른 content_hash → UPDATE (status="updated")

    사용자 요구 #5/#6:
      - content_hash 같으면 재생성 X (skipped_same_hash)
      - content_hash 변경 시만 UPDATE

    pre-condition:
      - len(embedding) == dimension (mismatch 시 ``VectorDimensionMismatch`` raise)

    반환: ``(row, status)``. status ∈ {"inserted", "updated", "skipped_same_hash"}
    """
    if len(embedding) != dimension:
        raise VectorDimensionMismatch(
            expected=dimension, got=len(embedding),
            where=f"upsert chunk={chunk_id}",
        )

    existing: Optional[KnowledgeVector] = (
        db.query(KnowledgeVector)
        .filter(
            KnowledgeVector.chunk_id == chunk_id,
            KnowledgeVector.provider == provider,
            KnowledgeVector.model == model,
        )
        .one_or_none()
    )

    encoded = encode_embedding(embedding)

    if existing is None:
        row = KnowledgeVector(
            chunk_id=chunk_id,
            provider=provider,
            model=model,
            dimension=dimension,
            embedding_json=encoded,
            embedding_blob=None,
            content_hash=content_hash,
        )
        db.add(row)
        db.flush()
        return row, "inserted"

    if existing.content_hash == content_hash and existing.dimension == dimension:
        # 사용자 요구 #5 — 재생성 skip.
        return existing, "skipped_same_hash"

    # 변경 — UPDATE in-place.
    existing.dimension = dimension
    existing.embedding_json = encoded
    existing.embedding_blob = None
    existing.content_hash = content_hash
    db.flush()
    return existing, "updated"


def find_vector(
    db: Session,
    *,
    chunk_id: int,
    provider: str,
    model: str,
) -> Optional[KnowledgeVector]:
    """(chunk_id, provider, model) 키 단건 조회. 없으면 None."""
    return (
        db.query(KnowledgeVector)
        .filter(
            KnowledgeVector.chunk_id == chunk_id,
            KnowledgeVector.provider == provider,
            KnowledgeVector.model == model,
        )
        .one_or_none()
    )


def get_vector_with_hash(
    db: Session,
    *,
    chunk_id: int,
    provider: str,
    model: str,
    content_hash: str,
) -> Optional[KnowledgeVector]:
    """content_hash 일치 row 만 반환 — same_hash skip 판정용 (사용자 요구 #6).

    indexer 가 chunk 의 현재 content_hash 와 비교하기 위해 호출. 일치하면
    재생성 불필요, 불일치/없음이면 새로 임베딩.
    """
    row = find_vector(db, chunk_id=chunk_id, provider=provider, model=model)
    if row is None:
        return None
    if row.content_hash != content_hash:
        return None
    return row


# ──────────────────────── 검색용 list ────────────────────────


def list_vectors_for_query(
    db: Session,
    *,
    provider: str,
    model: str,
    dimension: int,
    category: Optional[str] = None,
) -> list[tuple[KnowledgeVector, KnowledgeChunk]]:
    """top_k 검색 입력 — (vector_row, chunk_row) 페어.

    dimension 불일치 row 는 자동 제외 (사용자 요구 #13 — 안전 실패).
    category 인자 지정 시 해당 카테고리 chunk 만 반환 (manuals/sms_guides).

    JOIN 으로 한 번에 — chunk 가 없는 orphan vector 는 자동 제외.
    """
    q = (
        db.query(KnowledgeVector, KnowledgeChunk)
        .join(KnowledgeChunk, KnowledgeChunk.id == KnowledgeVector.chunk_id)
        .filter(
            KnowledgeVector.provider == provider,
            KnowledgeVector.model == model,
            KnowledgeVector.dimension == dimension,
        )
    )
    if category:
        q = q.filter(KnowledgeChunk.category == category)
    rows = q.all()
    return [(v, c) for v, c in rows]


# ──────────────────────── 정합성 helper ────────────────────────


def delete_orphan_vectors(db: Session) -> int:
    """chunk 가 없는 vector row 제거 — FK CASCADE 보강 + admin tool 슬롯.

    SQLAlchemy 세션 단위 호출. ON DELETE CASCADE 가 정상 작동하면 호출 불필요지만
    SQLite 환경에서 PRAGMA foreign_keys 가 OFF 인 경우의 fallback.

    ⚠️  본 함수는 indexer/router 가 자동 호출하지 않는다 — admin/maintenance
    도구가 명시적으로 호출. 실수 호출 방지 위해 별도 함수로 격리.
    """
    chunk_ids_subq = db.query(KnowledgeChunk.id).subquery()
    orphan_q = db.query(KnowledgeVector).filter(
        ~KnowledgeVector.chunk_id.in_(chunk_ids_subq)
    )
    count = orphan_q.count()
    if count > 0:
        for row in orphan_q.all():
            db.delete(row)
        db.flush()
    return count


# ──────────────────────── 통계 ────────────────────────


def count_vectors(
    db: Session,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> int:
    """vector row 수 — 관리자 화면/테스트용."""
    q = db.query(KnowledgeVector)
    if provider is not None:
        q = q.filter(KnowledgeVector.provider == provider)
    if model is not None:
        q = q.filter(KnowledgeVector.model == model)
    return q.count()


__all__ = [
    "encode_embedding",
    "decode_embedding",
    "upsert_vector",
    "find_vector",
    "get_vector_with_hash",
    "list_vectors_for_query",
    "delete_orphan_vectors",
    "count_vectors",
]
