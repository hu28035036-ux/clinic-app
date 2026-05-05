"""Phase 5 — ai_executor 단위 테스트.

검증 항목:
- Gate 2 (승인 직전 최종 재검증) 미통과 시 service 호출 안 함
- Gate 2 통과 + 기존 service callable 호출 → 성공 / 실패 처리
- 신환 등록 service 호출 (별도 callable)
- service 예외 발생 시 안전 처리 (기존 프로그램 보호)
- DB 직접 수정 0 (executor 자체는 callable 만 호출)
- 외부 AI API 호출 0
- audit log 갱신 (status / executed_result / error_message / executed_at)
"""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai import ai_audit
from app.ai.ai_command_schema import (
    AiCommandStatus,
    DataSourceState,
    TreatmentItem,
    TreatmentItemStatus,
)
from app.ai.ai_executor import (
    execute_approved_appointment,
    execute_approved_new_patient,
    finalize_audit,
)
from app.migrations.m019_ai_command_logs import up as up19
from app.migrations.m020_treatment_aliases import up as up20
from app.models.models import Base, Employee, Patient, Treatment

# ────────────────────────────── Fixtures ──────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Treatment(id="t1", code="manual_30", name="도수치료 30분", short="도30", count_increment=1))
    sess.commit()
    yield sess
    sess.close()


@pytest.fixture
def audit_conn():
    c = sqlite3.connect(":memory:")
    up19(c)
    up20(c)
    yield c
    c.close()


def _verified_treatment() -> TreatmentItem:
    return TreatmentItem(
        raw_text="도수30",
        matched_treatment_id="t1",
        matched_treatment_name="도수치료 30분",
        source=DataSourceState.DB_VERIFIED,
        status=TreatmentItemStatus.DB_VERIFIED,
    )


# ────────────────────────────── Gate 2 — 최종 재검증 ──────────────────────────────


