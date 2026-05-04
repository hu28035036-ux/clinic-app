"""AI commands API 응답 키 contract + INTENT_NAMES + reason_code 셋 (19-13 신규).

frozenset 으로 응답 key / outcome / reason_code 셋 보존. contract 테스트가 인라인
응답 dict / outcome 와 본 상수의 셋 비교 → 임의 변경 검출.

# COMPAT: 본 frozenset 상수의 *원소 변경 ⊥* — UI (AI 도우미 탭 / SMS 초안 모달 /
#         AI 휴무 모달) 가 모두 의존. contract 테스트가 회귀 검출.

# SAFETY: 본 모듈은 *상수 셋* 만 — 외부 호출 ⊥, DB 변경 ⊥.

# RISK: 응답 key 33+ (manual/search 3 + manual/ask 9 + sources 3 + health 9 +
#       health/public 4 + status 9 + sms/draft 7 + action/parse 6 + action/preview 11 +
#       action/execute 5) 변경 ⊥. 본 19-13 가 변경 ⊥.
"""
from __future__ import annotations


# ──────────────── INTENT 정책 ────────────────

# 현재 구현된 INTENT (services/ai/action_leave.py:INTENT_NAME).
INTENT_NAMES_IMPLEMENTED: frozenset[str] = frozenset({
    "create_therapist_leave",
})

# 후속 검토 INTENT (현재 미구현).
# TODO(19-x): AI 예약 / AI 환자 등록 / AI 문자 일괄 발송 — 후속 19-x.
INTENT_NAMES_TODO: frozenset[str] = frozenset({
    # AI 예약 흐름 — 현재 부재.
    "create_appointment",
    "modify_appointment",
    "cancel_appointment",
    # AI 환자 등록 흐름 — 현재 부재 (수동 등록 / data-convert 만 존재).
    "create_patient",
    # AI SMS 흐름 — 현재 sms_draft 만 (단건 초안). 일괄 발송 부재.
    "send_sms_batch",
})

# 알려진 모든 INTENT 셋 (현재 + 후속).
INTENT_NAMES_ALL: frozenset[str] = INTENT_NAMES_IMPLEMENTED | INTENT_NAMES_TODO


# ──────────────── action/parse 응답 (현재 구현) ────────────────

# POST /api/ai/action/parse 응답 key 6개.
# COMPAT: ``app/routers/ai.py:_serialize_parse_result`` byte-equivalent.
ACTION_PARSE_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "outcome",
    "parsed",
    "warnings",
    "safe_to_continue",
    "message",
})


# ──────────────── action/preview 응답 (현재 구현) ────────────────

# POST /api/ai/action/preview 응답 key 11개.
# COMPAT: ``app/routers/ai.py:_serialize_preview_result`` byte-equivalent.
ACTION_PREVIEW_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "outcome",
    "candidate",
    "mode",
    "existing",
    "appointments_count",
    "warnings",
    "safe_to_execute",
    "preview_token",
    "preview_token_exp",
    "message",
})


# ──────────────── action/execute 응답 (현재 구현) ────────────────

# POST /api/ai/action/execute 응답 key 5개.
# COMPAT: ``app/routers/ai.py:action_execute`` byte-equivalent.
ACTION_EXECUTE_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "outcome",
    "leave_id",
    "mode",
    "message",
})


# ──────────────── sms/draft 응답 (현재 구현) ────────────────

# POST /api/ai/sms/draft 응답 key 7개 (라우터가 prompt_text/response_text 제거 후 응답).
# COMPAT: ``app/routers/ai.py:sms_draft`` 의 ``out = {k: v ... if k not in
#         ("prompt_text", "response_text")}`` byte-equivalent.
SMS_DRAFT_RESPONSE_KEYS: frozenset[str] = frozenset({
    "draft",
    "warnings",
    "missing_fields",
    "context_used",
    "needs_user_confirm",
    "skipped",
    "skip_reason",
    "blocked",
    "blocked_reason",
    "guard_hits",
})

