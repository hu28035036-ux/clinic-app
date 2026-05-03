"""modules.leaves.rules — 휴무 도메인 규칙 (19-5 신규).

본 모듈은 휴무 / 연차 / 오전반차 / 오후반차 의 *도메인 규칙 단일 진실원천* 후보다.
19-4 ``app.modules.appointments.availability`` 의 휴무 helper 와 *byte-equivalent* 한
판정을 제공하며, 19-5 contract 테스트가 두 경로의 동등성을 검증한다.

19-5 본 세션 범위:
  - LEAVE_TYPE / LEAVE_KIND 상수 (단일 진실원천 후보).
  - 종일 / 오전반차 / 오후반차 *판정 helper* — 19-4 와 byte-equivalent.
  - 차단 사유 메시지 빌더.
  - DB / ORM import ⊥ — primitives + datetime / typing 만.
  - 19-4 availability 무수정 (사용자 명시) — 본 모듈은 *동등 helper*.

# COMPAT: 19-4 ``availability.py`` 의 ``LEAVE_TYPE_FULL/AM/PM/VALUES`` /
#         ``HALF_DAY_BOUNDARY_HOUR`` / ``is_morning_slot`` / ``is_afternoon_slot`` /
#         ``is_leave_blocking`` / ``find_blocking_leave`` 와 byte-equivalent. 19-5
#         contract 테스트가 정합 검증.

# SAFETY: 본 helper 는 *판정* 만 — 실제 차단 raise / DB 변경 ⊥. 호출자 책임.
#         devtools / curl POST 우회는 본 도메인 규칙 외 (19-9 시점 라우터 wire).

# NOTE: 휴무 표시 (19-3 calendar/view_models.py:LEAVE_TYPE_LABELS) ↔ 예약 차단 (19-4
#       availability.py:is_leave_blocking) ↔ 도메인 규칙 (본 19-5 rules.py) 의 LEAVE_TYPE
#       기준이 동일해야 함. 19-5 contract 테스트가 세 경로의 상수 셋 정합 검증.

# RISK: 반차 기준 시각은 *spec 02 정합 — 12:00 정확*. 변경 시 19-4 availability 와
#       19-3 calendar 의 leave_type_label 에도 영향 — 단일 진실원천 통합은 19-9 시점.
"""
from __future__ import annotations

from datetime import datetime
from typing import Final


# ─── LEAVE_TYPE 상수 (단일 진실원천 후보) ────────────────────────────────────

# DB 표준 — am / pm / full (m011 / m009 정합).
LEAVE_TYPE_FULL: Final[str] = "full"
LEAVE_TYPE_AM: Final[str] = "am"
LEAVE_TYPE_PM: Final[str] = "pm"

LEAVE_TYPE_VALUES: Final[tuple[str, ...]] = (
    LEAVE_TYPE_FULL,
    LEAVE_TYPE_AM,
    LEAVE_TYPE_PM,
)


# ─── LEAVE_KIND 상수 (m011 정합) ──────────────────────────────────────────────

LEAVE_KIND_ANNUAL: Final[str] = "annual"
LEAVE_KIND_MONTHLY: Final[str] = "monthly"

LEAVE_KIND_VALUES: Final[tuple[str, ...]] = (
    LEAVE_KIND_ANNUAL,
    LEAVE_KIND_MONTHLY,
)

LEAVE_KIND_DEFAULT: Final[str] = LEAVE_KIND_ANNUAL


# ─── 반차 기준 시각 (spec 02 정합) ────────────────────────────────────────────

# COMPAT: 19-4 ``availability.py:HALF_DAY_BOUNDARY_HOUR`` 와 동일 (12:00 정확).
HALF_DAY_BOUNDARY_HOUR: Final[int] = 12


# ─── 시간대 분류 (19-4 와 byte-equivalent) ────────────────────────────────────


def is_morning_slot(start_at: datetime) -> bool:
    """예약 시작 시각 < 12:00 (오전 슬롯).

    COMPAT: 19-4 ``availability.is_morning_slot`` 와 byte-equivalent.
    """
    return start_at.hour < HALF_DAY_BOUNDARY_HOUR


def is_afternoon_slot(start_at: datetime) -> bool:
    """예약 시작 시각 >= 12:00 (오후 슬롯).

    COMPAT: 19-4 ``availability.is_afternoon_slot`` 와 byte-equivalent.
    """
    return start_at.hour >= HALF_DAY_BOUNDARY_HOUR


# ─── 휴무 차단 판정 (spec 02) ────────────────────────────────────────────────


