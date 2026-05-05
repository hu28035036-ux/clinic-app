"""Phase 8 — create_leave 단위 테스트.

검증 (AI_FEATURE_MASTER_PLAN § 5.3):
- 휴무 유형 추출 (종일/연차 → full, 오전반차 → am, 오후반차 → pm)
- 비활성 치료사 차단
- 같은 날짜 기존 휴무 중복 차단
- 과거 날짜 차단
- 충돌 예약 안내 (warning, 차단 ⊥)
- service callable 호출 / DB 직접 수정 0
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.ai_command_schema import AiCommandStatus
from app.ai.ai_leave import (
    LEAVE_TYPE_AM,
    LEAVE_TYPE_FULL,
    LEAVE_TYPE_PM,
    build_leave_preview,
    execute_approved_leave,
    parse_leave_type_from_text,
    validate_leave_candidate,
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
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Employee(id="e2", name="비활성치료사", role="therapist", color="#9CA3AF", active=False))
    sess.commit()
    yield sess
    sess.close()


# ────────────────────────────── 1. 휴무 유형 추출 ──────────────────────────────


@pytest.mark.parametrize("text,expected", [
    ("박치료사 5월 5일 종일 휴무", LEAVE_TYPE_FULL),
    ("박치료사 연차", LEAVE_TYPE_FULL),
    ("박치료사 5월10일 오프", LEAVE_TYPE_FULL),
    ("박치료사 다음주 월요일 오전반차", LEAVE_TYPE_AM),
    ("박치료사 30일 오후반차", LEAVE_TYPE_PM),
    ("박치료사 5월 5일", None),
])
def test_parse_leave_type(text, expected):
    assert parse_leave_type_from_text(text) == expected


# ────────────────────────────── 2. 검증 — 필수값 ──────────────────────────────


def test_validate_leave_missing_therapist(db_session):
    res = validate_leave_candidate(
        db_session,
        therapist_id=None,
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    assert res.can_approve is False
    assert any(i.code == "치료사_미선택" for i in res.issues)


def test_validate_leave_missing_date(db_session):
    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=None,
        leave_type=LEAVE_TYPE_FULL,
    )
    assert res.can_approve is False
    assert any(i.code == "날짜_미확정" for i in res.issues)


def test_validate_leave_invalid_type(db_session):
    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type="custom-xyz",
    )
    assert res.can_approve is False
    assert any(i.code == "휴무유형_모호" for i in res.issues)


def test_validate_leave_inactive_therapist(db_session):
    res = validate_leave_candidate(
        db_session,
        therapist_id="e2",  # 비활성
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    assert res.can_approve is False
    assert any(i.code == "치료사_비활성" for i in res.issues)


def test_validate_leave_unknown_therapist(db_session):
    res = validate_leave_candidate(
        db_session,
        therapist_id="ghost-id",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    assert res.can_approve is False
    assert any(i.code == "치료사_비활성" for i in res.issues)


# ────────────────────────────── 3. 검증 — 중복 휴무 ──────────────────────────────


def test_validate_leave_existing_duplicate(db_session):
    db_session.add(
        EmployeeLeave(id="l1", employee_id="e1", leave_date="2026-05-30", leave_type=LEAVE_TYPE_FULL)
    )
    db_session.commit()

    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_AM,
    )
    assert res.can_approve is False
    assert any(i.code == "휴무_중복" for i in res.issues)
    assert res.duplicate_existing_leave is not None


def test_validate_leave_no_duplicate_different_date(db_session):
    db_session.add(
        EmployeeLeave(id="l1", employee_id="e1", leave_date="2026-05-30", leave_type=LEAVE_TYPE_FULL)
    )
    db_session.commit()

    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 31),
        leave_type=LEAVE_TYPE_FULL,
    )
    assert res.can_approve is True


# ────────────────────────────── 4. 검증 — 충돌 예약 (안내) ──────────────────────────────


def test_validate_leave_conflict_appointments_full_day(db_session):
    """종일 휴무 + 같은 날 예약 1건 → warning 으로 안내, 차단 ⊥."""
    db_session.add(
        Appointment(
            id="a1", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            status="reserved", treatment_codes='["manual_30"]',
        )
    )
    db_session.commit()

    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    # warning — 차단 ⊥
    assert res.can_approve is True
    assert len(res.conflicting_appointments) == 1
    assert any(i.severity == "warning" and i.code == "예약_충돌" for i in res.issues)


def test_validate_leave_conflict_am_only(db_session):
    """오전반차 + 오전 예약 → 충돌. 오후 예약 → 충돌 ⊥."""
    db_session.add(
        Appointment(
            id="a1", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            status="reserved", treatment_codes='["manual_30"]',
        )
    )
    db_session.add(
        Appointment(
            id="a2", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 14, 0),
            end_at=datetime(2026, 5, 30, 14, 30),
            status="reserved", treatment_codes='["manual_30"]',
        )
    )
    db_session.commit()

    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_AM,
    )
    assert len(res.conflicting_appointments) == 1
    assert res.conflicting_appointments[0].appointment_id == "a1"


def test_validate_leave_conflict_pm_only(db_session):
    db_session.add(
        Appointment(
            id="a1", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            status="reserved", treatment_codes='["manual_30"]',
        )
    )
    db_session.add(
        Appointment(
            id="a2", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 14, 0),
            end_at=datetime(2026, 5, 30, 14, 30),
            status="reserved", treatment_codes='["manual_30"]',
        )
    )
    db_session.commit()

    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_PM,
    )
    assert len(res.conflicting_appointments) == 1
    assert res.conflicting_appointments[0].appointment_id == "a2"


def test_validate_leave_conflict_excludes_canceled(db_session):
    """status=canceled 예약은 충돌 후보에서 제외."""
    db_session.add(
        Appointment(
            id="a1", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            status="canceled", treatment_codes='["manual_30"]',
        )
    )
    db_session.commit()

    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    assert len(res.conflicting_appointments) == 0


def test_validate_leave_strict_mode_blocks_conflict(db_session):
    """allow_existing_appointment_conflict=False → 충돌 시 error 차단."""
    db_session.add(
        Appointment(
            id="a1", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            status="reserved", treatment_codes='["manual_30"]',
        )
    )
    db_session.commit()

    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
        allow_existing_appointment_conflict=False,
    )
    assert res.can_approve is False


# ────────────────────────────── 5. 검증 — 과거 날짜 ──────────────────────────────


def test_validate_leave_past_date(db_session):
    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2020, 1, 1),
        leave_type=LEAVE_TYPE_FULL,
        is_past_date=True,
    )
    assert res.can_approve is False
    assert any(i.code == "과거_날짜" for i in res.issues)


# ────────────────────────────── 6. 정상 검증 ──────────────────────────────


def test_validate_leave_normal_no_conflict(db_session):
    res = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    assert res.can_approve is True
    assert all(v for v in res.checks.values())


# ────────────────────────────── 7. 실행 ──────────────────────────────


def test_execute_leave_calls_service(db_session):
    captured = {}

    def fake_leave(**kwargs):
        captured.update(kwargs)
        return {"leave_id": "l-new", "leave_date": "2026-05-30"}

    result = execute_approved_leave(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
        memo="컨퍼런스 참석",
        actor_user_id="staff1",
        leave_service=fake_leave,
    )
    assert result.success is True
    assert result.new_status == AiCommandStatus.EXECUTED.value
    assert captured["therapist_id"] == "e1"
    assert captured["leave_date"] == date(2026, 5, 30)
    assert captured["leave_type"] == LEAVE_TYPE_FULL
    assert captured["memo"] == "컨퍼런스 참석"


def test_execute_leave_blocks_when_inactive(db_session):
    calls = {"count": 0}

    def fake_leave(**kwargs):
        calls["count"] += 1
        return {}

    result = execute_approved_leave(
        db_session,
        therapist_id="e2",  # 비활성
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
        memo=None,
        actor_user_id="u1",
        leave_service=fake_leave,
    )
    assert result.success is False
    assert calls["count"] == 0


def test_execute_leave_blocks_when_duplicate(db_session):
    db_session.add(
        EmployeeLeave(id="l1", employee_id="e1", leave_date="2026-05-30", leave_type=LEAVE_TYPE_FULL)
    )
    db_session.commit()

    calls = {"count": 0}

    def fake_leave(**kwargs):
        calls["count"] += 1
        return {}

    result = execute_approved_leave(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_AM,
        memo=None,
        actor_user_id="u1",
        leave_service=fake_leave,
    )
    assert result.success is False
    assert calls["count"] == 0


def test_execute_leave_handles_service_exception(db_session):
    def failing(**kwargs):
        raise RuntimeError("DB write failed")

    result = execute_approved_leave(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
        memo=None,
        actor_user_id="u1",
        leave_service=failing,
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.FAILED.value
    assert "DB write failed" in (result.error_message or "")


# ────────────────────────────── 8. preview ──────────────────────────────


def test_build_leave_preview_normal(db_session):
    val = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    panel = build_leave_preview(
        therapist_id="e1",
        therapist_name="박치료사",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
        validation=val,
    )
    assert panel["title"] == "휴무 등록 후보"
    assert panel["fields"]["leave_type_display"] == "종일 휴무"
    assert panel["approval_disabled"] is False
    assert panel["conflicting_appointments"] == []


def test_build_leave_preview_with_conflicts(db_session):
    db_session.add(
        Appointment(
            id="a1", patient_id="p1", therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            status="reserved", treatment_codes='["manual_30"]',
        )
    )
    db_session.commit()

    val = validate_leave_candidate(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
    )
    panel = build_leave_preview(
        therapist_id="e1",
        therapist_name="박치료사",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
        validation=val,
    )
    assert len(panel["conflicting_appointments"]) == 1
    assert panel["conflicting_appointments"][0]["appointment_id"] == "a1"


# ────────────────────────────── 9. 안전 ──────────────────────────────


def test_executor_does_not_modify_db_directly(db_session):
    before = db_session.query(EmployeeLeave).count()

    def fake(**kwargs):
        return {"leave_id": "x"}

    execute_approved_leave(
        db_session,
        therapist_id="e1",
        leave_date=date(2026, 5, 30),
        leave_type=LEAVE_TYPE_FULL,
        memo=None,
        actor_user_id="u1",
        leave_service=fake,
    )
    after = db_session.query(EmployeeLeave).count()
    assert before == after  # service mock 이라 INSERT 0