# SMS draft 응답에 *부재 보장* 되어야 할 내부 key 셋 (regression 가드).
# SAFETY: ``prompt_text`` / ``response_text`` 는 LLM 입력/출력 원문 — UI 노출 ⊥.
SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS: frozenset[str] = frozenset({
    "prompt_text",
    "response_text",
})


# ──────────────── manual/search 응답 (현재 구현) ────────────────

# POST /api/ai/manual/search 응답 key.
# COMPAT: ``app/services/ai/manual_qa.py:manual_search`` byte-equivalent.
MANUAL_SEARCH_MIN_KEYS: frozenset[str] = frozenset({
    "sources",
    "top_score",
    "masked_question",
})


# ──────────────── manual/ask 응답 (현재 구현) ────────────────

# POST /api/ai/manual/ask 응답 key (분기 多 — not_found / blocked / answer 분기).
# COMPAT: ``app/services/ai/manual_qa.py:ask_manual_question`` 와 ``rag/pipeline``
#         의 응답 dict byte-equivalent.
MANUAL_ASK_RESPONSE_KEYS: frozenset[str] = frozenset({
    "answer",
    "not_found",
    "blocked",
    "blocked_reason",
    "confidence",
    "sources",
    "guard_hits",
    "masked_question",
    "low_score_threshold",
})


# ──────────────── sms/validate 응답 (현재 구현) ────────────────

# POST /api/ai/sms/validate 응답 key.
# COMPAT: ``app/routers/ai.py:sms_validate`` byte-equivalent.
SMS_VALIDATE_RESPONSE_KEYS: frozenset[str] = frozenset({
    "items",
    "summary",
})


# ──────────────── action_leave outcome 셋 (services/ai/action_leave.py:USER_MESSAGES) ────────────────

# 알려진 outcome 셋 — services/ai/action_leave.py:USER_MESSAGES 키 정합.
# COMPAT: 본 셋의 원소 변경은 services/ai/action_leave.py 본체 변경과 동시 — 본
#         19-13 가 변경 ⊥.
ACTION_LEAVE_OUTCOMES: frozenset[str] = frozenset({
    "ok",
    # 사전 게이트
    "no_leave_keyword",
    "multi_command",
    "input_too_short",
    "input_too_long",
    "pii_blocked",
    # LLM 실패
    "parse_fail",
    "intent_mismatch",
    "hallucinated_name",
    "hallucinated_date",
    "low_confidence",
    "provider_error",
    # 날짜
    "ambiguous_date",
    "invalid_date",
    "out_of_range_date",
    "no_leave_date",
    # 휴무유형
    "ambiguous_half_day",
    # 매칭
    "no_match",
    "multi_match",
    "inactive_therapist",
    "not_therapist",
    "invalid_name",
    # 실행
    "not_confirmed",
    "overwrite_not_acknowledged",
    "token_format",
    "token_signature",
    "token_unsafe",
    "token_mismatch",
    "token_expired",
    "conflict_changed",
    "therapist_changed",
    "db_error",
    "feature_disabled",
})


# ──────────────── reason_code 셋 (19-13 세션 지시문 정합) ────────────────

# **provider 호출 0회 정책** reason_code 셋 (Local-first 가드).
# SAFETY: 본 셋의 reason 이 발생하면 **LLM/Embedding 호출 ⊥**. ``len(provider.calls)
#         == 0`` 단언이 정책 단일 원천.
REASON_CODES_PROVIDER_BLOCKED: frozenset[str] = frozenset({
    "pii_detected",
    "no_sources",
    "low_confidence",
    "unknown_feature",
    "external_api_not_allowed",
    "llm_skipped_local_only",
    "llm_skipped_pii",
    "llm_skipped_no_sources",
    "llm_skipped_low_confidence",
})

