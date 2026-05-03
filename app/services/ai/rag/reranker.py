"""RAG reranker — 18-6 hybrid retriever 점수 정규화 + α/β 가중 결합 + dedup.

설계 원칙 (docs/ai_rag_architecture_plan.md §15, docs/harnesses/hybrid_harness_plan.md §6):

  1. **정규화는 max-normalization** — 각 source 의 최대값으로 나눠 [0, 1] 로
     맞춘다. raw 점수 직결합 금지: keyword score=5(token), vector score=0.7
     (cosine) 면 raw 결합 시 keyword 가 항상 압도. 정규화로 동일 척도화.
     - keyword_score 가 음수일 일 없음 (token intersection + bonus).
     - vector_score 는 cosine 이므로 [-1, 1]. 본 reranker 는 0 미만은 0 으로
       clamp 후 정규화 (음의 유사도는 의미 없음 — 무관 hit).

  2. **final_score = α · norm(keyword_score) + β · norm(vector_score)**
     - α + β 가 1 일 필요는 없다 (운영 튜닝 자유도). 본 모듈은 가중합만 한다.
     - α/β 는 호출자(``hybrid_retrieve``) 가 결정 — vector 비활성/실패 시
       자동 (1.0, 0.0). 본 reranker 는 받은 값 그대로 사용.

  3. **dedup key** — chunk_id 우선, 없으면 source_path.
     - vector hit 은 항상 chunk_id 가짐 (KnowledgeChunk.id).
     - keyword hit 은 document 단위라 chunk_id 부재 → source_path 로 dedup.
     - 한 결과에 chunk_id 가 있고 다른 결과에 없는데 source_path 가 같으면 →
       merge (chunk_id 가 있는 쪽이 "더 구체적인" 정보로 간주).

  4. **dedup 시 점수는 max() 대신 source 별 보존**:
     - keyword_score: 두 hit 중 keyword 쪽의 값 (0 이면 다른쪽이 그대로).
     - vector_score: 두 hit 중 vector 쪽의 값.
     - 그 다음 alpha/beta 로 final_score 재계산.
     - 결과: 한쪽만 hit 한 경우에도 다른쪽 점수 0 으로 final_score 산출 가능.

  5. **정렬은 final_score 내림차순** — 동률은 입력 순서 보존
     (Python ``sorted`` stable 활용). 결정성 핵심.

본 모듈은 외부 호출 0 — 순수 함수. provider/embedding 비의존.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────── dataclass ────────────────────────


@dataclass
class HybridHit:
    """Hybrid retriever 단일 결과 — Source 호환 + 점수 메타.

    필드:
      source_path / title / snippet : ``Source`` 와 호환되는 UI 노출 메타.
      chunk_id                      : KnowledgeChunk.id (vector hit 시 채움).
      heading / chunk_index         : chunk metadata (vector hit 시 채움).
      keyword_score                 : raw keyword score (정규화 전).
      vector_score                  : raw vector score (정규화 전, [0, 1] clamp 후).
      keyword_score_norm            : 정규화된 keyword score [0, 1].
      vector_score_norm             : 정규화된 vector score [0, 1].
      final_score                   : α · keyword_norm + β · vector_norm.
      search_mode                   : "keyword" | "vector" | "hybrid" — 어떤
                                      source 가 hit 했는지 표시.

    dedup key (``dedup_key()``): chunk_id 가 있으면 ``("c", chunk_id)``,
    없으면 ``("p", source_path)``.
    """
    source_path: str = ""
    title: str = ""
    snippet: str = ""
    chunk_id: Optional[int] = None
    heading: str = ""
    chunk_index: Optional[int] = None
    keyword_score: float = 0.0
    vector_score: float = 0.0
    keyword_score_norm: float = 0.0
    vector_score_norm: float = 0.0
    final_score: float = 0.0
    search_mode: str = "keyword"

    def dedup_key(self) -> tuple:
        """dedup 키 — chunk_id 우선, 없으면 source_path."""
        if self.chunk_id is not None:
            return ("c", int(self.chunk_id))
        return ("p", self.source_path or "")


# ──────────────────────── 정규화 ────────────────────────


def _max_normalize(values: list[float]) -> list[float]:
    """[0, max] → [0, 1] 로 정규화. 모든 값이 0 이면 모두 0 반환.

    - 입력은 0 이상 가정 (음수는 caller 가 0 으로 clamp).
    - max 가 0 이면 division-by-zero 방지로 모두 0.
    - 결정적 — 같은 입력 → 같은 출력.
    """
    if not values:
        return []
    mx = max(values)
    if mx <= 0.0:
        return [0.0 for _ in values]
    return [max(0.0, v) / mx for v in values]


def _clamp_pos(x: float) -> float:
    """음수 → 0, 그 외 그대로. cosine 음의 유사도 제거용."""
    return x if x > 0.0 else 0.0


# ──────────────────────── 결합 ────────────────────────


def combine(
    keyword_hits: list[HybridHit],
    vector_hits: list[HybridHit],
    *,
    alpha: float = 0.6,
    beta: float = 0.4,
) -> list[HybridHit]:
    """keyword + vector 결과를 α/β 가중 결합 + dedup + 정렬.

    절차:
      1. keyword_hits 의 keyword_score 를 max-normalize → keyword_score_norm.
      2. vector_hits 의 vector_score 를 max-normalize (음수는 0 clamp 후) →
         vector_score_norm.
      3. dedup key 별 merge — 같은 key 의 두 결과를 한 HybridHit 로 합침.
         - 메타 (source_path/title/snippet/chunk_id/heading/chunk_index) 는
           vector hit 의 값이 있으면 우선 (더 구체적), 없으면 keyword 값.
         - keyword_score / keyword_score_norm 은 keyword hit 의 값.
         - vector_score / vector_score_norm 은 vector hit 의 값.
      4. final_score = α · keyword_score_norm + β · vector_score_norm.
      5. final_score 내림차순 정렬 (동률은 입력 순서 stable).

    인자:
      keyword_hits : keyword retriever 결과 (search_mode="keyword" 표시).
      vector_hits  : vector retriever 결과 (search_mode="vector" 표시).
      alpha / beta : 가중치. ``hybrid_retrieve`` 가 결정 — vector 무시 시 (1, 0).

    반환:
      dedup + 가중합 적용된 ``HybridHit`` 리스트 (final_score 내림차순).
      입력이 모두 비어있으면 빈 리스트.
    """
    # 1) keyword 정규화 — 정규화 전 값은 보존 (search_mode/UI 진단용).
    if keyword_hits:
        kw_scores = [h.keyword_score for h in keyword_hits]
        kw_norms = _max_normalize(kw_scores)
        for h, n in zip(keyword_hits, kw_norms, strict=True):
            h.keyword_score_norm = n

    # 2) vector 정규화 — 음수 cosine 은 0 clamp.
    if vector_hits:
        vec_raw = [_clamp_pos(h.vector_score) for h in vector_hits]
        vec_norms = _max_normalize(vec_raw)
        for h, n in zip(vector_hits, vec_norms, strict=True):
            h.vector_score_norm = n

    # 3) dedup merge — key 별 단일 HybridHit.
    #    Python dict 가 insertion order 보존 (3.7+) → keyword 먼저, vector 가
    #    같은 key 면 merge. vector 만 hit 한 항목은 그 다음 추가.
    merged: dict[tuple, HybridHit] = {}

    for h in keyword_hits:
        key = h.dedup_key()
        if key in merged:
            # 같은 dedup key 가 keyword 안에서 중복 — 더 높은 keyword_score 보존.
            existing = merged[key]
            if h.keyword_score > existing.keyword_score:
                existing.keyword_score = h.keyword_score
                existing.keyword_score_norm = h.keyword_score_norm
            continue
        merged[key] = HybridHit(
            source_path=h.source_path,
            title=h.title,
            snippet=h.snippet,
            chunk_id=h.chunk_id,
            heading=h.heading,
            chunk_index=h.chunk_index,
            keyword_score=h.keyword_score,
            vector_score=0.0,
            keyword_score_norm=h.keyword_score_norm,
            vector_score_norm=0.0,
            final_score=0.0,
            search_mode="keyword",
        )

    for h in vector_hits:
        key = h.dedup_key()
        # source_path 키로도 같은 doc 찾기 — chunk_id 가 있는 vector hit 와
        # path 만 있는 keyword hit 가 같은 doc 일 수 있음.
        path_key = ("p", h.source_path or "")
        existing = merged.get(key) or merged.get(path_key)
        if existing is not None:
            # 메타는 vector hit 가 더 구체적 (chunk_id/heading/chunk_index 채움).
            if existing.chunk_id is None and h.chunk_id is not None:
                existing.chunk_id = h.chunk_id
                existing.heading = h.heading or existing.heading
                existing.chunk_index = (
                    h.chunk_index if h.chunk_index is not None else existing.chunk_index
                )
                # snippet 도 chunk content 가 더 좁게 의미 있음 — 채움.
                existing.snippet = h.snippet or existing.snippet
                existing.title = existing.title or h.title
            # vector_score 는 max — 동일 dedup key 안에서 가장 높은 값 보존.
            if h.vector_score > existing.vector_score:
                existing.vector_score = h.vector_score
                existing.vector_score_norm = h.vector_score_norm
            existing.search_mode = "hybrid"
            # path_key 로 찾았는데 chunk_id 가 채워졌다면 chunk key 로 재등록.
            if key not in merged and h.chunk_id is not None:
                merged[key] = existing
                # path_key 잔재는 그대로 두면 두 번 노출됨 — 정확히 같은 객체이므로
                # final iteration 시 ``set`` 로 unique 화한다.
            continue
        # vector 만 hit — 새 entry.
        merged[key] = HybridHit(
            source_path=h.source_path,
            title=h.title,
            snippet=h.snippet,
            chunk_id=h.chunk_id,
            heading=h.heading,
            chunk_index=h.chunk_index,
            keyword_score=0.0,
            vector_score=h.vector_score,
            keyword_score_norm=0.0,
            vector_score_norm=h.vector_score_norm,
            final_score=0.0,
            search_mode="vector",
        )

    # 같은 객체가 여러 key 로 중복 등록될 수 있음 — id 기준 unique 화.
    seen_ids: set[int] = set()
    deduped: list[HybridHit] = []
    for hit in merged.values():
        if id(hit) in seen_ids:
            continue
        seen_ids.add(id(hit))
        deduped.append(hit)

    # 4) final_score 계산.
    for hit in deduped:
        hit.final_score = (
            float(alpha) * hit.keyword_score_norm
            + float(beta) * hit.vector_score_norm
        )

    # 5) 정렬 — final_score 내림차순, 동률 stable.
    deduped.sort(key=lambda h: h.final_score, reverse=True)
    return deduped


# ──────────────────────── 디버그/검증 helper ────────────────────────


@dataclass
class CombineStats:
    """combine() 실행 메타 — 디버그/관찰용 (테스트가 단언에 사용 가능).

    필드:
      keyword_input_count : 입력 keyword hit 수
      vector_input_count  : 입력 vector hit 수
      output_count        : dedup 후 결과 수
      max_keyword_raw     : 정규화 전 keyword score 최대 (0 이면 정규화 X)
      max_vector_raw      : 정규화 전 vector score 최대 (음수는 0 clamp 후)
      alpha / beta        : 사용된 가중치
    """
    keyword_input_count: int = 0
    vector_input_count: int = 0
    output_count: int = 0
    max_keyword_raw: float = 0.0
    max_vector_raw: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    dedup_collisions: int = 0  # keyword 안에서 + vector 안에서 발생한 중복 수
    keyword_only_count: int = 0
    vector_only_count: int = 0
    hybrid_count: int = 0
    extras: dict = field(default_factory=dict)


def combine_with_stats(
    keyword_hits: list[HybridHit],
    vector_hits: list[HybridHit],
    *,
    alpha: float = 0.6,
    beta: float = 0.4,
) -> tuple[list[HybridHit], CombineStats]:
    """``combine()`` 과 동일 + 디버그 메타 함께 반환.

    프로덕션 hot path 에서는 ``combine()`` 사용. 본 함수는 테스트/관리자
    화면 디버그용. 알고리즘 자체는 동일하므로 ``combine()`` 위임.
    """
    stats = CombineStats(
        keyword_input_count=len(keyword_hits),
        vector_input_count=len(vector_hits),
        max_keyword_raw=max((h.keyword_score for h in keyword_hits), default=0.0),
        max_vector_raw=max((_clamp_pos(h.vector_score) for h in vector_hits), default=0.0),
        alpha=float(alpha),
        beta=float(beta),
    )

    # dedup collision 카운트 — combine 호출 전에 미리 측정 (combine 이 in-place
    # 변형하기 때문).
    seen_keys: set[tuple] = set()
    collisions = 0
    for h in keyword_hits:
        k = h.dedup_key()
        if k in seen_keys:
            collisions += 1
        seen_keys.add(k)
    seen_keys_v: set[tuple] = set()
    for h in vector_hits:
        k = h.dedup_key()
        if k in seen_keys_v:
            collisions += 1
        seen_keys_v.add(k)
    stats.dedup_collisions = collisions

    out = combine(keyword_hits, vector_hits, alpha=alpha, beta=beta)
    stats.output_count = len(out)
    stats.keyword_only_count = sum(1 for h in out if h.search_mode == "keyword")
    stats.vector_only_count = sum(1 for h in out if h.search_mode == "vector")
    stats.hybrid_count = sum(1 for h in out if h.search_mode == "hybrid")
    return out, stats


__all__ = [
    "HybridHit",
    "combine",
    "combine_with_stats",
    "CombineStats",
]
