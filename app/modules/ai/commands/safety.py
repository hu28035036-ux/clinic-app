"""AI commands Safety 게이트 helper (19-13 신규).

services/ai/action_leave.py 의 ``_pre_gate`` (PII / 다중 명령 / 키워드) +
sms_draft.py 의 ``assert_safe_for_external`` + manual_qa.py 의 hallucination guard
와 byte-equivalent **outcome → reason_code 매핑** 을 단일 원천으로 노출.

# COMPAT: 본 helper 는 services/ai/* 본체와 *byte-equivalent*. 라우터 / 서비스
#         본체 채택 ⊥. contract 테스트가 동작 동등성 검증.

# SAFETY: 본 모듈은 *outcome 분류 + reason_code 셋* 만 — 실제 PII 마스킹 / 차단
#         결정은 services/ai/pii.py + action_leave._pre_gate + sms_draft 가 보유.
#         본 19-13 가 정책 변경 ⊥.

# SAFETY: ``is_provider_blocked_outcome(outcome)`` 가 ``True`` 면 LLM/Embedding
#         호출 ⊥ (Local-first 정책 단일 원천).

# RISK: ``is_approval_required_outcome(outcome)`` 가 ``True`` 면 DB write ⊥
#       (Approval 정책 단일 원천).

# NOTE: 본 모듈은 *읽기 / 분류* 만 — DB 변경 ⊥, 외부 호출 ⊥.
"""
from __future__ import annotations

from typing import Optional

from .schemas import (
    REASON_CODES_APPROVAL_REQUIRED,
    REASON_CODES_LOOKUP_FAILED,
    REASON_CODES_PROVIDER_BLOCKED,
)


# ──────────────── outcome → reason_code 매핑 (services/ai/action_leave.py 정합) ────────────────

# COMPAT: ``services/ai/action_leave.py:_pre_gate`` 의 outcome → 19-13 reason_code
#         매핑. 본 19-13 가 outcome 신규 추가 ⊥ — services/ai/action_leave.py
#         본체 변경과 동시에만 가능.
ACTION_LEAVE_OUTCOME_TO_REASON: dict[str, str] = {
    # 사전 게이트 (LLM 호출 ⊥)
    "pii_blocked": "llm_skipped_pii",
    "input_too_short": "invalid_query",
    "input_too_long": "invalid_query",
    "no_leave_keyword": "unknown_feature",
    "multi_command": "invalid_query",
    # LLM 실패 / 환각
    "parse_fail": "validation_failed",
    "intent_mismatch": "unknown_feature",
    "hallucinated_name": "validation_failed",
    "hallucinated_date": "validation_failed",
    "low_confidence": "low_confidence",
    "provider_error": "external_api_not_allowed",
    # 날짜
    "ambiguous_date": "validation_failed",
    "invalid_date": "validation_failed",
    "out_of_range_date": "validation_failed",
    "no_leave_date": "validation_failed",
    # 휴무유형
    "ambiguous_half_day": "validation_failed",
    # 매칭
    "no_match": "therapist_not_found",
    "multi_match": "patient_ambiguous",
    "inactive_therapist": "therapist_not_found",
    "not_therapist": "therapist_not_found",
    "invalid_name": "validation_failed",
    # 실행 (Approval / Token)
    "not_confirmed": "not_confirmed",
    "overwrite_not_acknowledged": "overwrite_not_acknowledged",
    "token_format": "token_format",
    "token_signature": "token_signature",
    "token_unsafe": "token_unsafe",
    "token_mismatch": "token_mismatch",
    "token_expired": "token_expired",
    # 충돌
    "conflict_changed": "appointment_conflict",
    "therapist_changed": "appointment_conflict",
    # 시스템
    "db_error": "execution_blocked",
    "feature_disabled": "external_api_not_allowed",
}


def map_action_leave_outcome_to_reason(outcome: Optional[str]) -> Optional[str]:
    """``action_leave`` outcome → 19-13 reason_code 매핑.

    NOTE: 알려진 outcome 만 변환. ``"ok"`` / ``None`` / 알 수 없는 값은 ``None``.
    """
    if not outcome or outcome == "ok":
        return None
    return ACTION_LEAVE_OUTCOME_TO_REASON.get(outcome)


# ──────────────── outcome 분류 helper ────────────────

def is_provider_blocked_outcome(outcome: Optional[str]) -> bool:
    """주어진 outcome 이 발생하면 LLM/Embedding 호출 ⊥ 인지.

    SAFETY: ``True`` 면 ``len(provider.calls) == 0`` 단언이 정책 단일 원천.
    """
    reason = map_action_leave_outcome_to_reason(outcome)
    if reason is None:
        return False
    return reason in REASON_CODES_PROVIDER_BLOCKED