def is_leave_blocking(
    *,
    start_at: datetime,
    leave_type: str | None,
) -> bool:
    """치료사 휴무 row 가 주어진 예약 시작 시각을 차단하는가.

    매핑:
      ``leave_type="full"`` → 무조건 차단.
      ``leave_type="am"``   → 오전 슬롯 (< 12:00) 차단.
      ``leave_type="pm"``   → 오후 슬롯 (>= 12:00) 차단.
      그 외                 → 차단 ⊥ (안전 fallback).

    COMPAT: 19-4 ``availability.is_leave_blocking`` 와 byte-equivalent.
    """
    if not leave_type:
        return False
    if leave_type == LEAVE_TYPE_FULL:
        return True
    if leave_type == LEAVE_TYPE_AM:
        return is_morning_slot(start_at)
    if leave_type == LEAVE_TYPE_PM:
        return is_afternoon_slot(start_at)
    return False


def find_blocking_leave(
    *,
    therapist_id: str,
    start_at: datetime,
    leaves: list[dict] | None,
) -> dict | None:
    """``leaves`` 안에서 ``therapist_id`` + ``start_at.date()`` 매칭 + 시간 차단 row 반환.

    COMPAT: 19-4 ``availability.find_blocking_leave`` 와 byte-equivalent.
    """
    target_date = start_at.date().isoformat()
    for lv in leaves or []:
        if lv.get("employee_id") != therapist_id:
            continue
        if lv.get("leave_date") != target_date:
            continue
        if is_leave_blocking(start_at=start_at, leave_type=lv.get("leave_type")):
            return lv
    return None


# ─── 차단 사유 메시지 빌더 (19-9 시점 라우터 채택 후보) ──────────────────────


# NOTE: 19-4 시점 백엔드 차단 *미구현* (사용자 명시 "기존 규칙을 보존") —
#       19-9 시점 라우터가 채택할 때 본 메시지 빌더 사용. 한국어 사용자 노출 메시지.
LEAVE_BLOCK_MESSAGE_FULL: Final[str] = "치료사 종일 휴무로 예약을 잡을 수 없습니다."
LEAVE_BLOCK_MESSAGE_AM: Final[str] = "치료사 오전 반차로 오전 시간 예약을 잡을 수 없습니다."
LEAVE_BLOCK_MESSAGE_PM: Final[str] = "치료사 오후 반차로 오후 시간 예약을 잡을 수 없습니다."


def leave_block_message(leave_type: str | None) -> str:
    """차단 사유 한국어 메시지.

    NOTE: 19-9 시점 라우터가 ``raise HTTPException(400, leave_block_message(...))`` 로
    사용 가능. 알 수 없는 leave_type → 빈 문자열 (호출자가 fallback 메시지 결정).
    """
    if leave_type == LEAVE_TYPE_FULL:
        return LEAVE_BLOCK_MESSAGE_FULL
    if leave_type == LEAVE_TYPE_AM:
        return LEAVE_BLOCK_MESSAGE_AM
    if leave_type == LEAVE_TYPE_PM:
        return LEAVE_BLOCK_MESSAGE_PM
    return ""


# ─── 휴무 표시-차단 일관성 검증 helper (19-3 / 19-4 / 19-5 정합) ──────────────


def normalize_leave_type(value: str | None) -> str:
    """raw ``leave_type`` 값을 표준 LEAVE_TYPE 으로 정규화.

    COMPAT: ``api.py:list_employee_leaves`` 의 ``r.leave_type or "full"`` 패턴 정합.
    None / 빈 값 → "full" (DB 기본값).
    """
    if not value:
        return LEAVE_TYPE_FULL
    if value in LEAVE_TYPE_VALUES:
        return value
    # 알 수 없는 값은 그대로 통과 (raw 데이터 보존 — 호출자 결정).
    return value


def normalize_leave_kind(value: str | None) -> str:
    """raw ``leave_kind`` 값을 표준 LEAVE_KIND 로 정규화.

    COMPAT: ``api.py:list_employee_leaves`` 의 ``r.leave_kind or "annual"`` 패턴 정합.
    None / 빈 값 → "annual" (DB 기본값).
    """
    if not value:
        return LEAVE_KIND_DEFAULT
    if value in LEAVE_KIND_VALUES:
        return value
    return value


__all__ = [
    "LEAVE_TYPE_FULL",
    "LEAVE_TYPE_AM",
    "LEAVE_TYPE_PM",
    "LEAVE_TYPE_VALUES",
    "LEAVE_KIND_ANNUAL",
    "LEAVE_KIND_MONTHLY",
    "LEAVE_KIND_VALUES",
    "LEAVE_KIND_DEFAULT",
    "HALF_DAY_BOUNDARY_HOUR",
    "is_morning_slot",
    "is_afternoon_slot",
    "is_leave_blocking",
    "find_blocking_leave",
    "LEAVE_BLOCK_MESSAGE_FULL",
    "LEAVE_BLOCK_MESSAGE_AM",
    "LEAVE_BLOCK_MESSAGE_PM",
    "leave_block_message",
    "normalize_leave_type",
    "normalize_leave_kind",
]
