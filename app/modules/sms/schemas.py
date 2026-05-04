"""modules.sms.schemas — SMS API 응답 키 contract 상수 (19-10 신규).

본 모듈은 ``api.py`` 의 모든 SMS 핸들러 응답 dict 의 *키 셋* 을 contract 상수로
명시한다. UI / 외부 호출자가 의존하는 응답 키를 *임의 변경 ⊥* — contract 테스트가
회귀 검출.

19-10 본 세션 범위:
  - 응답 키 셋 상수 (frozenset).
  - Pydantic 모델 정의 ⊥.
  - 라우터 무수정.

# COMPAT: 본 contract 상수와 ``api.py`` 응답 dict 의 키 셋이 *byte-equivalent*.
#         contract 변경 ⊥ — 변경 시 UI 회귀 위험.

# SAFETY: 본 모듈은 *상수 정의* 만 — 동작 변경 ⊥. 비밀 / 환자 PII 미참조.

# NOTE: 입력 모델 (현재 라우터가 ``payload: dict`` 로 수동 처리) 은 ``app.models.schemas``
#       에 *없음* — 본 19-10 시점에도 추가 ⊥ (사용자 명시 "payload 시그니처 무수정").

# RISK: 응답 키 *제거* / *이름 변경* 은 ``AI_WORKING_RULES.md`` §1.7 정합 — 별도
#       합의 필수.
"""
from __future__ import annotations

from typing import Final


# ─── GET /api/sms/setting 응답 키 (api.py:2929~2939 정합) ────────────────────


SMS_SETTING_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "munjanara_id",
        "munjanara_pw",
        "munjanara_key",
        "sender_phone",
        "clinic_phone",
        "clinic_name",
        "api_url",
    }
)


# ─── POST /api/sms/setting 응답 키 (api.py:2969 정합) ────────────────────────


SMS_SETTING_UPDATE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok"})


# ─── GET /api/sms/templates / POST / PUT 응답 키 (api.py:3036~3044 정합) ────


SMS_TEMPLATE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"id", "name", "body", "sort_order", "active", "updated_at"}
)


# ─── DELETE /api/sms/templates/{tid} 응답 키 (api.py:3112 정합) ──────────────


SMS_TEMPLATE_DELETE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok"})


# ─── GET /api/sms/tomorrow-targets 항목 키 (api.py:3022~3029 정합) ───────────


SMS_TOMORROW_TARGET_KEYS: Final[frozenset[str]] = frozenset(
    {
        "appointment_id",
        "patient_id",
        "chart_no",
        "name",
        "phone",
        "reserved_at",
        "body",
        "treatment_summary",
    }
)


# ─── POST /api/sms/send 응답 envelope 키 (api.py:3442~3445 정합) ─────────────


SMS_SEND_ENVELOPE_KEYS: Final[frozenset[str]] = frozenset(
    {"sent", "failed", "total", "results"}
)


# ─── POST /api/sms/send results 항목 필수 키 (api.py:3273~3274 / 3425~3426) ──


# 모든 항목이 *최소* 갖춰야 할 4키. 분기에 따라 ``status_code`` 추가 가능.
SMS_SEND_RESULT_REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
    {"phone", "result", "kind", "detail"}
)


__all__ = [
    "SMS_SETTING_RESPONSE_KEYS",
    "SMS_SETTING_UPDATE_RESPONSE_KEYS",
    "SMS_TEMPLATE_RESPONSE_KEYS",
    "SMS_TEMPLATE_DELETE_RESPONSE_KEYS",
    "SMS_TOMORROW_TARGET_KEYS",
    "SMS_SEND_ENVELOPE_KEYS",
    "SMS_SEND_RESULT_REQUIRED_KEYS",
]
