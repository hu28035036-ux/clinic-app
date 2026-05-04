"""modules.appointments.schemas — 예약 응답 dict 키 contract 상수 (19-9 신규).

본 모듈은 ``api.py`` 의 모든 예약 핸들러 응답 dict 의 *키 셋* 을 contract 상수로
명시한다. UI / SMS / 통계 / AI 가 의존하는 응답 키를 *임의 변경 ⊥* — contract
테스트가 회귀 검출.

19-9 본 세션 범위:
  - 응답 키 셋 상수 (frozenset) — 핸들러 별.
  - Pydantic 모델 정의 ⊥ (입력 모델은 ``app.models.schemas`` 그대로 — 기존 정합).
  - 본 contract 상수는 *키 회귀 보호* 용 — 19-9 contract 테스트가 응답 dict 의
    ``keys() == CONTRACT`` 검증.
  - 라우터 무수정.

# COMPAT: 본 contract 상수와 ``api.py`` 응답 dict 의 키 셋이 *byte-equivalent*.
#         contract 변경 ⊥ — 변경 시 UI / SMS / 통계 / AI 모두 회귀 위험.

# SAFETY: 본 모듈은 *상수 정의* 만 — 동작 변경 ⊥. Pydantic 모델 정의 ⊥.

# NOTE: 입력 모델 (``AppointmentIn`` / ``AppointmentUpdate`` / ``ApproveAction``
#       / ``CancelAction`` / ``AssignmentChange``) 은 ``app.models.schemas`` 에
#       그대로 — 본 모듈은 *응답 키 회귀 보호* 만 담당.

# RISK: 응답 키가 추가되는 경우만 contract 갱신 (UI 가 이미 알고 있는 키 그대로
#       남김). 키 *제거* / *이름 변경* 은 ``AI_WORKING_RULES.md`` §1.7 정합 — 별도
#       합의 필수.
"""
from __future__ import annotations

from typing import Final


# ─── POST /appointments 응답 키 (api.py:1661 정합) ───────────────────────────


CREATE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"id", "status"})


# ─── PUT /appointments/{aid} 응답 키 (api.py:1744 정합) ──────────────────────


UPDATE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok", "version"})


# ─── POST /appointments/{aid}/assign 응답 키 (api.py:1791 정합) ──────────────


ASSIGN_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok", "version"})


# ─── POST /appointments/{aid}/approve 응답 키 (api.py:1979 정합) ─────────────


APPROVE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok", "status", "version"})


# ─── POST /appointments/{aid}/revert-approve 응답 키 (api.py:2003 정합) ──────


REVERT_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok", "version"})


# ─── POST /appointments/{aid}/cancel 응답 키 (api.py:2021 정합) ──────────────


CANCEL_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok", "version"})


# ─── DELETE /appointments/{aid} 응답 키 (api.py:2038 정합) ───────────────────


DELETE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"ok"})


# ─── POST /appointments/{aid}/split-code 응답 키 ─────────────────────────────


# split=False 분기 (api.py:1877 정합) — 4키.
SPLIT_NO_SPLIT_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"ok", "split", "id", "version"}
)

# split=True 분기 (api.py:1925~1931 정합) — 5키.
SPLIT_REAL_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"ok", "split", "original_id", "new_id", "version"}
)


# ─── _serialize_appointment 응답 키 (api.py:194~219 정합) ────────────────────


# 9 top-level 키 — id / start / end / color / textColor / extendedProps + (FullCalendar 표준).
APPOINTMENT_SERIALIZE_TOP_KEYS: Final[frozenset[str]] = frozenset(
    {"id", "start", "end", "color", "textColor", "extendedProps"}
)

# extendedProps 안의 키 — 16개 + 20-3-1 F-10 추가 = 17개 (api.py:199~218 정합).
APPOINTMENT_EXTENDED_PROPS_KEYS: Final[frozenset[str]] = frozenset(
    {
        "patient_id",
        "patient_name",
        "patient_chart_no",
        "patient_phone",
        "patient_birth_date",
        "patient_memo",
        "therapist_id",
        "treatment_codes",
        "status",
        "memo",
        "approved_at",
        "approved_by",
        "opacity",
        "duration_min",
        "assignments",
        "is_new_patient",
        "version",
        # 20-3-1 (post-19-P / F-10): 노쇼 별도 필드 (status="canceled" 와 동시 가능)
        "no_show",
        # 20-3-4 (post-19-P / F-2): 반복 예약 시리즈 FK (단일 예약은 None)
        "series_id",
        # 20-3-5 (post-19-P / F-3): 자원 (치료실) FK (자원 미지정은 None)
        "resource_id",
    }
)


# ─── GET /patients/{pid}/manual-history-summary 응답 키 (api.py:1516~1522 정합)


MANUAL_HISTORY_SUMMARY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "patient_id",
        "has_manual_history",
        "manual_count",
        "has_new_patient_flag",
        "manual_appointment_ids",
    }
)


# ─── GET /patients/{pid}/history 응답 envelope 키 (api.py:1597~1603 정합) ────


PATIENT_HISTORY_ENVELOPE_KEYS: Final[frozenset[str]] = frozenset(
    {"total", "offset", "limit", "days", "items"}
)


__all__ = [
    "CREATE_RESPONSE_KEYS",
    "UPDATE_RESPONSE_KEYS",
    "ASSIGN_RESPONSE_KEYS",
    "APPROVE_RESPONSE_KEYS",
    "REVERT_RESPONSE_KEYS",
    "CANCEL_RESPONSE_KEYS",
    "DELETE_RESPONSE_KEYS",
    "SPLIT_NO_SPLIT_RESPONSE_KEYS",
    "SPLIT_REAL_RESPONSE_KEYS",
    "APPOINTMENT_SERIALIZE_TOP_KEYS",
    "APPOINTMENT_EXTENDED_PROPS_KEYS",
    "MANUAL_HISTORY_SUMMARY_KEYS",
    "PATIENT_HISTORY_ENVELOPE_KEYS",
]
