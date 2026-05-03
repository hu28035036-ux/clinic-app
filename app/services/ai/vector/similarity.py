"""Vector similarity 함수 — 18-5.

cosine similarity + top_k 추출. 외부 호출 0, 결정적, 안전 fallback.

설계 원칙 (사용자 요구 #13/#14, vector_harness_plan §5.10~12):
  1. 빈 벡터 / 0 벡터 → 0.0 안전 반환 (raise 금지).
  2. dimension mismatch → 0.0 안전 반환 (사용자 요구 #13).
  3. cosine 결과는 안정적 (단위 벡터 dot product 와 동일).
  4. top_k 정렬은 stable — 동률은 입력 순서 보존.

외부 의존성: 없음 (math 표준 라이브러리만 사용).
"""
from __future__ import annotations

import math
from typing import Any


# ──────────────────────── cosine ────────────────────────


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """두 벡터의 cosine similarity. 안전 모드 — 어떤 입력에도 raise 하지 않음.

    반환:
      [-1.0, 1.0] 범위의 float. 다음 케이스는 0.0:
        - a 또는 b 가 None / 빈 리스트
        - dimension mismatch (len(a) != len(b))
        - a 또는 b 가 0 벡터 (norm == 0)

    사용자 요구 #13/#14 만족 — 안전 fallback + 결정적 계산.
    """
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0

    # math.fsum 으로 부동소수점 누적 오차 최소화.
    dot = math.fsum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(math.fsum(x * x for x in a))
    norm_b = math.sqrt(math.fsum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot / (norm_a * norm_b)
    # 부동소수점 오차로 [-1, 1] 살짝 벗어날 수 있음 — clamp.
    if sim > 1.0:
        return 1.0
    if sim < -1.0:
        return -1.0
    return sim


# ──────────────────────── top_k ────────────────────────


def top_k(
    query_vec: list[float],
    candidates: list[tuple[Any, list[float]]],
    *,
    k: int = 5,
) -> list[tuple[Any, float]]:
    """query 와 candidates 간 cosine top_k.

    인자:
      query_vec  : 질의 벡터
      candidates : ``[(payload, vector), ...]`` — payload 는 임의 객체 (chunk_id 등)
      k          : 상위 몇 개

    반환:
      ``[(payload, score), ...]`` — score 내림차순. 동률은 입력 순서 보존
      (Python ``sorted`` 가 stable 함을 활용).

    안전 fallback (사용자 요구 #14):
      - query_vec 이 비었거나 0 벡터 → 빈 리스트
      - candidates 가 비어있음 → 빈 리스트
      - dimension mismatch 인 candidate → score 0.0 (필터되지 않고 포함되되
        뒤로 밀림)
    """
    if k <= 0:
        return []
    if not query_vec:
        return []
    if not candidates:
        return []
    # query 가 0 벡터인지 검사 (한 번만).
    qn = math.sqrt(math.fsum(x * x for x in query_vec))
    if qn == 0.0:
        return []

    scored: list[tuple[Any, float]] = []
    for payload, vec in candidates:
        score = cosine_similarity(query_vec, vec)
        scored.append((payload, score))

    # 안정 정렬 — score 내림차순.
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


# ──────────────────────── 보조 ────────────────────────


def is_zero_vector(v: list[float]) -> bool:
    """모든 원소가 0 또는 빈 벡터인지."""
    if not v:
        return True
    return all(x == 0.0 for x in v)


__all__ = [
    "cosine_similarity",
    "top_k",
    "is_zero_vector",
]