def is_approval_required_outcome(outcome: Optional[str]) -> bool:
    """주어진 outcome 이 발생하면 DB write ⊥ + 사용자 승인 필요인지.

    RISK: ``True`` 면 ``EmployeeLeave`` upsert / ``Appointment`` write / 외부 SMS
    발송 ⊥. action_leave.execute 의 token_* / not_confirmed /
    overwrite_not_acknowledged 분기와 정합.
    """
    reason = map_action_leave_outcome_to_reason(outcome)
    if reason is None:
        return False
    return reason in REASON_CODES_APPROVAL_REQUIRED


def is_lookup_failed_outcome(outcome: Optional[str]) -> bool:
    """주어진 outcome 이 발생하면 환자 / 치료사 / 치료항목 / 예약 매칭 실패인지.

    NOTE: ``True`` 면 사용자에게 다른 식별자로 재시도 요청.
    """
    reason = map_action_leave_outcome_to_reason(outcome)
    if reason is None:
        return False
    return reason in REASON_CODES_LOOKUP_FAILED


# ──────────────── PII / Safety 정책 상수 ────────────────

# RISK: ``services/ai/action_leave.py`` 의 ``_MAX_INPUT_LEN = 200`` /
#       ``_MIN_INPUT_LEN = 1`` 와 byte-equivalent. 본 19-13 가 변경 ⊥.
INPUT_MAX_LEN: int = 200
INPUT_MIN_LEN: int = 1

# RISK: ``services/ai/action_leave.py`` 의 ``_LEAVE_KEYWORDS`` 와 byte-equivalent.
LEAVE_KEYWORDS: tuple[str, ...] = (
    "휴무", "연차", "월차", "반차", "휴가", "쉼", "쉬는",
)

# SAFETY: ``services/ai/action_leave.py`` 의 ``_PATIENT_INDICATORS`` 와
#         byte-equivalent. 휴무 명령에 환자 키워드 발견 시 LLM 호출 ⊥.
PATIENT_INDICATORS: tuple[str, ...] = (
    "환자", "차트", "카르테", "차트번호", "내원", "방문", "chart",
)


def has_leave_keyword(text: str) -> bool:
    """입력에 휴무 키워드가 있는지 — services/ai/action_leave.py:_pre_gate
    byte-equivalent.
    """
    if not text:
        return False
    return any(k in text for k in LEAVE_KEYWORDS)


def has_patient_indicator(text: str) -> bool:
    """입력에 환자 키워드가 있는지 — services/ai/action_leave.py:_pre_gate
    byte-equivalent.

    SAFETY: ``True`` 면 LLM 호출 ⊥ (PII 의심).
    """
    if not text:
        return False
    return any(k in text for k in PATIENT_INDICATORS)


def is_input_length_valid(text: str) -> bool:
    """입력 길이 정책 — ``[INPUT_MIN_LEN, INPUT_MAX_LEN]``. byte-equivalent."""
    if text is None:
        return False
    n = len(text)
    return INPUT_MIN_LEN <= n <= INPUT_MAX_LEN


# ──────────────── PII 부재 정책 (외부 LLM 전송 금지 필드) ────────────────

# SAFETY: 본 셋의 필드는 LLM prompt / log / 응답에 *원문 부재 보장* —
#         services/ai/sms_draft.py 의 PII 가드 + ai_logging.py 의 마스킹 정책 정합.
PII_FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "phone",
    "patient_phone",
    "rrn",
    "ssn",
    "birth",
    "birth_date",
    "chart_no",
    "chart_no_maybe",
    "patient_memo",
    "appointment_memo",
    "real_name",
})

# SAFETY: 본 셋의 key 는 응답에 *원문 부재 보장* — admin / sms_draft / ai_settings
#         응답 구조 변경 ⊥. ``app/modules/admin/schemas.py:AI_SETTINGS_FORBIDDEN_KEYS``
#         + ``app/modules/admin/schemas.py:PUBLIC_CONFIG_DROP_KEYS`` + 본 모듈
#         정합.
SECRET_KEYS_FORBIDDEN_IN_LOG: frozenset[str] = frozenset({
    "api_key",
    "munjanara_pw",
    "munjanara_password",
    "munjanara_key",
    "admin_password_hash",
    "admin_password",
    "sync_secret",
    "preview_token",  # HMAC 토큰은 audit detail 에 원문 부재
})
