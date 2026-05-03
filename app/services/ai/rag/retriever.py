"""RAG retriever — 18-2 keyword + 18-6 hybrid.

진입점:
  - ``keyword_retrieve(query, *, category, limit)``
        18-2 keyword 검색. Document 단위로 ``knowledge.keyword_index.search_documents``
        위임. raw dict 리스트 (path/category/name/title/snippet/score) 반환.
  - ``hybrid_retrieve(query, *, hybrid_enabled, mode, alpha, beta, top_k, ...)``
        18-6 hybrid 검색. keyword + (옵션) vector 결합.
        - ``hybrid_enabled=False`` (기본 OFF) → keyword 단독 모드와 결과 동등.
        - ``mode == "local_only"`` → vector 경로 시도 자체 차단.
        - vector backend 실패 → keyword fallback (vector_disabled / provider_error).
        - 결과 dedup: chunk_id (있으면) → source_path.
        - final_score = α · norm(keyword_score) + β · norm(vector_score).
  - ``retrieve(query, ...)`` : 18-1 stub 그대로 NotImplementedError 보존
        (테스트 단언 보호 — 정식 진입점은 ``hybrid_retrieve``).

설계 원칙 (docs/ai_rag_architecture_plan.md §15, docs/harnesses/hybrid_harness_plan.md):
  1. **hybrid OFF = keyword 단독 모드와 동등** — 회귀 0 (반드시).
  2. **vector backend 실패 → keyword fallback** — 검색 자체가 중단되지 않음.
  3. **local_only 에서 vector 경로 시도 0** — embedding factory 호출 자체 차단.
  4. **dedup key = chunk_id 우선, source_path fallback** — reranker 가 책임.
  5. **점수 정규화는 reranker.combine() 위임** — α/β 는 caller 가 결정.
  6. **외부 LLM 호출 0** — 본 모듈은 검색만, LLM 호출 없음.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .confidence import compute_confidence, normalize_mode
from .reranker import HybridHit, combine
from .schemas import (
    AI_MODE_LOCAL_ONLY,
    REASON_EMBEDDING_SKIPPED_LOCAL_ONLY,
    REASON_EMBEDDING_SKIPPED_SHORT_QUERY,
    REASON_PROVIDER_ERROR,
    REASON_VECTOR_DISABLED,
    Source,
)
from ..knowledge.keyword_index import search_documents


# ──────────────────────── HybridResult dataclass ────────────────────────


@dataclass
class HybridResult:
    """``hybrid_retrieve`` 응답 — 검색 결과 + 호출 메타 + reason_code.

    필드:
      hits                : ``HybridHit`` 리스트 (final_score 내림차순, top_k 자른 후).
      requested_mode      : 호출자가 요청한 search 모드 ("keyword" | "vector" | "hybrid").
      effective_mode      : 실제 사용된 search 모드 — fallback 발생 시 변경.
      reason_code         : 차단/fallback 사유 (없으면 빈 문자열).
                            응답 / AiUsageLog 양쪽에 그대로 전달.
      vector_attempted    : vector 경로를 시도했는가 (factory 차단 전 boolean).
      vector_failed       : vector 경로가 실패했는가 (true 면 keyword fallback).
      embedding_called    : embedding_provider.embed_query 가 호출되었는가.
      keyword_count       : keyword 결과 수 (정규화 전).
      vector_count        : vector 결과 수 (정규화 전).
      top_score           : final_score 최대 (hits[0].final_score, 없으면 0.0).
      top_score_keyword_raw : keyword raw score 최대 (manual_qa.LOW_SCORE_THRESHOLD
                              호환 — 기존 ``top_score`` int 비교용).
      confidence          : "high" | "low" | "unknown" (top_score 기준).
      alpha / beta        : 실제 사용된 가중치 (vector 비활성/실패 시 1.0/0.0).
      ai_mode             : 호출자가 전달한 모드 (정규화 후).
    """
    hits: list[HybridHit] = field(default_factory=list)
    requested_mode: str = "keyword"
    effective_mode: str = "keyword"
    reason_code: str = ""
    vector_attempted: bool = False
    vector_failed: bool = False
    embedding_called: bool = False
    keyword_count: int = 0
    vector_count: int = 0
    top_score: float = 0.0
    top_score_keyword_raw: int = 0
    confidence: str = "unknown"
    alpha: float = 1.0
    beta: float = 0.0
    ai_mode: str = "local_first"


# ──────────────────────── keyword 진입점 (18-2) ────────────────────────


def keyword_retrieve(
    query: str,
    *,
    category: str = "manuals",
    limit: int = 5,
) -> list[dict]:
    """18-2 keyword 검색 진입점 — Document 단위.

    반환 dict (기존 ``app.services.rag.search.search`` 와 동일 키):
      ``path, category, name, title, snippet, score``.

    ``score`` 가 pipeline 의 confidence/threshold 단계에 필요하므로 raw dict
    리스트를 반환한다. ``Source`` dataclass 변환은 ``to_sources()`` 사용.
    """
    return search_documents(
        query,
        category=category if category else None,
        limit=limit,
    )


def to_sources(raw_results: list[dict]) -> list[Source]:
    """raw dict 리스트 → ``Source`` dataclass 리스트 (UI/응답용)."""
    out: list[Source] = []
    for r in raw_results:
        out.append(
            Source(
                title=str(r.get("title") or r.get("name") or r.get("path", "")),
                path=str(r.get("path", "")),
                snippet=str(r.get("snippet", "")),
            )
        )
    return out


# ──────────────────────── 18-6 hybrid 진입점 ────────────────────────


def hybrid_retrieve(
    query: str,
    *,
    db: Optional[Any] = None,
    embedding_provider: Optional[Any] = None,
    hybrid_enabled: bool = False,
    mode: str = "local_first",
    alpha: float = 0.6,
    beta: float = 0.4,
    top_k: int = 5,
    category: str = "manuals",
) -> HybridResult:
    """keyword + (옵션) vector 결합 검색 — 18-6 정식 진입점.

    인자:
      query              : 검색 질의.
      db                 : SQLAlchemy 세션 (vector 경로 활성 시 필요).
      embedding_provider : ``EmbeddingProvider`` 인스턴스 (vector 경로 활성 시 필요).
      hybrid_enabled     : ``AI_RAG_HYBRID_ENABLED`` 시뮬레이션. False (기본) 시
                           vector 경로 자체 시도 안 함 — keyword 단독 모드와 동등.
      mode               : "local_only" | "local_first" | "ai_assist".
                           local_only 는 vector 경로 자체 차단.
      alpha / beta       : 가중치. vector 비활성/실패 시 자동 (1.0, 0.0) 으로
                           override.
      top_k              : 최종 반환 결과 수.
      category           : keyword/vector 검색 모두 해당 카테고리만 ("manuals").

    반환:
      ``HybridResult`` — hits + 호출 메타 + reason_code.

    동작:
      1. mode 정규화. local_only / hybrid_enabled=False / vector path 부재 →
         keyword 단독.
      2. vector 경로 활성 조건:
         - hybrid_enabled == True
         - mode != "local_only"
         - embedding_provider is not None
         - db is not None
         - is_embeddable_query(query) (caller 검증 안 했으면 본 함수가 검사)
      3. vector 경로 호출:
         - embedding_provider.embed_query(query) → query_vec
         - vector_store.list_vectors_for_query → 후보 (vrow, crow) 페어
         - similarity.top_k → ranked
      4. vector 경로 실패 (어떤 단계든 예외) → keyword fallback +
         reason_code = vector_disabled or provider_error.
      5. reranker.combine 으로 점수 정규화 + dedup + α/β 가중합.
      6. top_k 자르고 HybridResult 반환.

    회귀 보호:
      - hybrid_enabled=False / embedding_provider=None / db=None /
        mode=local_only / vector 실패 → 모두 keyword 단독 결과.
      - 어떤 분기든 keyword_retrieve 는 항상 호출됨 (검색 중단 0).
    """
    # 모드 정규화 — 알 수 없는 모드는 local_first 로 안전 fallback.
    mode_eff = normalize_mode(mode)

    result = HybridResult(
        requested_mode="hybrid" if hybrid_enabled else "keyword",
        effective_mode="keyword",
        ai_mode=mode_eff,
        alpha=1.0,
        beta=0.0,
    )

    # 1) keyword 검색은 항상 실행 (fallback 보장).
    keyword_raw = keyword_retrieve(query, category=category, limit=max(top_k * 2, top_k))
    keyword_hits = _to_keyword_hits(keyword_raw)
    result.keyword_count = len(keyword_hits)
    result.top_score_keyword_raw = (
        int(keyword_raw[0].get("score", 0)) if keyword_raw else 0
    )

    # 2) vector 경로 시도 가능 여부 검사.
    vector_hits: list[HybridHit] = []
    can_try_vector = (
        hybrid_enabled
        and mode_eff != AI_MODE_LOCAL_ONLY
        and embedding_provider is not None
        and db is not None
    )

    if hybrid_enabled and mode_eff == AI_MODE_LOCAL_ONLY:
        # local_only — vector 경로 자체 차단. embedding 호출 0.
        result.reason_code = REASON_EMBEDDING_SKIPPED_LOCAL_ONLY
    elif hybrid_enabled and embedding_provider is None:
        # provider 부재 — vector_disabled 로 keyword fallback.
        result.reason_code = REASON_VECTOR_DISABLED
    elif hybrid_enabled and db is None:
        # db 부재 — vector store 조회 불가.
        result.reason_code = REASON_VECTOR_DISABLED
    elif not hybrid_enabled:
        # hybrid OFF — keyword 단독, 별도 reason_code 없음.
        pass

    if can_try_vector:
        # query 길이 체크 — 짧은 query 는 embedding 가치 없음.
        if not _is_embeddable_query(query):
            result.reason_code = REASON_EMBEDDING_SKIPPED_SHORT_QUERY
        else:
            try:
                vector_hits = _vector_path(
                    query=query,
                    db=db,
                    embedding_provider=embedding_provider,
                    top_k=max(top_k * 2, top_k),
                    category=category,
                    result=result,
                )
            except Exception as e:
                # vector 경로 catastrophic 실패 — keyword fallback.
                # reason_code 는 PROVIDER_ERROR (호출 시도 후 실패) 로 표시.
                result.vector_attempted = True
                result.vector_failed = True
                if not result.reason_code:
                    result.reason_code = REASON_PROVIDER_ERROR
                # PII 누출 방지 — 예외 메시지는 어떤 응답에도 포함 X.
                _ = e  # 의도적 무시 (로그/응답에 노출 X — caller 가 별도 로깅).
                vector_hits = []

    result.vector_count = len(vector_hits)

    # 3) α/β 결정 — vector 결과 없으면 자동 (1.0, 0.0).
    if vector_hits:
        eff_alpha = float(alpha)
        eff_beta = float(beta)
    else:
        eff_alpha = 1.0
        eff_beta = 0.0
    result.alpha = eff_alpha
    result.beta = eff_beta

    # 4) reranker — 점수 정규화 + dedup + α/β 가중합.
    combined = combine(keyword_hits, vector_hits, alpha=eff_alpha, beta=eff_beta)

    # 5) top_k 자르기.
    final_hits = combined[:top_k]
    result.hits = final_hits
    result.top_score = final_hits[0].final_score if final_hits else 0.0
    result.confidence = compute_confidence(result.top_score)

    # 6) effective_mode 결정 — 어떤 source 가 실제 결과를 만들었는가.
    if vector_hits and keyword_hits:
        result.effective_mode = "hybrid"
    elif vector_hits:
        result.effective_mode = "vector"
    else:
        result.effective_mode = "keyword"

    return result


# ──────────────────────── 내부 helper ────────────────────────


def _is_embeddable_query(text: Optional[str]) -> bool:
    """query 가 embedding 가치 있는 길이인지.

    ``vector.embeddings.is_embeddable_query`` 와 동일 조건이지만, vector 패키지
    부재 환경에서도 retriever 가 import 가능하도록 본 함수에서 직접 검사.
    """
    if text is None:
        return False
    if not isinstance(text, str):
        return False
    cleaned = text.strip()
    return len(cleaned) >= 2


def _to_keyword_hits(raw: list[dict]) -> list[HybridHit]:
    """keyword raw dict 리스트 → HybridHit 리스트 (search_mode="keyword")."""
    out: list[HybridHit] = []
    for r in raw:
        out.append(
            HybridHit(
                source_path=str(r.get("path", "")),
                title=str(r.get("title") or r.get("name") or r.get("path", "")),
                snippet=str(r.get("snippet", "")),
                chunk_id=None,
                heading="",
                chunk_index=None,
                keyword_score=float(r.get("score", 0)),
                vector_score=0.0,
                search_mode="keyword",
            )
        )
    return out


def _vector_path(
    *,
    query: str,
    db: Any,
    embedding_provider: Any,
    top_k: int,
    category: str,
    result: HybridResult,
) -> list[HybridHit]:
    """vector 검색 경로 — embed_query → vector store → similarity → HybridHit.

    예외는 caller (``hybrid_retrieve``) 가 catch — 본 함수에서는 raise.
    호출 카운트는 result.embedding_called 로 표시.
    """
    # lazy import — 18-5 vector 패키지 부재 환경에서도 retriever import 가능.
    from ..vector.similarity import top_k as similarity_top_k
    from ..vector.store import decode_embedding, list_vectors_for_query

    result.vector_attempted = True

    # query embedding 호출.
    qvec = embedding_provider.embed_query(query)
    result.embedding_called = True

    if not qvec:
        return []

    provider_name = getattr(embedding_provider, "name", "") or ""
    model = getattr(embedding_provider, "model", "") or ""
    qdim = len(qvec)

    if not provider_name or not model:
        return []

    # candidate vectors 조회 (provider/model/dimension 일치 + category).
    pairs = list_vectors_for_query(
        db,
        provider=provider_name,
        model=model,
        dimension=qdim,
        category=category if category else None,
    )

    if not pairs:
        return []

    candidates: list[tuple[Any, list[float]]] = []
    for vrow, crow in pairs:
        try:
            vec = decode_embedding(vrow, expected_dim=qdim)
        except Exception:
            # dimension mismatch / decode 실패 → 해당 row 건너뜀.
            continue
        # payload 는 (vrow, crow) 페어 — 후속에서 chunk metadata 추출.
        candidates.append(((vrow, crow), vec))

    if not candidates:
        return []

    ranked = similarity_top_k(qvec, candidates, k=top_k)

    out: list[HybridHit] = []
    for (vrow, crow), score in ranked:
        out.append(
            HybridHit(
                source_path=str(crow.source_path or ""),
                title=str(crow.title or crow.source_path or ""),
                snippet=_chunk_snippet(crow.content),
                chunk_id=int(crow.id) if crow.id is not None else None,
                heading=str(crow.heading or ""),
                chunk_index=int(crow.chunk_index) if crow.chunk_index is not None else None,
                keyword_score=0.0,
                vector_score=float(score),
                search_mode="vector",
            )
        )
    return out


def _chunk_snippet(content: Optional[str], *, max_chars: int = 300) -> str:
    """chunk content 의 짧은 발췌 — keyword search snippet 과 동등 길이 (300자)."""
    if not content:
        return ""
    s = str(content).strip()
    if len(s) <= max_chars:
        return s
    return s[:max_chars]


def reset_cache() -> None:
    """retriever 캐시 초기화 — knowledge.loader 캐시도 함께 초기화."""
    from ..knowledge.loader import reset_cache as _reset_loader

    _reset_loader()


# ── 18-1 stub 보존 (회귀 단언 충족) ──
def retrieve(
    query: str,
    *,
    category: str = "manuals",
    limit: int = 5,
    mode: str = "keyword",
) -> list[dict]:
    """18-1 stub — chunk + hybrid 통합 후 18-5 시점에 정식 구현 예정.

    18-2 시점의 keyword 검색은 ``keyword_retrieve()`` 를 사용한다.
    18-6 시점의 hybrid 검색은 ``hybrid_retrieve()`` 를 사용한다.
    """
    _ = (query, category, limit, mode)
    raise NotImplementedError(
        "rag.retriever.retrieve 는 stub 입니다. "
        "keyword 검색은 keyword_retrieve(), hybrid 검색은 hybrid_retrieve() 를 사용하세요."
    )


__all__: list[Any] = [
    "keyword_retrieve",
    "to_sources",
    "retrieve",
    "reset_cache",
    "hybrid_retrieve",
    "HybridResult",
    "HybridHit",
]
