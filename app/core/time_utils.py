"""core.time_utils — Asia/Seoul 시간 유틸 helper (신규).

19-P-2 §2-1 V2 트리의 ``app/core/time_utils.py`` — 신규 helper.

본 모듈은 modules 가 오늘 / 내일 / 점심창 / 반차 / Asia/Seoul 시간 처리를 일관되게
할 때 쓸 수 있는 helper 를 제공한다. 19-1 시점에는 *기존 라우터가 참조하지 않는다* —
신규 modules 가 점진적으로 채택할 수 있는 facade.

# NOTE: 본 helper 의 시간 기준은 *Asia/Seoul* 로 고정. 기존 ``api.py`` 안의
#       ``datetime`` 직접 사용 위치 (점심창 / 반차 12:00 기준 / 휴무일 비교 / 통계
#       날짜 범위) 는 19-1 시점에 *변경하지 않는다*. 본 모듈은 향후 19-4
#       availability / 19-5 leaves / 19-11 stats 등이 채택할 때 사용.

# NOTE: 반차 기준 = 12:00 정확. ``leave_type=am`` < 12:00 차단 / ``leave_type=pm`` >= 12:00
#       차단 (19-P-7 R-APPT-04 정합). 19-4 / 19-5 분리 시점에 본 helper 채택 검토.

# RISK: tz 처리에서 naive datetime vs aware datetime 혼용 시 비교 오류 가능.
#       본 helper 는 *naive datetime* (Asia/Seoul 로컬) 기준으로 통일 — 기존
#       SQLAlchemy 컬럼 (``Appointment.start_at`` 등) 과 정합.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta


# ─── 반차 기준 시각 (12:00 정확) ──────────────────────────────────────────────

NOON: time = time(12, 0)


# ─── 오늘 / 내일 (Asia/Seoul 로컬 기준 — 운영 환경 OS tz 따름) ─────────────────

def today() -> date:
    """오늘 날짜 (Asia/Seoul 로컬). 운영 환경은 KR locale 가정."""
    return datetime.now().date()


def tomorrow() -> date:
    """내일 날짜 (오늘 + 1일)."""
    return today() + timedelta(days=1)


# ─── am / pm 분기 helper ─────────────────────────────────────────────────────

def is_morning(t: time) -> bool:
    """주어진 시각이 오전 (< 12:00) 인지.

    NOTE: ``leave_type="am"`` (오전반차) 차단 기준. 12:00 정각은 *오후* 로 분류.
    """
    return t < NOON


def is_afternoon(t: time) -> bool:
    """주어진 시각이 오후 (>= 12:00) 인지.

    NOTE: ``leave_type="pm"`` (오후반차) 차단 기준. 12:00 정각은 *오후* 로 분류.
    """
    return t >= NOON


# ─── 점심창 helper (modules/appointments/availability 후보) ────────────────────

def lunch_window(lunch_start: time, lunch_end: time) -> tuple[time, time]:
    """점심창 (start, end) 튜플. 기존 ``_lunch_window`` 와 호환되는 표현.

    NOTE: 본 helper 는 점심창 *값* 만 반환 — 차단 로직은 별도. 19-4 availability
    분리 시점에 ``_check_lunch_block`` 채택 검토 (TODO(19-4)).
    """
    return (lunch_start, lunch_end)


def is_within_lunch(t: time, lunch_start: time, lunch_end: time) -> bool:
    """주어진 시각이 점심창 안에 있는지 (lunch_start ≤ t < lunch_end).

    NOTE: 점심 시작 시각은 차단 *대상*, 종료 시각은 차단 *제외* (운영 정책 정합).
    """
    return lunch_start <= t < lunch_end


# ─── ISO 형식 helper (응답 직렬화 — datetime → "YYYY-MM-DDTHH:MM:SS") ────────

def isoformat_minute(dt: datetime) -> str:
    """``YYYY-MM-DDTHH:MM`` 형식 (초 / microsecond 절단). 응답 키 형식 보존용.

    NOTE: 기존 ``Appointment.start_at`` 등 datetime 컬럼 직렬화 시 분 단위까지만
    노출하는 패턴 정합 (19-P-1 §21 응답 키 형식).
    """
    return dt.strftime("%Y-%m-%dT%H:%M")


__all__ = [
    "NOON",
    "today",
    "tomorrow",
    "is_morning",
    "is_afternoon",
    "lunch_window",
    "is_within_lunch",
    "isoformat_minute",
]
