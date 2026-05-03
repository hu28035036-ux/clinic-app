"""Knowledge indexer — 18-4 chunk DB 영속화 + 18-5 vector hook (옵션).

reindex 진입점 + 결과 dataclass + 동시 실행 lock + (18-5) optional embedding 단계.

원칙 (docs/AI_WORKING_RULES.md, docs/ai_rag_migration_plan.md):
  - 외부 LLM 호출 0 (chunker 만 호출).
  - 외부 Embedding 호출 0 — 단, ``embedding_provider`` 인자 명시 시에만 임베딩
    단계 실행. None (default) 이면 18-4 동작 그대로 (회귀 0).
  - reindex 실패 시 기존 chunk 삭제 금지 — 본 모듈은 어떤 분기에서도
    ``db.delete()`` / ``DELETE FROM`` 을 호출하지 않는다.
  - content_hash 동일 → skip (중복 저장 방지, 사용자 요구 #5).
  - 문서 변경 → 영향 chunk 만 in-place UPDATE (사용자 요구 #6).
  - 부분 실패 → 실패 path/error 만 ``KnowledgeIndexRun`` 에 기록, 다른 문서는 진행.
  - 동시 실행 → 비차단 lock 으로 두번째 호출은 즉시 ``skipped_in_progress``.
  - PII / 원문 / API key 절대 로그/에러에 저장 금지 — error 텍스트는 400자 컷.

18-5 vector 단계 (optional):
  - ``reindex_all(embedding_provider=...)`` 로 활성화. None 이면 단계 통째로 skip.
  - chunk row 의 ``content_hash`` 와 기존 vector row 의 ``content_hash`` 비교 →
    동일하면 SKIP (사용자 요구 #5).
  - provider 호출 실패 → ``failed_embeddings`` 카운트 + reindex status 영향 0
    (keyword fallback 정책).

내부 함수 only — 관리자 라우터 / UI 미연결 (사용자 지시문에 의해 명시적 금지).
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ....models.models import KnowledgeChunk, KnowledgeIndexRun
from ..rag.schemas import Chunk, Document
from .chunker import chunk_document
from .loader import load_documents
from .loader import reset_cache as _loader_reset_cache

# ──────────────────────── 상수 / lock ────────────────────────

_REINDEX_LOCK = threading.Lock()
_FAILED_PATH_SEP = "\n"
_ERROR_TEXT_LIMIT = 400  # PII/원문 누출 방지 상한

# status 상수 — KnowledgeIndexRun.status 와 ReindexResult.status 양쪽에 사용
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STATUS_SKIPPED_IN_PROGRESS = "skipped_in_progress"


# ──────────────────────── ReindexResult dataclass ────────────────────────


@dataclass
class ReindexResult:
    """reindex 실행 요약 — 18-4 12개 필드 + run_id + 18-5 vector 7개.

    필드 (18-4 사용자 메시지):
      total_documents / processed_documents / failed_documents
      total_chunks / inserted_chunks / updated_chunks / skipped_chunks / failed_chunks
      started_at / finished_at / status / errors

    필드 (18-5 vector 단계):
      embedded_chunks               : 새로 임베딩 생성된 chunk 수
      skipped_embeddings_same_hash  : content_hash 동일로 skip 한 chunk 수
      skipped_embeddings_no_provider: provider 부재로 통째로 skip 한 chunk 수
      failed_embeddings             : provider 호출 실패 chunk 수
      embedding_provider_name       : 사용한 provider name (예: "fake")
      embedding_model               : 사용한 model (예: "fake-embed-1")
      embedding_dimension           : provider.dimension
      vector_disabled_reason        : "" | "local_only" | "api_key_missing" |
                                      "disabled" | "provider_error" |
                                      "no_provider"
    """
    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    total_chunks: int = 0
    inserted_chunks: int = 0
    updated_chunks: int = 0
    skipped_chunks: int = 0
    failed_chunks: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: str = STATUS_RUNNING
    errors: list[dict] = field(default_factory=list)
    run_id: Optional[int] = None
    # ── 18-5 vector 단계 카운터 (default=0/"" → 18-4 호출자 회귀 0) ──
    embedded_chunks: int = 0
    skipped_embeddings_same_hash: int = 0
    skipped_embeddings_no_provider: int = 0
    failed_embeddings: int = 0
    embedding_provider_name: str = ""
    embedding_model: str = ""
    embedding_dimension: int = 0
    vector_disabled_reason: str = ""

    def to_dict(self) -> dict:
        """응답 형태 — 12개 + run_id + 18-5 vector 8개."""
        return asdict(self)


# ──────────────────────── 진입점 ────────────────────────


def reindex_all(
    db: Session,
    *,
    trigger: str = "manual",
    embedding_provider=None,
    vector_disabled_reason: str = "",
) -> ReindexResult:
    """매뉴얼 전체 reindex 진입점 (internal-only).

    인자:
      db                     : SQLAlchemy 세션 (라우터/테스트가 SessionLocal 로 생성)
      trigger                : "manual" | "startup" | "upgrade" — KnowledgeIndexRun.trigger 에 기록
      embedding_provider     : (18-5 신규, default=None) ``EmbeddingProvider`` 인스턴스.
                               None 이면 vector 단계 통째로 skip — 18-4 호출자 회귀 0.
      vector_disabled_reason : (18-5 신규, default="") factory 차단 사유 전달.
                               "local_only" | "api_key_missing" | "disabled" | ...

    반환:
      ``ReindexResult`` — 동시 실행 시 ``status=skipped_in_progress`` 즉시 반환.

    예외 정책:
      - 문서 단위 실패: catch → result.errors 에 누적, 계속 진행.
      - loader/카탈로그 단위 catastrophic 실패: KnowledgeIndexRun.status=failed
        로 갱신 후 raise — 단, 어떤 분기에서도 기존 chunk row 를 DELETE 하지 않음.
      - vector 단계 실패: status 영향 0 — keyword fallback (사용자 요구 #12).
    """
    if not _REINDEX_LOCK.acquire(blocking=False):
        now = _utc_iso()
        return ReindexResult(
            status=STATUS_SKIPPED_IN_PROGRESS,
            started_at=now,
            finished_at=now,
            vector_disabled_reason=vector_disabled_reason or "",
        )
    try:
        return _reindex_locked(
            db,
            trigger=trigger,
            embedding_provider=embedding_provider,
            vector_disabled_reason=vector_disabled_reason or "",
        )
    finally:
        _REINDEX_LOCK.release()


# ──────────────────────── 내부 구현 ────────────────────────


def _reindex_locked(
    db: Session,
    *,
    trigger: str,
    embedding_provider=None,
    vector_disabled_reason: str = "",
) -> ReindexResult:
    """lock 보유 상태에서 호출되는 본체.

    흐름:
      1. loader 캐시 reset (변경 감지 보장)
      2. KnowledgeIndexRun(status=running) row 생성 + commit → run_id 확보
      3. load_documents() — 전 카테고리
      4. 문서 단위 try/except → 성공 시 db.commit(), 실패 시 db.rollback()
      5. (18-5) embedding_provider 가 주어지면 vector 단계 실행 (옵션)
      6. status 결정 (success/partial/failed) + run row UPDATE + commit
      7. ReindexResult 반환
    """
    started = datetime.utcnow()
    result = ReindexResult(
        started_at=started.isoformat(),
        status=STATUS_RUNNING,
        vector_disabled_reason=vector_disabled_reason or "",
    )
    failed_paths_buf: list[str] = []

    # 1. loader 캐시 reset — 변경된 매뉴얼이 stale dict 로 가려지지 않도록
    try:
        _loader_reset_cache()
    except Exception:
        pass  # cache reset 실패는 치명적이지 않음

    # 2. run row 생성 (run_id 확보)
    run = KnowledgeIndexRun(
        started_at=started,
        status=STATUS_RUNNING,
        trigger=trigger or "manual",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    result.run_id = run.id

    # 3. 문서 로딩 (catastrophic 실패 시 run row 를 failed 로 갱신 후 raise)
    try:
        docs: list[Document] = load_documents()
    except Exception as e:
        _finalize_run(
            db, run, result,
            failed_paths_buf=failed_paths_buf,
            status=STATUS_FAILED,
            extra_error={"path": "<loader>", "error": _short_error(e), "stage": "load"},
        )
        raise

    result.total_documents = len(docs)

    # 4. 문서 단위 처리 — per-doc commit 으로 부분 실패 시 보존
    for doc in docs:
        try:
            _index_one_document(db, doc, result)
            db.commit()
        except Exception as e:
            db.rollback()
            result.failed_documents += 1
            err_entry = {
                "path": doc.path or "<unknown>",
                "error": _short_error(e),
                "stage": "persist",
            }
            result.errors.append(err_entry)
            if doc.path:
                failed_paths_buf.append(doc.path)

    # 5. (18-5) vector 단계 — embedding_provider 가 주어졌을 때만 실행.
    #    실패해도 reindex status 영향 0 (keyword fallback 정책).
    if embedding_provider is not None:
        try:
            _embed_chunks_into_vectors(db, embedding_provider, result)
            db.commit()
        except Exception as e:
            db.rollback()
            # vector 단계 catastrophic 실패도 reindex status 는 영향 없음.
            result.errors.append({
                "path": "<vector>",
                "error": _short_error(e),
                "stage": "embed",
            })
            if not result.vector_disabled_reason:
                result.vector_disabled_reason = "provider_error"
    else:
        # embedding_provider 미주입 — vector 단계 통째로 skip (18-4 동작 유지).
        if not result.vector_disabled_reason:
            result.vector_disabled_reason = "no_provider"

    # 6. 최종 status 결정 + run row 갱신
    final_status = _final_status(result)
    _finalize_run(
        db, run, result,
        failed_paths_buf=failed_paths_buf,
        status=final_status,
    )

    return result


def _index_one_document(db: Session, doc: Document, result: ReindexResult) -> None:
    """단일 문서를 chunking → DB upsert.

    위치 키 (doc_id, chunk_index) 기준으로:
      - 존재 X       → INSERT (inserted_chunks++)
      - 존재 + 동일  → SKIP   (skipped_chunks++)   ← 사용자 요구 #5
      - 존재 + 변경  → UPDATE (updated_chunks++)   ← 사용자 요구 #6

    ``existing`` 잔여(새 산출물에 없는 chunk_index) 는 DELETE 하지 않는다 —
    사용자 요구 #7 + 마이그레이션 §0 정책. 향후 18-5/18-6 의 retriever 가
    document_version 으로 stale 을 거를 수 있도록 metadata 만 보존.
    """
    new_chunks = chunk_document(doc)  # 외부 호출 0 (chunker 는 순수 함수)
    if not new_chunks:
        result.processed_documents += 1
        return

    doc_id = new_chunks[0].doc_id
    existing_rows = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.doc_id == doc_id)
        .all()
    )
    existing: dict[int, KnowledgeChunk] = {row.chunk_index: row for row in existing_rows}

    for ch in new_chunks:
        result.total_chunks += 1
        prev = existing.pop(ch.chunk_index, None)
        if prev is None:
            db.add(_chunk_to_orm(ch))
            result.inserted_chunks += 1
        elif prev.content_hash == ch.content_hash:
            result.skipped_chunks += 1
        else:
            _apply_chunk_to_orm(prev, ch)
            result.updated_chunks += 1

    # 잔여 (existing) 는 의도적으로 DELETE 하지 않음. 사용자 요구 #7 보존.
    db.flush()
    result.processed_documents += 1


def _final_status(result: ReindexResult) -> str:
    """ReindexResult 카운터 기반 최종 status 결정.

    규칙:
      - failed == 0                              → success
      - processed >= 1 (그리고 failed >= 1)      → partial  (적어도 일부 성공)
      - processed == 0 (그리고 failed >= 1)      → failed   (전부 실패)
    """
    if result.failed_documents == 0:
        return STATUS_SUCCESS
    if result.processed_documents >= 1:
        return STATUS_PARTIAL
    return STATUS_FAILED


def _finalize_run(
    db: Session,
    run: KnowledgeIndexRun,
    result: ReindexResult,
    *,
    failed_paths_buf: list[str],
    status: str,
    extra_error: Optional[dict] = None,
) -> None:
    """run row 에 모든 카운터 기록 + commit. result 에도 동기화."""
    if extra_error:
        result.errors.append(extra_error)

    result.status = status
    result.finished_at = _utc_iso()

    run.finished_at = datetime.utcnow()
    run.status = status
    run.total_documents = result.total_documents
    run.processed_documents = result.processed_documents
    run.failed_documents = result.failed_documents
    run.total_chunks = result.total_chunks
    run.inserted_chunks = result.inserted_chunks
    run.updated_chunks = result.updated_chunks
    run.skipped_chunks = result.skipped_chunks
    run.failed_chunks = result.failed_chunks
    run.failed_paths = _FAILED_PATH_SEP.join(failed_paths_buf)
    run.errors = _safe_json(result.errors)
    db.add(run)
    db.commit()


# ──────────────────────── ORM 변환 helper ────────────────────────


def _chunk_to_orm(ch: Chunk) -> KnowledgeChunk:
    return KnowledgeChunk(
        doc_id=ch.doc_id,
        source_path=ch.source_path,
        category=ch.category,
        title=ch.title,
        heading=ch.heading,
        section_path=ch.section_path,
        chunk_index=ch.chunk_index,
        content=ch.content,
        content_hash=ch.content_hash,
        token_count=ch.token_count,
        tags=ch.tags,
        document_version=ch.document_version,
    )


def _apply_chunk_to_orm(row: KnowledgeChunk, ch: Chunk) -> None:
    """기존 row 를 새 chunk 로 in-place UPDATE (id/doc_id/chunk_index 보존)."""
    row.source_path = ch.source_path
    row.category = ch.category
    row.title = ch.title
    row.heading = ch.heading
    row.section_path = ch.section_path
    row.content = ch.content
    row.content_hash = ch.content_hash
    row.token_count = ch.token_count
    row.tags = ch.tags
    row.document_version = ch.document_version
    # updated_at 은 SQLAlchemy onupdate 가 자동 처리


# ──────────────────────── 18-5 vector 단계 ────────────────────────


def _embed_chunks_into_vectors(db: Session, embedding_provider, result: ReindexResult) -> None:
    """모든 chunk 에 대해 (provider, model) 키 vector 생성/업데이트.

    흐름:
      1. ``KnowledgeChunk`` 전체 조회.
      2. 각 chunk 별 ``get_vector_with_hash`` 로 same_hash skip 판정.
        - 일치 → ``skipped_embeddings_same_hash`` ++
        - 불일치/없음 → 임베딩 대상 리스트에 추가
      3. 대상 chunk 들의 content 만 모아 ``embed_documents`` 1회 호출.
      4. ``upsert_vector`` per chunk → ``embedded_chunks`` ++
      5. 단일 chunk 단위 예외도 catch 하여 ``failed_embeddings`` 기록.

    PII/원문 보호:
      - chunk content 자체는 매뉴얼 텍스트만 들어옴 (PII 없음 — knowledge/manuals).
      - provider 호출 실패 시 예외 메시지는 ``_short_error()`` 로 400자 컷.

    의존:
      - 본 함수는 ``app.services.ai.vector.store`` 의 ``upsert_vector`` /
        ``get_vector_with_hash`` 사용. 18-5 시점 신규 의존 (vector 패키지 부재
        환경에서는 호출자가 ``embedding_provider=None`` 으로 통과).
    """
    # lazy import — 18-5 vector 패키지 부재 환경에서도 indexer module load 가능.
    from ..vector.store import get_vector_with_hash, upsert_vector

    provider_name = getattr(embedding_provider, "name", "") or ""
    model = getattr(embedding_provider, "model", "") or ""
    dimension = int(getattr(embedding_provider, "dimension", 0) or 0)

    if not provider_name or not model or dimension <= 0:
        # provider 메타 부족 — 전체 skip.
        result.skipped_embeddings_no_provider += 1
        if not result.vector_disabled_reason:
            result.vector_disabled_reason = "no_provider"
        return

    result.embedding_provider_name = provider_name
    result.embedding_model = model
    result.embedding_dimension = dimension

    # 모든 chunk row 수집.
    chunks: list[KnowledgeChunk] = db.query(KnowledgeChunk).all()
    if not chunks:
        return

    # same_hash skip 판정 — 임베딩 대상만 추출.
    targets: list[tuple[KnowledgeChunk, str]] = []  # (chunk_row, content_for_embed)
    for c in chunks:
        existing = get_vector_with_hash(
            db,
            chunk_id=c.id,
            provider=provider_name,
            model=model,
            content_hash=c.content_hash,
        )
        if existing is not None:
            # content_hash 동일 + dimension 동일 시 SKIP (사용자 요구 #5).
            if existing.dimension == dimension:
                result.skipped_embeddings_same_hash += 1
                continue
        targets.append((c, c.content))

    if not targets:
        return

    # 배치 임베딩 — provider 가 raise 하면 전체 batch 실패.
    texts = [t[1] for t in targets]
    try:
        vectors = embedding_provider.embed_documents(texts)
    except Exception as e:
        # provider 오류 → 모든 대상 chunk 실패 처리. reindex status 는 영향 없음.
        result.failed_embeddings += len(targets)
        result.errors.append({
            "path": "<vector_batch>",
            "error": _short_error(e),
            "stage": "embed",
        })
        if not result.vector_disabled_reason:
            result.vector_disabled_reason = "provider_error"
        return

    if len(vectors) != len(targets):
        result.failed_embeddings += len(targets)
        result.errors.append({
            "path": "<vector_batch>",
            "error": f"provider returned {len(vectors)} vectors for {len(targets)} chunks",
            "stage": "embed",
        })
        if not result.vector_disabled_reason:
            result.vector_disabled_reason = "provider_error"
        return

    # upsert per chunk — 단일 chunk 실패가 다른 chunk 에 영향 없도록 try 각자.
    for (chunk_row, _), vec in zip(targets, vectors):
        try:
            _row, status = upsert_vector(
                db,
                chunk_id=chunk_row.id,
                provider=provider_name,
                model=model,
                dimension=dimension,
                embedding=vec,
                content_hash=chunk_row.content_hash,
            )
            if status in ("inserted", "updated"):
                result.embedded_chunks += 1
            else:
                # skipped_same_hash 가 store 단에서 발생할 수도 (race)
                result.skipped_embeddings_same_hash += 1
        except Exception as e:
            result.failed_embeddings += 1
            result.errors.append({
                "path": chunk_row.source_path or f"<chunk#{chunk_row.id}>",
                "error": _short_error(e),
                "stage": "embed",
            })


# ──────────────────────── 안전 helper ────────────────────────


def _short_error(e: BaseException) -> str:
    """예외 → 짧은 텍스트. PII/원문 누출 방지 상한 적용."""
    try:
        text = f"{type(e).__name__}: {e}"
    except Exception:
        text = type(e).__name__
    if len(text) > _ERROR_TEXT_LIMIT:
        text = text[:_ERROR_TEXT_LIMIT] + "...[truncated]"
    return text


def _safe_json(obj) -> str:
    """JSON 직렬화 — 비-ASCII (한국어) 보존, 실패 시 빈 배열."""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return "[]"


def _utc_iso() -> str:
    return datetime.utcnow().isoformat()


__all__ = [
    "ReindexResult",
    "reindex_all",
    "STATUS_RUNNING",
    "STATUS_SUCCESS",
    "STATUS_PARTIAL",
    "STATUS_FAILED",
    "STATUS_SKIPPED_IN_PROGRESS",
]
