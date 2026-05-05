"""Phase 11 — data_quality_check / ops_assistant 단위 테스트.

검증 (AI_FEATURE_MASTER_PLAN § 5.5):
- 모두 read-only / 추천만 — 자동 수정 ⊥
- 차트번호 / 연락처 누락 / 이름+생년월일 / 연락처 중복 검사
- 빈 시간대 추천 (휴무 / canceled 제외)
- 치료사별 부하 분석
- 자동 예약 / 자동 병합 / 자동 휴무 등록 함수 미노출
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.ai_ops import (
    analyze_therapist_load,
    build_data_quality_preview,
    build_empty_slots_preview,
    build_therapist_load_preview,
    check_chart_no_duplicates,
    check_name_birth_duplicates,
    check_phone_duplicates,
    check_phone_missing,
    find_empty_slots,
    run_data_quality_check,
)
from app.models.models import (
    Appointment,
    Base,
    Employee,
    EmployeeLeave,
    Patient,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    # 환자 — 차트번호 중복 1쌍, 연락처 누락 1명, 이름+생년월일 중복 1쌍, 연락처 중복 1쌍
    sess.add(Patient(id="p1", name="박환자", chart_no="11111", birth_date="1980-01-01", phone="010-1111-1111"))
    sess.add(Patient(id="p2", name="박환자", chart_no="11111", birth_date="1985-05-05", phone="010-2222-2222"))  # 차트 중복
    sess.add(Patient(id="p3", name="김민수", chart_no="22222", birth_date="1990-10-10", phone=""))  # 연락처 누락
    sess.add(Patient(id="p4", name="이지은", chart_no="33333", birth_date="1995-03-03", phone="010-3333-3333"))
    sess.add(Patient(id="p5", name="이지은", chart_no="44444", birth_date="1995-03-03", phone="010-4444-4444"))  # 이름+생년 중복
    sess.add(Patient(id="p6", name="홍길동", chart_no="55555", birth_date="2000-01-01", phone="010-9999-9999"))
    sess.add(Patient(id="p7", name="다른사람", chart_no="66666", birth_date="2000-02-02", phone="010-9999-9999"))  # 연락처 중복
    # 치료사
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Employee(id="e2", name="김치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Employee(id="e3", name="비활성", role="therapist", color="#9CA3AF", active=False))
    # 예약 — 5/30 박치료사 9시 / 14시
    sess.add(Appointment(id="a1", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 9, 0), end_at=datetime(2026, 5, 30, 9, 30),
        status="reserved", treatment_codes='["manual_30"]'))
    sess.add(Appointment(id="a2", patient_id="p2", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 14, 0), end_at=datetime(2026, 5, 30, 14, 30),
        status="reserved", treatment_codes='["manual_30"]'))
    # canceled (충돌 후보 ⊥)
    sess.add(Appointment(id="a3", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 11, 0), end_at=datetime(2026, 5, 30, 11, 30),
        status="canceled", treatment_codes='["manual_30"]'))
    sess.commit()
    yield sess
    sess.close()


# ────────────────────────────── 1. data_quality_check ──────────────────────────────


def test_check_chart_no_duplicates(db_session):
    issue = check_chart_no_duplicates(db_session)
    assert issue is not None
    assert issue.kind == "chart_no_duplicate"
    # p1 / p2 (차트 11111)
    assert len(issue.affected_patients) == 2


def test_check_phone_missing(db_session):
    issue = check_phone_missing(db_session)
    assert issue is not None
    assert issue.kind == "phone_missing"
    assert any(p["id"] == "p3" for p in issue.affected_patients)


def test_check_name_birth_duplicates(db_session):
    issue = check_name_birth_duplicates(db_session)
    assert issue is not None
    assert issue.kind == "name_birth_duplicate"
    # p4 / p5 (이지은 1995-03-03)
    assert len(issue.affected_patients) == 2


def test_check_phone_duplicates(db_session):
    issue = check_phone_duplicates(db_session)
    assert issue is not None
    assert issue.kind == "phone_duplicate"
    # p6 / p7 (010-9999-9999)
    assert len(issue.affected_patients) == 2


def test_check_returns_none_when_no_issue(db_session):
    """모든 환자 삭제 후 → None."""
    db_session.query(Patient).delete()
    db_session.commit()
    assert check_chart_no_duplicates(db_session) is None
    assert check_phone_missing(db_session) is None
    assert check_name_birth_duplicates(db_session) is None
    assert check_phone_duplicates(db_session) is None


def test_run_data_quality_check_all(db_session):
    report = run_data_quality_check(db_session)
    # 4종 모두 발견
    assert len(report.issues) == 4
    assert report.total_count > 0


def test_run_data_quality_check_selective(db_session):
    report = run_data_quality_check(db_session, check_kinds=("chart_no",))
    assert len(report.issues) == 1
    assert report.issues[0].kind == "chart_no_duplicate"


# ────────────────────────────── 2. find_empty_slots ──────────────────────────────


def test_find_empty_slots_normal(db_session):
    """5/30 박치료사 9-12시. 9시 / 14시 예약 있음. 빈 슬롯: 10, 11."""
    slots = find_empty_slots(
        db_session,
        target_date=date(2026, 5, 30),
        therapist_id="e1",
        hour_range=(9, 13),
    )
    hours = sorted(s.hour for s in slots)
    # 9 (예약), 10 (빈), 11 (canceled — 빈), 12 (빈)
    assert hours == [10, 11, 12]


def test_find_empty_slots_full_leave(db_session):
    db_session.add(EmployeeLeave(id="l1", employee_id="e1", leave_date="2026-05-30", leave_type="full"))
    db_session.commit()
    slots = find_empty_slots(
        db_session,
        target_date=date(2026, 5, 30),
        therapist_id="e1",
    )
    assert slots == []


def test_find_empty_slots_am_leave(db_session):
    db_session.add(EmployeeLeave(id="l1", employee_id="e1", leave_date="2026-05-30", leave_type="am"))
    db_session.commit()
    slots = find_empty_slots(
        db_session,
        target_date=date(2026, 5, 30),
        therapist_id="e1",
        hour_range=(9, 18),
    )
    # 오전 (< 13) 차단. 14시 예약 → 14 제외. 빈: 13, 15, 16, 17
    hours = sorted(s.hour for s in slots)
    assert 9 not in hours
    assert 12 not in hours
    assert 13 in hours
    assert 14 not in hours


def test_find_empty_slots_inactive_therapist(db_session):
    slots = find_empty_slots(
        db_session, target_date=date(2026, 5, 30), therapist_id="e3"
    )
    assert slots == []


def test_find_empty_slots_unknown_therapist(db_session):
    slots = find_empty_slots(
        db_session, target_date=date(2026, 5, 30), therapist_id="ghost"
    )
    assert slots == []


# ────────────────────────────── 3. analyze_therapist_load ──────────────────────────────


def test_analyze_therapist_load_sorted(db_session):
    loads = analyze_therapist_load(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 5, 30)
    )
    # 박치료사 2건 (a1, a2) — canceled (a3) 제외
    assert any(x.therapist_id == "e1" and x.appointment_count == 2 for x in loads)
    # appointment_count 순 정렬
    counts = [x.appointment_count for x in loads]
    assert counts == sorted(counts, reverse=True)


def test_analyze_therapist_load_empty_period(db_session):
    loads = analyze_therapist_load(
        db_session, period_start=date(2026, 6, 30), period_end=date(2026, 6, 30)
    )
    assert loads == []


def test_analyze_therapist_load_invalid_range(db_session):
    with pytest.raises(ValueError):
        analyze_therapist_load(
            db_session,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 5, 1),
        )


# ────────────────────────────── 4. preview ──────────────────────────────


def test_data_quality_preview_marks_auto_modify_disabled(db_session):
    report = run_data_quality_check(db_session)
    preview = build_data_quality_preview(report)
    assert preview["auto_modify_disabled"] is True
    assert preview["read_only"] is True
    assert "자동 수정" not in preview["actions"]


def test_empty_slots_preview_marks_auto_create_disabled(db_session):
    slots = find_empty_slots(
        db_session, target_date=date(2026, 5, 30), therapist_id="e1"
    )
    preview = build_empty_slots_preview(slots, target_date=date(2026, 5, 30), therapist_id="e1")
    assert preview["auto_create_disabled"] is True
    assert preview["read_only"] is True


def test_therapist_load_preview_marks_read_only(db_session):
    loads = analyze_therapist_load(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 5, 30)
    )
    preview = build_therapist_load_preview(
        loads, period_start=date(2026, 5, 30), period_end=date(2026, 5, 30)
    )
    assert preview["read_only"] is True
    assert preview["auto_balance_disabled"] is True


# ────────────────────────────── 5. 안전 — 자동 수정 함수 미노출 ──────────────────────────────


def test_module_does_not_expose_auto_modify_functions():
    """본 모듈은 자동 수정 / 자동 예약 / 자동 휴무 함수를 노출하지 않음."""
    import app.ai.ai_ops as mod

    forbidden = (
        "merge_patients",
        "delete_patient",
        "auto_create_appointment",
        "auto_register_leave",
        "auto_fix",
        "auto_modify",
    )
    public = [n for n in dir(mod) if not n.startswith("_")]
    for name in forbidden:
        assert name not in public, f"{name} 가 public API 에 있음 — 자동 수정 ⊥ 위반"


# ────────────────────────────── 6. 안전 — DB 직접 수정 0 ──────────────────────────────


def test_ops_does_not_modify_db(db_session):
    before_p = db_session.query(Patient).count()
    before_a = db_session.query(Appointment).count()
    before_l = db_session.query(EmployeeLeave).count()

    run_data_quality_check(db_session)
    find_empty_slots(db_session, target_date=date(2026, 5, 30), therapist_id="e1")
    analyze_therapist_load(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 5, 30)
    )

    assert db_session.query(Patient).count() == before_p
    assert db_session.query(Appointment).count() == before_a
    assert db_session.query(EmployeeLeave).count() == before_l
