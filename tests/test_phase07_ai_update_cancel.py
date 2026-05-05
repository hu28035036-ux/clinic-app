"""Phase 7 — update_appointment / cancel_appointment 단위 테스트.

검증 항목 (AI_FEATURE_MASTER_PLAN § 5.2):
- 대상 예약 식별 (환자 + 날짜 + 시간 → 단일 Appointment)
- 변경 전·후 비교 (diff 의 changed_fields)
- 변경 후 시간 충돌 검사 (자기 자신 exclude 정합)
- 변경 후 휴무 / 권한 / 과거 날짜 검사
- 취소: 이미 취소된 예약 차단 / 물리 삭제 금지 (service callable 만 호출)
- DB 직접 수정 0
- 외부 AI API 호출 0
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.ai_appointment_change import (
    build_appointment_diff,
    build_cancel_preview,
    build_update_preview,
    execute_approved_cancel_appointment,
    execute_approved_update_appointment,
    resolve_target_appointment,
    validate_cancel_appointment,
    validate_update_appointment,
)
from app.ai.ai_command_schema import (
    AiCommandStatus,
)
from app.models.models import (
    Appointment,
    Base,
    Employee,
    EmployeeLeave,
    Patient,
    Treatment,
)

# ────────────────────────────── Fixtures ──────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.add(Patient(id="p2", name="김민수", chart_no="33333", birth_date="1990-01-01", phone="010-5555-6666"))
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Employee(id="e2", name="김치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Treatment(id="t1", code="manual_30", name="도수치료 30분", short="도30", count_increment=1))
    sess.add(Treatment(id="t2", code="manual_60", name="도수치료 60분", short="도60", count_increment=1))
    # 시드 예약: 박환자 5월 30일 9:00-9:30 박치료사 manual_30
    sess.add(
        Appointment(
            id="a1",
            patient_id="p1",
            therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            status="reserved",
            treatment_codes='["manual_30"]',
        )
    )
    # 시드 예약 2: 김민수 5월 30일 10:00-10:30 박치료사
    sess.add(
        Appointment(
            id="a2",
            patient_id="p2",
            therapist_id="e1",
            start_at=datetime(2026, 5, 30, 10, 0),
            end_at=datetime(2026, 5, 30, 10, 30),
            status="reserved",
            treatment_codes='["manual_30"]',
        )
    )
    # 이미 취소된 예약
    sess.add(
        Appointment(
            id="a3",
            patient_id="p1",
            therapist_id="e1",
            start_at=datetime(2026, 5, 30, 14, 0),
            end_at=datetime(2026, 5, 30, 14, 30),
            status="canceled",
            treatment_codes='["manual_30"]',
        )
    )
    sess.commit()
    yield sess
    sess.close()


# ────────────────────────────── 1. 대상 예약 식별 ──────────────────────────────


def test_resolve_target_by_patient_date_time(db_session):
    res = resolve_target_appointment(
        db_session,
        patient_id="p1",
        target_date=date(2026, 5, 30),
        start_hour=9,
    )
    assert res.target is not None
    assert res.target.appointment_id == "a1"
    assert res.target.status == "reserved"


def test_resolve_target_excludes_canceled(db_session):
    """status=canceled 예약은 후보에서 제외."""
    res = resolve_target_appointment(
        db_session,
        patient_id="p1",
        target_date=date(2026, 5, 30),
        start_hour=14,
    )
    # a3 가 14시이지만 canceled → 제외 → 다른 시간대도 없으므로 not_found
    assert res.target is None
    assert res.not_found is True


def test_resolve_target_no_time_returns_all(db_session):
    """시간 누락 → 같은 날 환자 예약 모두 candidates (canceled 제외)."""
    res = resolve_target_appointment(
        db_session,
        patient_id="p1",
        target_date=date(2026, 5, 30),
        start_hour=None,
    )
    # a1 (9시) 만 — a3 는 canceled 제외
    assert len(res.candidates) == 1
    assert res.target is not None
    assert res.target.appointment_id == "a1"


def test_resolve_target_not_found_when_patient_missing(db_session):
    res = resolve_target_appointment(
        db_session,
        patient_id=None,
        target_date=date(2026, 5, 30),
        start_hour=9,
    )
    assert res.not_found is True


# ────────────────────────────── 2. diff ──────────────────────────────


def test_diff_time_change_only(db_session):
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    target = res.target
    diff = build_appointment_diff(
        before=target,
        new_start_hour=10,
        new_start_minute=30,
    )
    assert "start_time" in diff.changed_fields
    assert diff.before["start_at"].endswith("09:00:00")
    assert diff.after["start_at"].endswith("10:30:00")


def test_diff_therapist_change(db_session):
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    diff = build_appointment_diff(before=res.target, new_therapist_id="e2")
    assert "therapist_id" in diff.changed_fields
    assert diff.after["therapist_id"] == "e2"


def test_diff_no_change_returns_empty_changed_fields(db_session):
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    diff = build_appointment_diff(before=res.target)  # 모두 None
    assert diff.changed_fields == []


def test_diff_treatment_codes_change(db_session):
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    diff = build_appointment_diff(
        before=res.target, new_treatment_codes=["manual_60"]
    )
    assert "treatment_codes" in diff.changed_fields


# ────────────────────────────── 3. update validator ──────────────────────────────


def test_validate_update_excludes_self(db_session):
    """변경 후 시간이 자기 자신과 같아도 충돌 처리하지 않음 (exclude)."""
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    # 같은 시간 그대로 (no change) — 자기 자신과의 충돌이지만 exclude 라 ok
    val = validate_update_appointment(
        db_session,
        target=res.target,
        new_start_hour=9,
    )
    assert val.can_approve is True


def test_validate_update_blocks_when_other_appt_overlaps(db_session):
    """변경 후 시간에 다른 환자 예약이 있으면 충돌."""
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    # a1 을 10시로 변경 시도 → a2 (10시) 와 충돌
    val = validate_update_appointment(
        db_session,
        target=res.target,
        new_start_hour=10,
    )
    assert val.can_approve is False
    assert any(i.code == "시간_겹침" for i in val.issues)


def test_validate_update_leave_conflict(db_session):
    """변경 후 날짜에 치료사 휴무 → 차단."""
    db_session.add(
        EmployeeLeave(
            id="l1",
            employee_id="e1",
            leave_date="2026-06-01",
            leave_type="full",
        )
    )
    db_session.commit()
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    val = validate_update_appointment(
        db_session,
        target=res.target,
        new_target_date=date(2026, 6, 1),
        new_start_hour=9,
    )
    assert val.can_approve is False
    assert any(i.code == "휴무_충돌" for i in val.issues)


# ────────────────────────────── 4. update executor ──────────────────────────────


def test_execute_update_calls_service(db_session):
    captured = {}

    def fake_update(**kwargs):
        captured.update(kwargs)
        return {"appointment_id": kwargs["appointment_id"], "status": "updated"}

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    result = execute_approved_update_appointment(
        db_session,
        target=res.target,
        new_start_hour=11,
        new_start_minute=0,
        actor_user_id="staff1",
        update_service=fake_update,
    )
    assert result.success is True
    assert result.new_status == AiCommandStatus.EXECUTED.value
    assert captured["appointment_id"] == "a1"
    assert captured["start_hour"] == 11


def test_execute_update_blocks_on_no_change(db_session):
    """변경 사항 없으면 service 호출 안 함."""
    calls = {"count": 0}

    def fake_update(**kwargs):
        calls["count"] += 1
        return {}

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    result = execute_approved_update_appointment(
        db_session,
        target=res.target,
        actor_user_id="staff1",
        update_service=fake_update,
    )
    assert result.success is False
    assert calls["count"] == 0


def test_execute_update_blocks_on_conflict(db_session):
    """변경 후 충돌이면 service 호출 안 함."""
    calls = {"count": 0}

    def fake_update(**kwargs):
        calls["count"] += 1
        return {}

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    result = execute_approved_update_appointment(
        db_session,
        target=res.target,
        new_start_hour=10,  # a2 와 충돌
        update_service=fake_update,
        actor_user_id="staff1",
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.VALIDATION_FAILED.value
    assert calls["count"] == 0


def test_execute_update_handles_service_exception(db_session):
    def failing(**kwargs):
        raise RuntimeError("DB write failed")

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    result = execute_approved_update_appointment(
        db_session,
        target=res.target,
        new_start_hour=11,
        actor_user_id="staff1",
        update_service=failing,
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.FAILED.value
    assert "DB write failed" in (result.error_message or "")


# ────────────────────────────── 5. cancel validator ──────────────────────────────


def test_validate_cancel_normal(db_session):
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    val = validate_cancel_appointment(res.target)
    assert val.can_approve is True


def test_validate_cancel_already_canceled(db_session):
    """status=canceled 예약은 검증 차단 — 다만 resolve 가 canceled 를 제외하므로
    target 이 직접 주입된 경우만 본 케이스 발생."""
    from app.ai.ai_appointment_change import TargetAppointment

    canceled = TargetAppointment(
        appointment_id="a3",
        patient_id="p1",
        therapist_id="e1",
        start_at=datetime(2026, 5, 30, 14, 0),
        end_at=datetime(2026, 5, 30, 14, 30),
        status="canceled",
    )
    val = validate_cancel_appointment(canceled)
    assert val.can_approve is False
    assert any(i.code == "이미_취소됨" for i in val.issues)


def test_validate_cancel_target_none():
    val = validate_cancel_appointment(None)
    assert val.can_approve is False
    assert any(i.code == "대상_미확정" for i in val.issues)


# ────────────────────────────── 6. cancel executor ──────────────────────────────


def test_execute_cancel_calls_service(db_session):
    captured = {}

    def fake_cancel(**kwargs):
        captured.update(kwargs)
        return {"appointment_id": kwargs["appointment_id"], "status": "canceled"}

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    result = execute_approved_cancel_appointment(
        target=res.target,
        reason="환자 요청",
        actor_user_id="staff1",
        cancel_service=fake_cancel,
    )
    assert result.success is True
    assert result.new_status == AiCommandStatus.EXECUTED.value
    assert captured["appointment_id"] == "a1"
    assert captured["reason"] == "환자 요청"


def test_execute_cancel_does_not_physically_delete(db_session):
    """executor 자체가 DELETE 호출 안 함 (Appointment row 그대로 유지)."""
    before = db_session.query(Appointment).count()

    def fake_cancel(**kwargs):
        # service 가 직접 status 변경 (시뮬레이션)
        return {"appointment_id": kwargs["appointment_id"]}

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    execute_approved_cancel_appointment(
        target=res.target,
        reason=None,
        actor_user_id="u1",
        cancel_service=fake_cancel,
    )
    after = db_session.query(Appointment).count()
    assert before == after  # 물리 삭제 0


def test_execute_cancel_already_canceled_blocks(db_session):
    from app.ai.ai_appointment_change import TargetAppointment

    canceled_target = TargetAppointment(
        appointment_id="a3",
        patient_id="p1",
        therapist_id="e1",
        start_at=datetime(2026, 5, 30, 14, 0),
        end_at=datetime(2026, 5, 30, 14, 30),
        status="canceled",
    )

    calls = {"count": 0}

    def fake_cancel(**kwargs):
        calls["count"] += 1
        return {}

    result = execute_approved_cancel_appointment(
        target=canceled_target,
        reason=None,
        actor_user_id="u1",
        cancel_service=fake_cancel,
    )
    assert result.success is False
    assert calls["count"] == 0


def test_execute_cancel_handles_service_exception(db_session):
    def failing(**kwargs):
        raise RuntimeError("svc fail")

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    result = execute_approved_cancel_appointment(
        target=res.target,
        reason=None,
        actor_user_id="u1",
        cancel_service=failing,
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.FAILED.value


# ────────────────────────────── 7. preview ──────────────────────────────


def test_build_update_preview_normal(db_session):
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    diff = build_appointment_diff(before=res.target, new_start_hour=11)
    val = validate_update_appointment(
        db_session, target=res.target, new_start_hour=11
    )
    panel = build_update_preview(diff=diff, validation=val)
    assert panel["title"] == "예약 변경 후보"
    assert "예약 완료" not in panel["title"]
    assert panel["approval_disabled"] is False


def test_build_cancel_preview_normal(db_session):
    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    val = validate_cancel_appointment(res.target)
    panel = build_cancel_preview(target=res.target, validation=val, reason="환자 요청")
    assert panel["title"] == "예약 취소 후보"
    assert panel["reason"] == "환자 요청"
    assert panel["approval_disabled"] is False


# ────────────────────────────── 8. 안전 ──────────────────────────────


def test_resolver_does_not_modify_db(db_session):
    before_a = db_session.query(Appointment).count()
    resolve_target_appointment(
        db_session,
        patient_id="p1",
        target_date=date(2026, 5, 30),
        start_hour=9,
    )
    assert db_session.query(Appointment).count() == before_a


def test_executor_does_not_modify_db_directly(db_session):
    """executor 호출 후 DB row 수 동일 (service 가 mock 이라 실제 변경 0)."""
    before = db_session.query(Appointment).count()

    def fake_update(**kwargs):
        return {"appointment_id": kwargs["appointment_id"]}

    res = resolve_target_appointment(
        db_session, patient_id="p1", target_date=date(2026, 5, 30), start_hour=9
    )
    execute_approved_update_appointment(
        db_session,
        target=res.target,
        new_start_hour=11,
        actor_user_id="u1",
        update_service=fake_update,
    )
    after = db_session.query(Appointment).count()
    assert before == after
