"""AI commands 정책 상수 + 알려진 outcome 셋 (19-13 신규).

services/ai/action_leave.py 의 토큰 정책 / outcome 셋 / TTL 등을 *재노출* —
helper 채택 ⊥, 정책 단일 원천 가드 용도.

# COMPAT: 본 모듈의 모든 정책 상수는 ``services/ai/action_leave.py`` 의 인라인
#         상수와 *byte-equivalent*. 본 19-13 가 정책 변경 ⊥.

# SAFETY: 본 모듈은 *상수 셋* 만 — DB 변경 ⊥, LLM 호출 ⊥, 외부 호출 ⊥.

# RISK: ``TOKEN_TTL_SEC = 120`` — Preview / Execute 시간 간격 정책. 본 19-13 가
#       *변경 ⊥*. 너무 길면 TOCTOU 위험 / 너무 짧으면 사용자 승인 시간 부족.

# RISK: ``TOKEN_VERSION = 1`` — HMAC 페이로드 버전. 변경 시 기존 발급 토큰 모두
#       무효. 본 19-13 가 *변경 ⊥*.
"""
from __future__ import annotations


# ──────────────── HMAC 토큰 정책 (services/ai/action_leave.py 정합) ────────────────

# RISK: Preview / Execute 시간 간격 (초). services/ai/action_leave.py:TOKEN_TTL_SEC
#       와 byte-equivalent. 본 19-13 가 변경 ⊥.
TOKEN_TTL_SEC: int = 120

# RISK: HMAC 페이로드 버전. services/ai/action_leave.py:TOKEN_VERSION 와
#       byte-equivalent. 본 19-13 가 변경 ⊥ — 변경 시 발급 토큰 모두 무효.
TOKEN_VERSION: int = 1


# ──────────────── 알려진 mode 셋 (action_leave preview / execute) ────────────────

# COMPAT: services/ai/action_leave.py:_check_conflict 의 mode 와 byte-equivalent.
ACTION_LEAVE_MODES: frozenset[str] = frozenset({
    "create",     # 신규 휴무 등록
    "overwrite",  # 기존 휴무 덮어쓰기 (사용자가 overwrite_acknowledged=True 필요)
    "noop",       # 동일 휴무 이미 있음 — DB write ⊥
})


# ──────────────── leave_type / leave_kind 셋 ────────────────

# COMPAT: services/ai/action_leave.py:ParsedAction.leave_type_hint 와 byte-equivalent.
LEAVE_TYPES: frozenset[str] = frozenset({
    "full",
    "morning",
    "afternoon",
    "unknown",
})

# COMPAT: services/ai/action_leave.py:ParsedAction.leave_kind_hint 와 byte-equivalent.
LEAVE_KINDS: frozenset[str] = frozenset({
    "annual",   # 연차
    "monthly",  # 월차
    "unknown",
})


# ──────────────── confidence 셋 ────────────────

# COMPAT: services/ai/action_leave.py:ParsedAction.confidence 와 byte-equivalent.
CONFIDENCE_LEVELS: frozenset[str] = frozenset({
    "high",
    "low",
})


# ──────────────── SMS draft tone 셋 ────────────────

# COMPAT: ``app/routers/ai.py:sms_draft`` 의 ``tone not in ("friendly", "formal")``
#         가드와 byte-equivalent.
SMS_DRAFT_TONES: frozenset[str] = frozenset({
    "friendly",
    "formal",
})


# ──────────────── action_leave INTENT 정책 ────────────────

# COMPAT: services/ai/action_leave.py:INTENT_NAME 와 byte-equivalent.
ACTION_LEAVE_INTENT_NAME: str = "create_therapist_leave"