# **승인 없는 DB 변경 차단** reason_code 셋 (Approval 가드).
# RISK: 본 셋의 reason 이 발생하면 **DB write ⊥**. action_leave 의 token_* /
#       not_confirmed / overwrite_not_acknowledged 와 정합.
REASON_CODES_APPROVAL_REQUIRED: frozenset[str] = frozenset({
    "approval_required",
    "execution_blocked",
    "validation_failed",
    "not_confirmed",
    "overwrite_not_acknowledged",
    "token_format",
    "token_signature",
    "token_unsafe",
    "token_mismatch",
    "token_expired",
})

# **검색 / 매칭 실패** reason_code 셋 — DB 변경 / LLM 호출 부재 + 사용자에게
# 다시 입력 요청.
# NOTE: 환자 / 치료사 / 치료항목 / 예약 / 휴무 매칭 실패 시. AI 가 *추측 답변
#       금지* — 정확히 매칭된 후보가 있을 때만 진행.
REASON_CODES_LOOKUP_FAILED: frozenset[str] = frozenset({
    "patient_not_found",
    "patient_ambiguous",
    "therapist_not_found",
    "treatment_not_found",
    "appointment_conflict",
    "leave_conflict",
})

# 모든 알려진 reason_code 셋 (cross-check 용).
REASON_CODES_ALL: frozenset[str] = (
    REASON_CODES_PROVIDER_BLOCKED
    | REASON_CODES_APPROVAL_REQUIRED
    | REASON_CODES_LOOKUP_FAILED
)


# ──────────────── HTTP 상태 코드 매핑 (action/execute) ────────────────

# COMPAT: ``app/routers/ai.py:action_execute`` 의 분기 byte-equivalent.
# - r.ok=True → 200
# - r.outcome in ("conflict_changed", "therapist_changed") → 409
# - r.outcome == "db_error" → 500
# - 그 외 (not_confirmed, overwrite_not_acknowledged, token_*) → 400
ACTION_EXECUTE_OUTCOME_HTTP_STATUS: dict[str, int] = {
    # 동시성 충돌 → 409 Conflict
    "conflict_changed": 409,
    "therapist_changed": 409,
    # 서버 에러 → 500
    "db_error": 500,
    # 그 외 실패 → 400 (default)
}


# ──────────────── AI feature 셋 (ai_logging feature key) ────────────────

# services/ai/ai_logging.py 가 사용하는 feature key.
AI_LOGGING_FEATURES: frozenset[str] = frozenset({
    "manual_search",
    "manual_ask",
    "sms_draft",
    "sms_validate",
    "action_leave_parse",
    "action_leave_preview",
    "action_leave_execute",
})


# ──────────────── 모든 contract 셋 (cross-check 용) ────────────────

AI_COMMANDS_ALL_CONTRACT_SETS: dict[str, frozenset[str]] = {
    "action_parse": ACTION_PARSE_RESPONSE_KEYS,
    "action_preview": ACTION_PREVIEW_RESPONSE_KEYS,
    "action_execute": ACTION_EXECUTE_RESPONSE_KEYS,
    "sms_draft": SMS_DRAFT_RESPONSE_KEYS,
    "sms_draft_forbidden": SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS,
    "manual_search_min": MANUAL_SEARCH_MIN_KEYS,
    "manual_ask": MANUAL_ASK_RESPONSE_KEYS,
    "sms_validate": SMS_VALIDATE_RESPONSE_KEYS,
    "action_leave_outcomes": ACTION_LEAVE_OUTCOMES,
    "intent_names_implemented": INTENT_NAMES_IMPLEMENTED,
    "intent_names_todo": INTENT_NAMES_TODO,
    "reason_codes_provider_blocked": REASON_CODES_PROVIDER_BLOCKED,
    "reason_codes_approval_required": REASON_CODES_APPROVAL_REQUIRED,
    "reason_codes_lookup_failed": REASON_CODES_LOOKUP_FAILED,
    "ai_logging_features": AI_LOGGING_FEATURES,
}