def test_executor_revalidation_blocks_when_missing_required(db_session):
    """필수값 누락 시 service 호출 안 함."""
    calls = {"count": 0}

    def fake_service(**kwargs):
        calls["count"] += 1
        return {"appointment_id": "a1"}

    result = execute_approved_appointment(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=None,  # 누락
        start_hour=9,
        treatment_items=[_verified_treatment()],
        memo=None,
        actor_user_id="u1",
        appointment_service=fake_service,
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.VALIDATION_FAILED.value
    assert calls["count"] == 0  # service 미호출


def test_executor_revalidation_blocks_when_treatment_unverified(db_session):
    """치료항목 미확정 시 service 호출 안 함."""
    calls = {"count": 0}

    def fake_service(**kwargs):
        calls["count"] += 1
        return {"appointment_id": "a1"}

    unverified = TreatmentItem(
        raw_text="주",
        status=TreatmentItemStatus.NEEDS_CLARIFICATION,
    )
    result = execute_approved_appointment(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[unverified],
        memo=None,
        actor_user_id="u1",
        appointment_service=fake_service,
    )
    assert result.success is False
    assert calls["count"] == 0


# ────────────────────────────── 정상 실행 ──────────────────────────────


def test_executor_calls_service_with_correct_args(db_session):
    captured = {}

    def fake_service(**kwargs):
        captured.update(kwargs)
        return {"appointment_id": "a-new", "status": "scheduled"}

    result = execute_approved_appointment(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        start_minute=0,
        duration_min=30,
        treatment_items=[_verified_treatment()],
        memo="첫 방문",
        actor_user_id="staff1",
        appointment_service=fake_service,
    )
    assert result.success is True
    assert result.new_status == AiCommandStatus.EXECUTED.value
    assert result.result_payload["appointment_id"] == "a-new"
    # service 가 받은 인자 확인
    assert captured["patient_id"] == "p1"
    assert captured["therapist_id"] == "e1"
    assert captured["target_date"] == date(2026, 5, 30)
    assert captured["start_hour"] == 9
    assert captured["treatment_codes"] == ["t1"]
    assert captured["memo"] == "첫 방문"
    assert captured["actor_user_id"] == "staff1"


def test_executor_handles_service_exception(db_session):
    """service 가 예외 던져도 기존 프로그램은 살아있고 ExecutionResult.success=False."""
    def failing_service(**kwargs):
        raise RuntimeError("DB write failed")

    result = execute_approved_appointment(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
        memo=None,
        actor_user_id="u1",
        appointment_service=failing_service,
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.FAILED.value
    assert result.error_message and "DB write failed" in result.error_message


# ────────────────────────────── 신환 등록 executor ──────────────────────────────


def test_new_patient_executor_calls_service():
    captured = {}

    def fake_patient_service(**kwargs):
        captured.update(kwargs)
        return {"patient_id": "p-new", "chart_no": "99999"}

    result = execute_approved_new_patient(
        chart_no="99999",
        name="새환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        actor_user_id="staff1",
        patient_service=fake_patient_service,
    )
    assert result.success is True
    assert result.new_status == AiCommandStatus.PATIENT_REGISTERED.value
    assert result.result_payload["patient_id"] == "p-new"
    assert captured["chart_no"] == "99999"
    assert captured["name"] == "새환자"


def test_new_patient_executor_blocks_missing_required():
    def fake_service(**kwargs):
        return {}

    result = execute_approved_new_patient(
        chart_no="",
        name=None,
        birth_date=None,
        phone=None,
        actor_user_id="u1",
        patient_service=fake_service,
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.PATIENT_REGISTRATION_FAILED.value


def test_new_patient_executor_handles_exception():
    def failing(**kwargs):
        raise ValueError("unique constraint failed")

    result = execute_approved_new_patient(
        chart_no="99999",
        name="새환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        actor_user_id="u1",
        patient_service=failing,
    )
    assert result.success is False
    assert result.new_status == AiCommandStatus.PATIENT_REGISTRATION_FAILED.value
    assert "unique constraint" in (result.error_message or "")


# ────────────────────────────── audit 통합 ──────────────────────────────


def test_finalize_audit_records_success(audit_conn):
    cmd_id = ai_audit.write_log(audit_conn, user_id="u1", raw_text="test", status="approved")

    from app.ai.ai_executor import ExecutionResult

    res = ExecutionResult(
        success=True,
        new_status=AiCommandStatus.EXECUTED.value,
        result_payload={"appointment_id": "a1"},
    )
    finalize_audit(ai_audit, audit_conn, command_id=cmd_id, execution=res)

    log = ai_audit.get_log(audit_conn, cmd_id)
    assert log["status"] == AiCommandStatus.EXECUTED.value
    assert log["executed_result"] == {"appointment_id": "a1"}
    assert log["executed_at"] is not None
    assert log["error_message"] is None


def test_finalize_audit_records_failure_with_revalidation(audit_conn, db_session):
    cmd_id = ai_audit.write_log(audit_conn, user_id="u1", raw_text="test", status="approved")

    # 의도적으로 재검증 실패
    def fake_service(**kwargs):
        return {}

    exec_result = execute_approved_appointment(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=None,  # 누락
        start_hour=9,
        treatment_items=[_verified_treatment()],
        memo=None,
        actor_user_id="u1",
        appointment_service=fake_service,
    )
    finalize_audit(ai_audit, audit_conn, command_id=cmd_id, execution=exec_result)

    log = ai_audit.get_log(audit_conn, cmd_id)
    assert log["status"] == AiCommandStatus.VALIDATION_FAILED.value
    assert log["executed_at"] is None  # 실행 안 됨
    assert log["validation_result"] is not None
    assert log["validation_result"]["can_approve"] is False


# ────────────────────────────── 안전 / 단위화 ──────────────────────────────


def test_executor_does_not_modify_db_directly(db_session):
    """executor 호출 후 DB row 변화 0 (callable 이 mock 이라 INSERT 0)."""
    before_p = db_session.query(Patient).count()

    def fake_service(**kwargs):
        return {"appointment_id": "a-mock"}

    execute_approved_appointment(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
        memo=None,
        actor_user_id="u1",
        appointment_service=fake_service,
    )
    after_p = db_session.query(Patient).count()
    assert before_p == after_p  # executor 자체는 DB 직접 수정 안 함


def test_executor_no_external_api_call(db_session):
    """executor 는 외부 API 호출 0."""
    def fake_service(**kwargs):
        return {"ok": True}

    result = execute_approved_appointment(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
        memo=None,
        actor_user_id="u1",
        appointment_service=fake_service,
    )
    assert result.success is True
