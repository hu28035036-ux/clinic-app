"""modules.appointments.availability — 예약 가능 여부 / 충돌 / 휴무 / 반차 / 점심창 /
낙관적 락 판정 순수 helper (19-4 신규).

본 모듈은 ``app/routers/api.py`` 의 ``_lunch_window`` (line 64~84) /
``_check_lunch_block`` (line 87~107) / ``_check_version`` (line 1664~1673) /
``_bump_version`` (line 1676~1677) 의 *판정 로직* 을 *동등한 순수 helper* 로 추출한다.
또한 *현재 백엔드 미구현* 인 도수치료 중복 / 휴무 (full/am/pm) 차단의 *판정 helper*
도 정의 (실제 차단 raise 는 호출자 책임 — 19-4 시점 라우터 미채택).

19-4 본 세션 범위:
  - 판정 helper 만 정의 — 기존 응답 / 동작과 byte-equivalent.
  - DB / ORM / SQLAlchemy import ⊥ — primitives 또는 read-only attribute 만.
  - 라우터 무수정 (helper 미채택).
  - 백엔드 차단 코드 *신설* ⊥ (사용자 지시문 "기존 규칙을 보존").
  - xfail 7건 + skip 1건 정방향 전환 ⊥ (백엔드 차단 미구현 그대로).

# COMPAT: ``api.py:_lunch_window`` / ``_check_lunch_block`` / ``_check_version`` 와
#         byte-equivalent 결과. 호출 시그니처는 *primitives* 로 변경 — 본 helper 는
#         FastAPI HTTPException 을 raise 하지 않음 (반환값은 boolean / dict).
#         차단 raise 는 *호출자* 가 ``raise HTTPException(400, ...)`` 로 처리.

# SAFETY: ``devtools / curl POST 우회 방지`` — 본 helper 는 *판정* 만, 실제 차단은
#         호출자 책임. 19-4 시점 라우터가 채택 ⊥ — 19-9 appointments 본체 분리 시
#         라우터가 본 helper 를 호출하여 일관 검증.

# NOTE: 휴무 차단 (full/am/pm) 은 *반차 12:00 기준* (spec 02). am 반차 = 휴무자가
#       오전 (< 12:00) 휴무 → 오전 슬롯 차단. pm 반차 = 오후 (>= 12:00) 휴무 →
#       오후 슬롯 차단. 본 helper 는 *판정만* — 실제 차단은 19-9 시점 라우터 wire.

# RISK: 도수치료 중복 차단 (spec 01 §1) 은 ``Treatment.role == "therapist" and code !=
#       ESWT_CODE`` 분류 기반. 본 helper 는 *manual code 셋* 을 인자로 받음 —
#       치료항목 정의 변경 (19-6 시점) 영향 ⊥.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Final


# ─── 점심창 정책 상수 (api.py 인라인 정합) ───────────────────────────────────

# 점심창 분 단위 [start, end) — 24시간 분 표기 (0 ~ 1439 = 24*60 - 1).
LUNCH_MIN_BOUND: Final[int] = 0
LUNCH_MAX_BOUND: Final[int] = 24 * 60


# ─── 점심창 helper (api.py:_lunch_window 와 동등 — pure-input) ────────────────


def parse_lunch_window(
    *,
    enabled: bool,
    lunch_start: str | None,
    lunch_end: str | None,
) -> tuple[int, int, str, str] | None:
    """``config.json`` primitives → ``(start_min, end_min, start_str, end_str)`` 또는 None.

    COMPAT: ``api.py:_lunch_window`` (line 64~84) 와 byte-equivalent. ``enabled=False``,
    형식 이상 (HH:MM 분리 실패), 범위 초과 (>= 24:00), end <= start 면 None (= 차단 비활성).

    NOTE: ``api.py`` 의 ``load_config()`` 호출은 호출자 책임. 본 helper 는 *값 변환*만.
    """
    if not enabled:
        return None
    try:
        ls_str = (lunch_start or "").strip()
        le_str = (lunch_end or "").strip()
        sh, sm = ls_str.split(":")
        eh, em = le_str.split(":")
        s = int(sh) * 60 + int(sm)
        e = int(eh) * 60 + int(em)
    except Exception:
        return None
    if not (LUNCH_MIN_BOUND <= s < LUNCH_MAX_BOUND and LUNCH_MIN_BOUND <= e <= LUNCH_MAX_BOUND):
        return None
    if e <= s:
        return None
    return (s, e, ls_str, le_str)


def overlaps_lunch_window(
    start_at: datetime,
    duration_min: int | None,
    window: tuple[int, int, str, str] | None,
) -> bool:
    """예약 시간창 ``[start_at, start_at+duration)`` 가 점심창과 겹치는지.

    COMPAT: ``api.py:_check_lunch_block`` (line 87~107) 의 *겹침 판정* 부분과
    byte-equivalent. ``window=None`` (점심 비활성) 또는 ``duration_min<=0`` 이면 False.

    NOTE: 본 helper 는 boolean 반환만 — 실제 차단 raise 는 호출자.
    """
    if window is None:
        return False
    try:
        dur = int(duration_min or 0)
    except Exception:
        return False
    if dur <= 0:
        return False
    s_min, e_min, _ls_str, _le_str = window
    sm = start_at.hour * 60 + start_at.minute
    em = sm + dur
    return em > s_min and sm < e_min


def lunch_block_message(window: tuple[int, int, str, str]) -> str:
    """점심창 차단 시 표시할 한국어 메시지.

    COMPAT: ``api.py:_check_lunch_block`` (line 105~106) 의 메시지 포맷과 일치.
    """
    _s_min, _e_min, ls_str, le_str = window
    return f"점심시간({ls_str}~{le_str})에는 예약을 잡을 수 없습니다."


# ─── 낙관적 락 (api.py:_check_version / _bump_version 와 동등) ────────────────


VERSION_CONFLICT_ERROR_CODE: Final[str] = "version_conflict"
VERSION_CONFLICT_MESSAGE: Final[str] = (
    "다른 PC에서 먼저 수정되었습니다. 최신 정보를 불러오세요."
)


def is_version_conflict(db_version: int | None, client_version: Any) -> bool:
    """클라이언트가 보낸 ``version`` 이 DB 버전과 다른가 (낙관적 락 충돌).

    COMPAT: ``api.py:_check_version`` (line 1664~1673) 와 byte-equivalent.
    ``client_version=None`` → False (검사 스킵 정합).

    NOTE: ``api.py:_check_version`` 은 ``raise HTTPException(409, ...)`` 까지 수행.
    본 helper 는 *판정만* — 호출자가 boolean 으로 받아 raise 책임.
    """
    if client_version is None:
        return False
    return (db_version or 0) != client_version


def version_conflict_detail(db_version: int | None) -> dict:
    """409 응답 ``detail`` dict 빌드.

    COMPAT: ``api.py:_check_version`` (line 1669~1673) 의 dict literal 정합.
    """
    return {
        "error": VERSION_CONFLICT_ERROR_CODE,
        "message": VERSION_CONFLICT_MESSAGE,
        "current_version": int(db_version or 0),
    }


def next_version(db_version: int | None) -> int:
    """``_bump_version`` 의 pure 버전 — DB 변경은 호출자 책임.

    COMPAT: ``api.py:_bump_version`` (line 1676~1677) 와 동등.
    """
    return (db_version or 0) + 1


# ─── 시간 충돌 검사 (도수 중복 차단 후보 — 백엔드 미구현, helper 만 정의) ────


def appointments_overlap(
    *,
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> bool:
    """두 시간창 ``[a_start, a_end)`` 와 ``[b_start, b_end)`` 가 겹치는가.

    NOTE: 닫힘 / 열림 경계 — 양 끝이 정확히 같은 경우 (예: a_end == b_start) 는 *허용*
    (인접만, 겹침 아님). spec 01 §1 정합.
    """
    return a_end > b_start and a_start < b_end


def is_manual_treatment(
    treatment_codes: list[str] | None,
    manual_code_set: set[str],
) -> bool:
    """``treatment_codes`` 안에 도수치료 코드가 하나라도 있는가.

    NOTE: 도수 중복 차단 (spec 01 §1) 의 핵심 분기 — *어느 한 쪽에라도 도수 포함이면
    중복 검사 대상*. ESWT 는 도수가 아니므로 ``manual_code_set`` 에 미포함 (호출자가
    `_therapist_only_codes_set` 으로 사전 필터).

    RISK: 19-4 시점 라우터 미채택 — 백엔드 차단 코드 신설은 본 세션 범위 외.
    실제 wire 는 19-9 appointments 본체 분리 시점.
    """
    if not treatment_codes:
        return False
    return any(c in manual_code_set for c in treatment_codes)


def has_manual_conflict_at_slot(
    *,
    new_codes: list[str] | None,
    new_start: datetime,
    new_end: datetime,
    new_id: str | None,
    existing_appointments: list[dict],
    manual_code_set: set[str],
) -> bool:
    """같은 치료사 / 같은 시간 슬롯에 도수치료 중복이 있는가 (spec 01 §1 판정 후보).

    인자:
      ``new_codes``        : 신규 / 수정 예약의 ``treatment_codes``.
      ``new_start/new_end``: 신규 / 수정 예약의 시간창.
      ``new_id``           : 수정 시 자기 자신 제외용 (None = 신규).
      ``existing_appointments``: 같은 치료사의 같은 날 (또는 더 좁은 범위) 예약 목록.
                                각 dict 는 ``{"id", "start", "end", "codes", "status"}``.
      ``manual_code_set``  : 도수치료 코드 집합 (``_therapist_only_codes_set``).

    NOTE: ``status == "canceled"`` 는 중복 검사에서 제외 (spec 01 §1).
    NOTE: 수정 시 ``new_id == existing.id`` 면 자기 자신 → 제외.
    NOTE: 신규 또는 기존 중 *어느 한 쪽이라도* 도수 포함이면 중복 차단 대상.
    RISK: 19-4 시점 *라우터 미채택* — wire 는 19-9 시점.
    """
    new_has_manual = is_manual_treatment(new_codes, manual_code_set)
    for existing in existing_appointments or []:
        if existing.get("status") == "canceled":
            continue
        if new_id is not None and existing.get("id") == new_id:
            continue
        ex_codes = existing.get("codes") or []
        ex_has_manual = is_manual_treatment(ex_codes, manual_code_set)
        # 둘 다 도수 미포함이면 같은 시간이라도 허용.
        if not (new_has_manual or ex_has_manual):
            continue
        ex_start = existing.get("start")
        ex_end = existing.get("end")
        if ex_start is None or ex_end is None:
            continue
        if appointments_overlap(
            a_start=new_start, a_end=new_end,
            b_start=ex_start, b_end=ex_end,
        ):
            return True
    return False


# ─── 휴무 / 반차 차단 (백엔드 미구현 — helper 만 정의) ────────────────────────


# 반차 기준 시각 (spec 02) — 12:00 정확.
HALF_DAY_BOUNDARY_HOUR: Final[int] = 12

LEAVE_TYPE_FULL: Final[str] = "full"
LEAVE_TYPE_AM: Final[str] = "am"
LEAVE_TYPE_PM: Final[str] = "pm"

LEAVE_TYPE_VALUES: Final[tuple[str, ...]] = (
    LEAVE_TYPE_FULL,
    LEAVE_TYPE_AM,
    LEAVE_TYPE_PM,
)


def is_morning_slot(start_at: datetime) -> bool:
    """예약 시작 시각 < 12:00 (오전 슬롯) 정합.

    NOTE: 반차 기준은 *시작 시각* — duration 으로 12:00 을 넘어가더라도 슬롯 분류는
    시작 시각으로 결정 (spec 02 §1 정합).
    """
    return start_at.hour < HALF_DAY_BOUNDARY_HOUR


def is_afternoon_slot(start_at: datetime) -> bool:
    """예약 시작 시각 >= 12:00 (오후 슬롯)."""
    return start_at.hour >= HALF_DAY_BOUNDARY_HOUR


def is_leave_blocking(
    *,
    start_at: datetime,
    leave_type: str | None,
) -> bool:
    """치료사 휴무 row 가 주어진 예약 시작 시각을 차단하는가 (spec 02 판정 후보).

    매핑:
      ``leave_type="full"``    → 무조건 차단 (종일).
      ``leave_type="am"``      → 오전 슬롯 (< 12:00) 차단. 오후 OK.
      ``leave_type="pm"``      → 오후 슬롯 (>= 12:00) 차단. 오전 OK.
      ``leave_type=None`` 또는 알 수 없음 → 차단 ⊥ (안전 fallback).

    NOTE: 본 helper 는 *동일 날짜 휴무가 있다는 전제* 에서 호출됨 — 호출자가 미리
    ``EmployeeLeave`` row 의 날짜 일치를 확인. 본 helper 는 *시간 기반 분기* 만.
    RISK: 19-4 시점 *라우터 미채택* — xfail 4건 (test_therapist_leave.py) 그대로.
    """
    if not leave_type:
        return False
    if leave_type == LEAVE_TYPE_FULL:
        return True
    if leave_type == LEAVE_TYPE_AM:
        return is_morning_slot(start_at)
    if leave_type == LEAVE_TYPE_PM:
        return is_afternoon_slot(start_at)
    # 알 수 없는 leave_type — 안전 fallback (차단 ⊥).
    return False


def find_blocking_leave(
    *,
    therapist_id: str,
    start_at: datetime,
    leaves: list[dict],
) -> dict | None:
    """``leaves`` 안에서 ``therapist_id`` + ``start_at.date()`` 매칭 + 시간 차단 row 반환.

    인자:
      ``leaves``: 같은 날의 휴무 목록 (호출자가 미리 조회). 각 dict 는
                  ``{"employee_id", "leave_date", "leave_type"}`` 포함.

    반환: 차단 매치된 휴무 dict 또는 None.
    NOTE: 호출자가 본 row 의 ``memo`` 등을 활용해 차단 메시지 조립 가능.
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


