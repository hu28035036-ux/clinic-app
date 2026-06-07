"""modules.stats.repository — 통계 read-only 조회 helper (19-11 신규).

본 모듈은 ``Appointment`` / ``ManualCount`` / ``Treatment`` / ``Employee`` 의
*조회 전용* 함수를 제공한다 (통계 / 집계 흐름 정합). 실제 변경 ⊥ — 라우터
책임. DB 세션은 호출자 주입.

19-11 본 세션 범위:
  - 기간 범위 예약 조회.
  - approved 필터 조회.
  - ManualCount (체외충격파 수동 입력) 기간 조회.
  - 도수치료 Treatment 자동 조회 (role=therapist + code != ESWT_CODE + active).
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:stats_summary`` (line 3994~4001) / ``stats_by_hour`` (line
#         4069~4076) / ``stats_aggregate`` (line 3670~3674) / ``stats_aggregate``
#         (line 3693~3697) / ``_get_manual_treatment_rows`` (line 3732~3749) 등의
#         query 패턴 정합.

# SAFETY: 운영 DB 직접 접근 ⊥ — caller dependency 의 격리 세션만 사용. PII 응답
#         dict 빌드는 ``aggregators`` / ``service`` 가 담당 — 본 모듈은 ORM row
#         만 반환.

# NOTE: 본 repository 는 ``Appointment`` / ``ManualCount`` / ``Treatment`` /
#       ``Employee`` 만 다룸. 환자 / 휴무 / SMS 조회는 19-7 / 19-5 / 19-10
#       repository 가 담당.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def list_appointments_in_range(
    db: Any,
    *,
    start: datetime,
    end: datetime,
) -> list[Any]:
    """``[start, end)`` 범위의 예약 row.

    COMPAT: ``api.py:stats_summary`` (line 3994~4001) / ``stats_by_hour`` /
    ``stats_by_weekday`` / ``stats_by_treatment`` / ``stats_daily`` /
    ``stats_aggregate`` 의 동일 query 패턴 정합.
    """
    from app.models import models as _m

    return (
        db.query(_m.Appointment)
        .filter(
            _m.Appointment.start_at >= start,
            _m.Appointment.start_at < end,
        )
        .all()
    )


def list_approved_appointments_in_range(
    db: Any,
    *,
    start: datetime,
    end: datetime,
) -> list[Any]:
    """``[start, end)`` 범위 + ``status == "approved"`` 인 예약 row.

    COMPAT: ``api.py:stats_aggregate`` (line 3670~3674) 의 query 정합.
    """
    from app.models import models as _m

    return (
        db.query(_m.Appointment)
        .filter(
            _m.Appointment.start_at >= start,
            _m.Appointment.start_at < end,
            _m.Appointment.status == "approved",
        )
        .all()
    )


def list_manual_count_rows_in_date_range(
    db: Any,
    *,
    start_date_str: str,
    end_date_str: str,
    treatment_code: str,
) -> list[Any]:
    """``[start_date_str, end_date_str)`` 범위 + ``treatment_code`` 인 ``ManualCount`` row.

    COMPAT: ``api.py:stats_aggregate`` (line 3693~3697) 의 query 정합. 날짜 형식
    ``"YYYY-MM-DD"`` (caller 가 변환).
    """
    from app.models import models as _m

    return (
        db.query(_m.ManualCount)
        .filter(
            _m.ManualCount.count_date >= start_date_str,
            _m.ManualCount.count_date < end_date_str,
            _m.ManualCount.treatment_code == treatment_code,
        )
        .all()
    )


def list_manual_treatment_rows(db: Any) -> list[Any]:
    """role=therapist + code != ESWT_CODE + active=True 인 Treatment row (sort_order 정렬).

    COMPAT: ``api.py:_get_manual_treatment_rows`` (line 3732~3749) 정합.

    NOTE: '도수치료' 의 공식 정의 (v1.2.3+) — code LIKE 'manual%' 이 *아니라*
    role 기반 판정. 새 항목 (tx_<random> 코드) 도 자동 반영.
    """
    from app.models import constants as _C
    from app.models import models as _m

    return (
        db.query(_m.Treatment)
        .filter(
            _m.Treatment.role == "therapist",
            _m.Treatment.code != _C.ESWT_CODE,
            _m.Treatment.active == True,  # noqa: E712 — SQLAlchemy expr
        )
        .order_by(_m.Treatment.sort_order)
        .all()
    )


def list_manual_treatment_codes(db: Any) -> list[str]:
    """``list_manual_treatment_rows`` 결과의 ``code`` 만.

    COMPAT: ``api.py:_get_manual_therapy_codes`` (line 3752~3754) 정합.
    """
    return [t.code for t in list_manual_treatment_rows(db)]


def get_active_eswt_treatment(db: Any) -> Any | None:
    """활성 ``ESWT_CODE`` Treatment row (없으면 None).

    COMPAT: ``api.py:stats_aggregate`` (line 3660~3663) / ``stats_by_therapist``
    (line 3474~3477) 의 query 정합.
    """
    from app.models import constants as _C
    from app.models import models as _m

    return (
        db.query(_m.Treatment)
        .filter(
            _m.Treatment.code == _C.ESWT_CODE,
            _m.Treatment.active == True,  # noqa: E712 — SQLAlchemy expr
        )
        .first()
    )


def list_all_treatments(db: Any) -> list[Any]:
    """모든 Treatment row (활성 / 비활성 모두). 코드→이름 매핑 빌드용.

    COMPAT: ``api.py:stats_by_treatment`` (line 4181) 의
    ``{t.code: t.name for t in db.query(Treatment).all()}`` 정합.
    """
    from app.models import models as _m

    return db.query(_m.Treatment).all()


def list_therapist_employees(db: Any) -> list[Any]:
    """role=therapist 인 직원 row.

    COMPAT: ``api.py:stats_aggregate`` (line 3702~3703) /
    ``stats_manual_by_therapist`` (line 3702~3703) 정합.
    """
    from app.models import models as _m
    from app.modules.therapists import service as _therapists_service

    rows = (
        db.query(_m.Employee)
        .all()
    )
    return [e for e in rows if _therapists_service.employee_can_manual(e)]


def list_all_employees(db: Any) -> list[Any]:
    """모든 직원 row — id→name 매핑 빌드용.

    COMPAT: ``api.py:stats_by_therapist`` (line 3527) 정합.
    """
    from app.models import models as _m

    return db.query(_m.Employee).all()


__all__ = [
    "list_appointments_in_range",
    "list_approved_appointments_in_range",
    "list_manual_count_rows_in_date_range",
    "list_manual_treatment_rows",
    "list_manual_treatment_codes",
    "get_active_eswt_treatment",
    "list_all_treatments",
    "list_therapist_employees",
    "list_all_employees",
]
