"""modules.appointments.repository — 예약 row read-only 조회 helper (19-9 신규).

본 모듈은 ``Appointment`` / ``TreatmentAssignment`` 테이블의 *조회 전용* 함수만
제공한다. 실제 변경 (create / update / delete / approve / cancel) 은 라우터 책임.

19-9 본 세션 범위:
  - 단건 / 날짜 범위 / 환자별 (canceled 제외 / approved) 조회 helper.
  - 마지막 예약 (per patient) 매핑 빌더.
  - DB 세션은 호출자 주입 — 운영 DB 직접 open ⊥, lazy import.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:list_appointments`` (line 1608) / ``last_appointments``
#         (line 1487) / ``patient_manual_history_summary`` (line 1498) /
#         ``patient_history`` (line 1525) / ``update_appointment`` 의 ``db.get``
#         (line 1683) / ``cancel_appointment`` 의 ``db.get`` (line 2009) 등 query
#         패턴 정합.

# SAFETY: 운영 DB 직접 접근 ⊥ — caller dependency 의 격리 세션만 사용. PII 응답
#         dict 빌드는 ``service`` 가 담당 — 본 모듈은 ORM row 만 반환.

# NOTE: 본 repository 는 ``Appointment`` / ``TreatmentAssignment`` 만 다룸 —
#       ``Patient`` / ``Employee`` 조회는 19-7 patients.repository / 19-8
#       therapists.repository 가 담당 (도메인 경계 분리).

# RISK: 날짜 파싱 / timezone 정규화는 라우터 책임 (api.py:1611~1614). 본 repository
#       는 *naive datetime* 만 받음 (호출자가 사전 정규화).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def get_appointment_by_id(db: Any, appointment_id: str) -> Any | None:
    """ID 로 예약 단건 조회.

    COMPAT: ``api.py:update_appointment`` (line 1683) / ``cancel_appointment``
    (line 2009) / ``approve_appointment`` (line 1960) / ``revert_approve``
    (line 1986) / ``delete_appointment`` (line 2027) / ``split_appointment_code``
    (line 1811) / ``change_assignment`` (line 1751) 의 ``db.get(Appointment,
    aid)`` 정합.
    """
    from app.models import models as _m

    return db.get(_m.Appointment, appointment_id)


def list_appointments_in_range(
    db: Any,
    *,
    start_naive: datetime,
    end_naive: datetime,
) -> list[Any]:
    """``[start_naive, end_naive)`` 범위의 예약 row 조회.

    COMPAT: ``api.py:list_appointments`` (line 1615~1617) 의
    ``filter(start_at >= ts, start_at < te)`` 정합. 호출자가 timezone 사전 정규화
    (naive datetime 만 받음).
    """
    from app.models import models as _m

    return (
        db.query(_m.Appointment)
        .filter(
            _m.Appointment.start_at >= start_naive,
            _m.Appointment.start_at < end_naive,
        )
        .all()
    )


def list_active_appointments_for_patient(db: Any, patient_id: str) -> list[Any]:
    """``status != "canceled"`` 인 환자 예약 row.

    COMPAT: ``api.py:patient_manual_history_summary`` (line 1504~1507) 의
    ``filter(patient_id == pid, status != "canceled")`` 정합.

    NOTE: 19-7 ``patients.repository.list_patient_appointments_active`` 와
    동일 결과 — 환자 / 예약 도메인 경계가 같은 query 를 공유. 19-9 시점은
    *예약 도메인 관점* 의 helper 로 별도 노출 (호출자 가독성 향상).
    """
    from app.models import models as _m

    return (
        db.query(_m.Appointment)
        .filter(
            _m.Appointment.patient_id == patient_id,
            _m.Appointment.status != "canceled",
        )
        .all()
    )


def list_approved_appointments_for_patient_desc(
    db: Any, patient_id: str
) -> list[Any]:
    """환자별 ``approved`` 예약 row (start_at desc — 최신순).

    COMPAT: ``api.py:patient_history`` (line 1538~1542) 의
    ``filter(patient_id == pid, status == "approved").order_by(start_at.desc())``
    정합.
    """
    from app.models import models as _m

    return (
        db.query(_m.Appointment)
        .filter(
            _m.Appointment.patient_id == patient_id,
            _m.Appointment.status == "approved",
        )
        .order_by(_m.Appointment.start_at.desc())
        .all()
    )


def last_appointment_per_patient(db: Any) -> list[tuple[str, Any]]:
    """환자별 *마지막* 예약 시간 (canceled 제외) 매핑.

    COMPAT: ``api.py:last_appointments`` (line 1489~1494) 의
    ``query(patient_id, max(start_at)).filter(status != "canceled").group_by(patient_id)``
    정합. 반환은 ``[(patient_id, max_start_at_or_None), ...]`` — 응답 dict 빌드는
    ``service.build_last_appointments_response`` 가 담당.
    """
    from sqlalchemy import func

    from app.models import models as _m

    rows = (
        db.query(
            _m.Appointment.patient_id,
            func.max(_m.Appointment.start_at).label("last"),
        )
        .filter(_m.Appointment.status != "canceled")
        .group_by(_m.Appointment.patient_id)
        .all()
    )
    return [(r[0], r[1]) for r in rows]


def find_assignment_for_code(
    appointment: Any,
    *,
    treatment_code: str,
) -> Any | None:
    """예약의 ``TreatmentAssignment`` 중 ``treatment_code`` 매칭 row.

    COMPAT: ``api.py:change_assignment`` (line 1778~1779) /
    ``split_appointment_code`` (line 1862~1864 / 1902~1904) 의 ``next((a for a
    in obj.assignments if a.treatment_code == ...), None)`` 정합.

    NOTE: ORM lazy load — 호출자가 ``obj.assignments`` 가 이미 로드된 세션을 보유.
    본 helper 는 *list scan 만* — DB 호출 ⊥.
    """
    if appointment is None:
        return None
    for a in appointment.assignments or []:
        if a.treatment_code == treatment_code:
            return a
    return None


def find_treatment_by_code(db: Any, treatment_code: str) -> Any | None:
    """치료 코드로 ``Treatment`` row 조회 (split / approve 흐름이 default_minutes 사용).

    COMPAT: ``api.py:split_appointment_code`` (line 1881) /
    ``_bump_patient_count`` (line 1938) 의 ``filter_by(code=treatment_code)`` 정합.

    NOTE: 19-6 treatments 모듈에 동등 helper 있을 수 있으나, 예약 흐름 가독성을
    위해 본 repository 에도 노출 — 동일 query 를 두 모듈에서 호출 가능.
    """
    from app.models import models as _m

    return db.query(_m.Treatment).filter_by(code=treatment_code).first()


def get_patient_treatment_count_row(
    db: Any,
    *,
    patient_id: str,
    treatment_id: str,
) -> Any | None:
    """``PatientTreatmentCount`` 단건 조회 (lazy 생성용 사전 검사).

    COMPAT: ``api.py:_bump_patient_count`` (line 1942~1944) 의
    ``filter_by(patient_id=..., treatment_id=...).first()`` 정합.
    """
    from app.models import models as _m

    return (
        db.query(_m.PatientTreatmentCount)
        .filter_by(patient_id=patient_id, treatment_id=treatment_id)
        .first()
    )


__all__ = [
    "get_appointment_by_id",
    "list_appointments_in_range",
    "list_active_appointments_for_patient",
    "list_approved_appointments_for_patient_desc",
    "last_appointment_per_patient",
    "find_assignment_for_code",
    "find_treatment_by_code",
    "get_patient_treatment_count_row",
]