# ─── 예약 종료시각 계산 (api.py 인라인 패턴 정합) ────────────────────────────


def compute_end_at(start_at: datetime, duration_min: int) -> datetime:
    """``start_at + duration_min`` → ``end_at``.

    COMPAT: ``api.py:1633`` / ``api.py:1705`` 의 ``start_at + timedelta(minutes=duration_min)``
    인라인 패턴 정합.
    """
    return start_at + timedelta(minutes=int(duration_min or 0))


__all__ = [
    # 점심창
    "LUNCH_MIN_BOUND",
    "LUNCH_MAX_BOUND",
    "parse_lunch_window",
    "overlaps_lunch_window",
    "lunch_block_message",
    # 낙관적 락
    "VERSION_CONFLICT_ERROR_CODE",
    "VERSION_CONFLICT_MESSAGE",
    "is_version_conflict",
    "version_conflict_detail",
    "next_version",
    # 시간 충돌 / 도수 중복 (helper 만 — 백엔드 미구현)
    "appointments_overlap",
    "is_manual_treatment",
    "has_manual_conflict_at_slot",
    # 휴무 / 반차 (helper 만 — 백엔드 미구현)
    "HALF_DAY_BOUNDARY_HOUR",
    "LEAVE_TYPE_FULL",
    "LEAVE_TYPE_AM",
    "LEAVE_TYPE_PM",
    "LEAVE_TYPE_VALUES",
    "is_morning_slot",
    "is_afternoon_slot",
    "is_leave_blocking",
    "find_blocking_leave",
    # 종료시각
    "compute_end_at",
]
