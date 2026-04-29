"""테스트 전용 시드 데이터 (멱등).

init_db() 가 자동으로 시드한 5개 치료항목(injection/cartilage/eswt/manual30/manual60)
위에 다음을 추가한다.

- 치료사 3명: 김테스트치료사 / 이테스트치료사 / 박테스트치료사
- 환자 3명: 홍길동테스트 / 김영희테스트 / 박철수테스트
- 휴무 3건: 종일 / 오전반차 / 오후반차 (FIXED_LEAVE_DATE 에 일괄)
- 추가 치료항목: manual90 (count_increment=1) — manual90 별도 집계 테스트용

이름·코드 기준 SELECT 후 없을 때만 INSERT — 반복 실행해도 중복되지 않는다.
모든 테스트 직원/환자 이름에 "테스트" 가 들어 있어 운영 DB 에 실수로 들어가도 즉시 식별 가능.
"""
from __future__ import annotations

# 테스트 휴무 고정 날짜 (충분히 미래로) — 실제 운영 캘린더와 겹칠 일 없음
FIXED_LEAVE_DATE = "2099-06-15"

# 테스트 직원 / 환자 이름 (운영 DB 침입 시 즉시 식별 가능)
THERAPIST_NAMES = ("김테스트치료사", "이테스트치료사", "박테스트치료사")
PATIENT_NAMES = ("홍길동테스트", "김영희테스트", "박철수테스트")

# 휴무 매핑: 치료사 이름 → leave_type
LEAVE_TYPE_BY_THERAPIST = {
    "김테스트치료사": "full",
    "이테스트치료사": "morning",
    "박테스트치료사": "afternoon",
}


def seed_test_data():
    """테스트 DB 에 멱등 시드. 실패 시 RuntimeError.

    호출 시점: conftest.py 의 session-scoped autouse fixture.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        _seed_treatments(db)
        therapist_ids = _seed_therapists(db)
        _seed_patients(db)
        _seed_leaves(db, therapist_ids)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _seed_treatments(db):
    """manual90 추가 (count_increment=1, role=therapist)."""
    from app.models import models

    if not db.query(models.Treatment).filter(models.Treatment.code == "manual90").first():
        max_sort = db.query(models.Treatment).count()
        db.add(models.Treatment(
            code="manual90",
            name="도수치료90분",
            short="도수18",
            default_minutes=90,
            role="therapist",
            count_increment=1,
            show_in_patient=True,
            active=True,
            sort_order=max_sort + 1,
            price=0,
        ))
        db.flush()


def _seed_therapists(db) -> dict:
    """3명 치료사 멱등 추가. 반환: {name: id}"""
    from app.models import models

    out = {}
    for name in THERAPIST_NAMES:
        existing = db.query(models.Employee).filter(
            models.Employee.name == name,
            models.Employee.role == "therapist",
        ).first()
        if existing:
            out[name] = existing.id
            continue
        max_sort = db.query(models.Employee).filter(
            models.Employee.role == "therapist"
        ).count()
        e = models.Employee(
            name=name,
            role="therapist",
            color="#9CA3AF",
            active=True,
            can_eswt=True,
            can_manual=True,
            sort_order=max_sort + 1,
        )
        db.add(e)
        db.flush()
        out[name] = e.id
    return out


def _seed_patients(db):
    """3명 환자 멱등 추가."""
    from app.models import models

    for name in PATIENT_NAMES:
        existing = db.query(models.Patient).filter(models.Patient.name == name).first()
        if existing:
            continue
        db.add(models.Patient(name=name))
        db.flush()


def _seed_leaves(db, therapist_ids: dict):
    """휴무 3건 멱등 추가."""
    from app.models import models

    for therapist_name, leave_type in LEAVE_TYPE_BY_THERAPIST.items():
        emp_id = therapist_ids[therapist_name]
        existing = db.query(models.EmployeeLeave).filter(
            models.EmployeeLeave.employee_id == emp_id,
            models.EmployeeLeave.leave_date == FIXED_LEAVE_DATE,
        ).first()
        if existing:
            continue
        db.add(models.EmployeeLeave(
            employee_id=emp_id,
            leave_date=FIXED_LEAVE_DATE,
            leave_type=leave_type,
            memo=f"하네스 시드 ({leave_type})",
        ))
        db.flush()


def get_test_therapist_id(name: str) -> str:
    """이름으로 시드된 치료사 ID 조회."""
    from app.database import SessionLocal
    from app.models import models

    db = SessionLocal()
    try:
        e = db.query(models.Employee).filter(
            models.Employee.name == name,
            models.Employee.role == "therapist",
        ).first()
        if not e:
            raise RuntimeError(f"시드된 치료사 '{name}' 를 찾을 수 없습니다.")
        return e.id
    finally:
        db.close()


def get_test_patient_id(name: str) -> str:
    """이름으로 시드된 환자 ID 조회."""
    from app.database import SessionLocal
    from app.models import models

    db = SessionLocal()
    try:
        p = db.query(models.Patient).filter(models.Patient.name == name).first()
        if not p:
            raise RuntimeError(f"시드된 환자 '{name}' 를 찾을 수 없습니다.")
        return p.id
    finally:
        db.close()
