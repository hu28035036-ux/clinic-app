"""Confidence + LLM 호출 게이트 — 18-6 hybrid retriever.

LLM 호출 차단의 단일 진실원천 (single source of truth) — 모든 모드/케이스에서
일관된 reason_code 발급.

게이트 결정 (`should_call_llm`) 우선순위 (docs/ai_rag_error_codes.md §5):
  1. ``invalid_query``      — caller 가 사전 차단 (본 모듈 범위 외)
  2. ``pii_detected``       — caller 가 사전 차단 (본 모듈은 boolean 인자만 받음)
  3. ``provider_disabled``  — AI disabled / api_key 없음 (caller 사전 차단)
  4. ``unknown_feature``    — intent_router (본 모듈 범위 외)
  5. ``no_sources``         — sources 0 건 (본 모듈)
  6. ``low_confidence``     — final_score < threshold (본 모듈)
  7. ``local_only``         — 모드 (본 모듈)
  8. 그 외                  → True (LLM 호출 허용)

confidence 매핑 (`compute_confidence`):
  - final_score >= ``HIGH_THRESHOLD`` → "high"
  - final_score >= ``LOW_THRESHOLD``  → "low"
  - 그 외                              → "unknown"

기존 ``manual_qa._confidence_for(score)`` (정수 score 기반) 와 동시 운영:
  - 본 모듈은 hybrid 의 final_score (float 0~1) 기반.
  - 18-7 admin/router 시점에 통합 결정. 18-6 은 양 정의 병행 운영.

본 모듈은 외부 호출 0 — 순수 함수. provider/embedding/db 비의존.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schemas import (
    AI_MODE_AI_ASSIST,
    AI_MODE_LOCAL_FIRST,
    AI_MODE_LOCAL_ONLY,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_UNKNOWN,
    REASON_LLM_SKIPPED_LOCAL_ONLY,
    REASON_LLM_SKIPPED_LOW_CONFIDENCE,
    REASON_LLM_SKIPPED_NO_SOURCES,
    REASON_LLM_SKIPPED_PII,
    REASON_LOW_CONFIDENCE,
    REASON_NO_SOURCES,
    REASON_PII_DETECTED,
    REASON_PROVIDER_DISABLED,
)

# ──────────────────────── 정책 상수 ────────────────────────

# final_score (정규화 [0, 1]) 기반 confidence 임계.
# - HIGH_THRESHOLD : 이 이상이면 LLM 호출 + "high" confidence.
# - LOW_THRESHOLD  : 이 이상이면 LLM 호출 가능하지만 "low" confidence.
# - 미만           → LLM 호출 차단 + "unknown".
#
# 운영 튜닝 가능 — 18-6 시점은 보수적 기본값. 18-7 에서 eval 기반 조정.
# manual_qa.LOW_SCORE_THRESHOLD (정수=2, raw keyword score) 와 별개 정의 —
# hybrid 는 정규화 점수 사용.
HIGH_THRESHOLD = 0.7
LOW_THRESHOLD = 0.3

# LLM 호출 게이트 임계 — final_score 가 이 미만이면 호출 차단.
# 본 임계는 ``LOW_THRESHOLD`` 와 동일 — confidence "unknown" 이면 LLM 차단.
# (불일치 정의는 디버깅 어려움 — 단일 임계로 통일).
LLM_CALL_THRESHOLD = LOW_THRESHOLD


# ──────────────────────── dataclass ────────────────────────


@dataclass
class GateDecision:
    """LLM 호출 게이트 결정 결과.

    필드:
      should_call : True 면 LLM 호출 가능, False 면 차단.
      reason_code : 차단 사유 (호출 가능 시 빈 문자열).
                    응답 JSON optional ``reason_code`` 와 ``AiUsageLog``
                    양쪽에 그대로 전달.
      confidence  : "high" | "low" | "unknown" — caller 가 응답에 그대로 매핑.
      blocked_reason : 기존 ``blocked_reason`` 호환용 사용자 메시지.
                       (v1.3.3 응답 후방호환).
      final_score : 게이트 입력으로 사용된 final_score (디버그/로그용).
    """
    should_call: bool
    reason_code: str = ""
    confidence: str = CONFIDENCE_UNKNOWN
    blocked_reason: str = ""
    final_score: float = 0.0


# ──────────────────────── confidence 매핑 ────────────────────────


def compute_confidence(
    final_score: float,
    *,
    high_threshold: float = HIGH_THRESHOLD,
    low_threshold: float = LOW_THRESHOLD,
) -> str:
    """final_score → "high" | "low" | "unknown" 매핑.

    - 입력은 [0, 1] 가정 (범위 밖이어도 안전 동작).
    - high_threshold / low_threshold 는 호출자 override 가능 (eval/A-B 비교용).
    """
    if final_score >= high_threshold:
        return CONFIDENCE_HIGH
    if final_score >= low_threshold:
        return CONFIDENCE_LOW
    return CONFIDENCE_UNKNOWN


# ──────────────────────── LLM 게이트 ────────────────────────


def should_call_llm(
    *,
    sources_count: int,
    final_score: float,
    mode: str = AI_MODE_LOCAL_FIRST,
    pii_detected: bool = False,
    provider_disabled: bool = False,
    threshold: float = LLM_CALL_THRESHOLD,
) -> GateDecision:
    """LLM 호출 차단 게이트 — 단일 진실원천.

    인자:
      sources_count     : RAG 결과 chunk/doc 수.
      final_score       : 정규화된 종합 점수 [0, 1].
      mode              : "local_only" | "local_first" | "ai_assist".
      pii_detected      : caller 가 PII 사전 검사 결과 전달.
      provider_disabled : AI disabled / api_key 없음 — caller 가 사전 검사.
      threshold         : LLM 호출 게이트 임계 (default=LLM_CALL_THRESHOLD).

    반환:
      ``GateDecision(should_call, reason_code, confidence, blocked_reason, final_score)``.

    우선순위 (docs/ai_rag_error_codes.md §5):
      1. provider_disabled          → reason="provider_disabled"
      2. pii_detected               → reason="pii_detected" (LLM 입력 차단)
      3. mode == "local_only"       → reason="llm_skipped_local_only"
      4. sources_count == 0         → reason="llm_skipped_no_sources"
      5. final_score < threshold    → reason="llm_skipped_low_confidence"
      6. 그 외                      → should_call=True
    """
    confidence = compute_confidence(final_score)

    # 1. provider_disabled — 외부 LLM 자체 사용 불가.
    if provider_disabled:
        return GateDecision(
            should_call=False,
            reason_code=REASON_PROVIDER_DISABLED,
            confidence=confidence,
            blocked_reason="provider disabled",
            final_score=final_score,
        )

    # 2. PII — 외부 전송 차단 (응답에서는 pii_detected 가 더 강한 메시지).
    if pii_detected:
        return GateDecision(
            should_call=False,
            reason_code=REASON_PII_DETECTED,
            confidence=confidence,
            blocked_reason="pii detected",
            final_score=final_score,
        )

    # 3. local_only — 모드가 LLM 자체 차단.
    if mode == AI_MODE_LOCAL_ONLY:
        return GateDecision(
            should_call=False,
            reason_code=REASON_LLM_SKIPPED_LOCAL_ONLY,
            confidence=confidence,
            blocked_reason="local only mode",
            final_score=final_score,
        )

    # 4. no_sources — RAG 결과 0 건이면 LLM 호출 시 할루시네이션 위험.
    if sources_count <= 0:
        return GateDecision(
            should_call=False,
            reason_code=REASON_LLM_SKIPPED_NO_SOURCES,
            confidence=CONFIDENCE_UNKNOWN,
            blocked_reason="no rag hit",
            final_score=0.0,
        )

    # 5. low_confidence — 임계 미만이면 LLM 호출 생략.
    if final_score < threshold:
        return GateDecision(
            should_call=False,
            reason_code=REASON_LLM_SKIPPED_LOW_CONFIDENCE,
            confidence=CONFIDENCE_UNKNOWN,
            blocked_reason="low rag confidence",
            final_score=final_score,
        )

    # 6. 통과 — LLM 호출 가능.
    return GateDecision(
        should_call=True,
        reason_code="",
        confidence=confidence,
        blocked_reason="",
        final_score=final_score,
    )


# ──────────────────────── reason_code 우선순위 ────────────────────────


def primary_reason_code(*candidates: Optional[str]) -> str:
    """여러 reason_code 중 가장 높은 우선순위 1개 선택 (docs/ai_rag_error_codes.md §5).

    응답의 ``reason_code`` 는 1개만 노출 — 동시 발급 시 우선순위 순 1개 선택.
    secondary 는 로그 레벨에서 별도 컬럼 (m014 시점).

    None / 빈 문자열은 무시. 우선순위에 없는 코드는 가장 낮게 (입력 순서 보존).
    """
    # 우선순위 (위가 높음)
    priority = (
        "invalid_query",
        "pii_detected",
        "provider_disabled",
        "provider_api_key_missing",
        "reindex_in_progress",
        "unknown_feature",
        "no_sources",
        "llm_skipped_no_sources",
        "low_confidence",
        "llm_skipped_low_confidence",
        "llm_skipped_local_only",
        "llm_skipped_pii",
        "llm_skipped_unknown_feature",
        "llm_skipped_invalid_query",
        "llm_skipped_keyword_only",
        "llm_skipped_local_answer",
        "llm_skipped_db_answer",
        "llm_skipped_rule_based",
        "vector_disabled",
        "embedding_skipped_local_only",
        "embedding_skipped_same_hash",
        "embedding_skipped_short_query",
        "embedding_skipped_disabled",
        "embedding_skipped_api_key_missing",
        "external_api_not_allowed",
        "unsupported_question",
        "timeout",
        "provider_error",
        "internal_error",
    )
    cleaned = [c for c in candidates if c]
    if not cleaned:
        return ""
    # 우선순위 dict 로 빠른 조회.
    rank = {c: i for i, c in enumerate(priority)}
    cleaned.sort(key=lambda c: rank.get(c, 999))
    return cleaned[0]


# ──────────────────────── 모드 검증 helper ────────────────────────


def is_valid_mode(mode: str) -> bool:
    """모드가 유효한지 — 알 수 없는 모드는 caller 가 local_first 로 fallback."""
    return mode in (AI_MODE_LOCAL_ONLY, AI_MODE_LOCAL_FIRST, AI_MODE_AI_ASSIST)


def normalize_mode(mode: Optional[str]) -> str:
    """알 수 없는 모드 / None → local_first (안전 default)."""
    if mode and is_valid_mode(mode):
        return mode
    return AI_MODE_LOCAL_FIRST


# ──────────────────────── reason_code → blocked_reason 매핑 ────────────────────────


_BLOCKED_REASON_MAP = {
    REASON_NO_SOURCES: "no rag hit",
    REASON_LLM_SKIPPED_NO_SOURCES: "no rag hit",
    REASON_LOW_CONFIDENCE: "low rag confidence",
    REASON_LLM_SKIPPED_LOW_CONFIDENCE: "low rag confidence",
    REASON_LLM_SKIPPED_LOCAL_ONLY: "local only mode",
    REASON_LLM_SKIPPED_PII: "pii detected",
    REASON_PII_DETECTED: "pii detected",
    REASON_PROVIDER_DISABLED: "provider disabled",
}


def blocked_reason_for(reason_code: str) -> str:
    """reason_code → v1.3.3 ``blocked_reason`` 호환 사용자 메시지.

    v1.3.3 응답에서 알려진 값:
      - "no rag hit" / "low rag confidence" / "no provider"
    신규 reason_code 도 위 중 하나로 매핑하거나, 없으면 reason_code 자체 반환.
    """
    return _BLOCKED_REASON_MAP.get(reason_code, reason_code or "")


__all__ = [
    "HIGH_THRESHOLD",
    "LOW_THRESHOLD",
    "LLM_CALL_THRESHOLD",
    "GateDecision",
    "compute_confidence",
    "should_call_llm",
    "primary_reason_code",
    "is_valid_mode",
    "normalize_mode",
    "blocked_reason_for",
]
