"""modules.patients.repository — 환자 row read-only 조회 helper (19-7 신규).

본 모듈은 ``Patient`` / ``PatientTreatmentCount`` 테이블의 *조회 전용* 함수만
제공한다. 실제 변경 (create / update / delete) 은 라우터 책임 (19-9 시점 service 채택).

19-7 본 세션 범위:
  - 단건 / 검색 / counts 조회 helper.
  - DB 세션은 호출자 주입 — 운영 DB 직접 open ⊥, lazy import.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:list_patients`` (line 1280) / ``search_patients`` (line 1301) /
#         ``get_patient`` (line 1348) / ``_check_patient_duplicate`` (line 1408) 의
#         query 패턴 정합.

# SAFETY: 운영 DB 직접 접근 ⊥ — caller dependency 의 격리 세션만 사용. PII 응답
#         dict 빌드는 ``service`` 가 담당 — 본 모듈은 ORM row 만 반환.
"""
from __future__ import annotations

from typing import Any


def list_all_patients(db: Any) -> list:
    """모든 환자 조회 (이름순).

    COMPAT: ``api.py:list_patients`` (line 1289) ``order_by(Patient.name)`` 정합.
    """
    from app.models import models as _m

    return db.query(_m.Patient).order_by(_m.Patient.name).all()


def get_patient_by_id(db: Any, patient_id: str) -> Any | None:
    """ID 로 단건 환자 조회.

    COMPAT: ``api.py:get_patient`` (line 1351) ``db.get(Patient, pid)`` 정합.
    """
    from app.models import models as _m

    return db.get(_m.Patient, patient_id)


def find_patient_by_chart_no(db: Any, chart_no: str) -> Any | None:
    """차트번호로 환자 조회 — 중복 검사용.

    COMPAT: ``api.py:_check_patient_duplicate`` (line 1419) 의 ``filter(chart_no==cn)``
    정합. 빈 chart_no 는 caller 가 사전 필터.
    """
    from app.models import models as _m

    return (
        db.query(_m.Patient.id)
        .filter(_m.Patient.chart_no == chart_no)
        .first()
    )


def find_patient_by_name_birth(
    db: Any,
    *,
    name: str,
    birth_date: str,
) -> Any | None:
    """이름+생년월일로 환자 조회 — 중복 검사용.

    COMPAT: ``api.py:_check_patient_duplicate`` (line 1423~1426) 정합.
    """
    from app.models import models as _m

    return (
        db.query(_m.Patient.id)
        .filter(
            _m.Patient.name == name,
            _m.Patient.birth_date == birth_date,
        )
        .first()
    )


def list_patient_counts(db: Any, patient_id: str) -> list:
    """환자별 ``PatientTreatmentCount`` row 조회.

    COMPAT: ``api.py:_patient_counts_dict`` (line 1215) ``filter_by(patient_id=p.id)``
    정합.
    """
    from app.models import models as _m

    return (
        db.query(_m.PatientTreatmentCount)
        .filter_by(patient_id=patient_id)
        .all()
    )


def list_patient_appointments_active(db: Any, patient_id: str) -> list:
    """``status != "canceled"`` 인 환자 예약 row.

    COMPAT: ``api.py:patient_manual_history_summary`` (line 1504~1507) 정합.
    신환 체크 / 도수치료 이력 산정용.
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


__all__ = [
    "list_all_patients",
    "get_patient_by_id",
    "find_patient_by_chart_no",
    "find_patient_by_name_birth",
    "list_patient_counts",
    "list_patient_appointments_active",
]
