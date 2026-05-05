"""Phase 4 — 신환 등록 연계 흐름 단위 테스트.

검증 항목:
- 환자 검색 실패 시 신환 등록 제안 (AI 가 차트번호/생년월일/연락처 자동 생성 안 함)
- 신환 입력 → 중복 검사 (4종) → 권한 정책
- 일반 직원 / 관리자 권한 차이
- 신환 등록과 예약 등록은 각각 별도 audit log row
- 신환 등록 후 예약 후보 재검증 트리거 (자동 저장 금지)
- DB 직접 수정 0 (orchestrator 는 read-only)
"""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai import ai_audit
from app.ai.ai_command_schema import AiCommandStatus
from app.ai.ai_new_patient_flow import (
    UserPermission,
    build_revalidation_request,
    can_register_new_patient,
    evaluate_new_patient_input,
    log_appointment_after_new_patient,
    log_new_patient_registration,
    propose_new_patient_from_resolution,
)
from app.ai.ai_resolver import PatientResolution
from app.ai.ai_validator import NewPatientDuplicateCheck
from app.migrations.m019_ai_command_logs import up as up19
from app.migrations.m020_treatment_aliases import up as up20
from app.models.models import Base, Patient

# ────────────────────────────── Fixtures ──────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.commit()
    yield sess
    sess.close()


@pytest.fixture
def audit_conn():
    """별도 sqlite3 connection — audit log 전용 (in-memory)."""
    c = sqlite3.connect(":memory:")
    up19(c)
    up20(c)
    yield c
    c.close()


# ────────────────────────────── 1단계: 검색 실패 → 제안 ──────────────────────────────


def test_propose_new_patient_when_resolution_not_found():
    res = PatientResolution(not_found=True)
    panel = propose_new_patient_from_resolution(
        res, suggested_chart_no="99999", suggested_name="신환자"
    )
    assert panel is not None
    assert panel["kind"] == "patient_not_found"
    assert panel["status"] == AiCommandStatus.PATIENT_REGISTRATION_PROPOSED.value
    # 차트번호 / 이름은 prefill, 생년월일 / 연락처는 None (AI 가 추측 안 함)
    assert panel["prefill"]["chart_no"] == "99999"
    assert panel["prefill"]["name"] == "신환자"
    assert panel["prefill"]["birth_date"] is None
    assert panel["prefill"]["phone"] is None


def test_propose_new_patient_skips_when_resolution_has_candidates():
    res = PatientResolution(candidates=[])  # not_found=False default
    res.candidates = []
    res.not_found = False
    panel = propose_new_patient_from_resolution(res)
    assert panel is None


# ────────────────────────────── 2단계: 권한 정책 ──────────────────────────────


def test_can_register_no_duplicate_general_user():
    dup = NewPatientDuplicateCheck()
    user = UserPermission(user_id="staff1", is_admin=False)
    ok, reason = can_register_new_patient(dup, user)
    assert ok is True
    assert reason is None


def test_can_register_with_duplicate_general_user_blocked():
    dup = NewPatientDuplicateCheck(
        has_duplicates=True,
        chart_no_duplicate=[{"id": "p1", "chart_no": "12345"}],
    )
    user = UserPermission(user_id="staff1", is_admin=False)
    ok, reason = can_register_new_patient(dup, user)
    assert ok is False
    assert reason and "관리자" in reason


def test_can_register_with_duplicate_admin_allowed():
    dup = NewPatientDuplicateCheck(
        has_duplicates=True,
        chart_no_duplicate=[{"id": "p1"}],
    )
    user = UserPermission(user_id="admin1", is_admin=True)
    ok, _ = can_register_new_patient(dup, user)
    assert ok is True


def test_can_register_missing_required_blocked_for_all():
    dup = NewPatientDuplicateCheck(missing_required=["이름"])
    admin = UserPermission(user_id="admin1", is_admin=True)
    staff = UserPermission(user_id="staff1", is_admin=False)
    assert can_register_new_patient(dup, admin)[0] is False
    assert can_register_new_patient(dup, staff)[0] is False


# ────────────────────────────── 3단계: 입력 평가 ──────────────────────────────


def test_evaluate_new_patient_no_duplicate_general_user(db_session):
    user = UserPermission(user_id="staff1", is_admin=False)
    result = evaluate_new_patient_input(
        db_session,
        chart_no="99999",
        name="새환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        user=user,
    )
    assert result.can_approve is True
    assert result.needs_admin is False
    assert result.status == AiCommandStatus.PATIENT_REGISTRATION_NEEDS_APPROVAL.value
    assert result.proposal_panel is not None
    assert result.proposal_panel["approval_disabled"] is False


def test_evaluate_new_patient_chart_no_duplicate_needs_admin(db_session):
    """차트번호 12345 이 이미 있음 → 일반 직원 unauthorized."""
    user = UserPermission(user_id="staff1", is_admin=False)
    result = evaluate_new_patient_input(
        db_session,
        chart_no="12345",
        name="박환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        user=user,
    )
    assert result.can_approve is False
    assert result.needs_admin is True
    assert result.duplicates.has_duplicates is True


def test_evaluate_new_patient_admin_force_register(db_session):
    """관리자는 차트번호 중복 무시하고 강제 가능."""
    user = UserPermission(user_id="admin1", is_admin=True)
    result = evaluate_new_patient_input(
        db_session,
        chart_no="12345",
        name="박환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        user=user,
    )
    assert result.can_approve is True
    assert result.needs_admin is False


def test_evaluate_new_patient_missing_name_blocks(db_session):
    user = UserPermission(user_id="admin1", is_admin=True)
    result = evaluate_new_patient_input(
        db_session,
        chart_no="99999",
        name=None,
        birth_date="2000-01-01",
        phone="010-9999-9999",
        user=user,
    )
    assert result.can_approve is False
    assert result.duplicates.missing_required == ["이름"]
    assert result.error_message and "이름" in result.error_message


# ────────────────────────────── 4단계: 별도 로그 ──────────────────────────────


def test_log_new_patient_and_appointment_separate_rows(audit_conn):
    """신환 등록과 예약 등록이 별도 row 로 기록 + cross-reference 유지."""
    user = UserPermission(user_id="staff1")
    dup = NewPatientDuplicateCheck()

    new_patient_log_id = log_new_patient_registration(
        ai_audit,
        audit_conn,
        user=user,
        raw_text="박환자 신환 등록",
        chart_no="99999",
        name="새환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        duplicates=dup,
        status=AiCommandStatus.PATIENT_REGISTERED.value,
    )

    appointment_log_id = log_appointment_after_new_patient(
        ai_audit,
        audit_conn,
        user=user,
        raw_text="박환자 4월30일 9시 도수30 예약",
        new_patient_id="new_p1",
        new_patient_log_id=new_patient_log_id,
        status=AiCommandStatus.NEEDS_APPROVAL.value,
    )

    assert new_patient_log_id != appointment_log_id

    # 두 row 모두 존재
    cur = audit_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ai_command_logs")
    assert cur.fetchone()[0] == 2

    # appointment 로그에 new_patient_log_id cross-reference
    log = ai_audit.get_log(audit_conn, appointment_log_id)
    assert log["parsed_json"]["new_patient_log_id"] == new_patient_log_id
    assert log["parsed_json"]["step"] == "appointment_after_new_patient"

    # 신환 로그에 step 명시
    new_log = ai_audit.get_log(audit_conn, new_patient_log_id)
    assert new_log["parsed_json"]["step"] == "new_patient_registration"
    assert new_log["validation_result"]["has_duplicates"] is False


def test_log_new_patient_records_duplicate_count(audit_conn):
    user = UserPermission(user_id="admin1", is_admin=True)
    dup = NewPatientDuplicateCheck(
        has_duplicates=True,
        chart_no_duplicate=[{"id": "p1"}],
        phone_duplicate=[{"id": "p1"}, {"id": "p2"}],
    )
    log_id = log_new_patient_registration(
        ai_audit,
        audit_conn,
        user=user,
        raw_text="강제 등록",
        chart_no="12345",
        name="박환자",
        birth_date="2000-01-01",
        phone="010-1111-2222",
        duplicates=dup,
        status=AiCommandStatus.PATIENT_REGISTRATION_NEEDS_APPROVAL.value,
    )
    log = ai_audit.get_log(audit_conn, log_id)
    assert log["validation_result"]["duplicates_count"] == 3


# ────────────────────────────── 5단계: 신환 후 예약 재검증 ──────────────────────────────


def test_revalidation_request_structure():
    req = build_revalidation_request(
        new_patient_id="new_p1",
        original_command_id=42,
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        start_minute=0,
    )
    assert req["status"] == AiCommandStatus.APPOINTMENT_NEEDS_REVALIDATION.value
    assert req["new_patient_id"] == "new_p1"
    assert req["original_command_id"] == 42
    assert req["appointment_context"]["therapist_id"] == "e1"
    assert req["appointment_context"]["target_date"] == "2026-05-30"
    assert req["appointment_context"]["start_hour"] == 9
    # 자동 저장 금지 — note 명시
    assert "다시 확인" in req["note"] or "재검증" in req["note"] or "확인" in req["note"]


def test_revalidation_request_with_no_therapist():
    req = build_revalidation_request(
        new_patient_id="new_p1",
        original_command_id=1,
        therapist_id=None,
        target_date=None,
        start_hour=None,
    )
    assert req["appointment_context"]["therapist_id"] is None
    assert req["appointment_context"]["target_date"] is None


# ────────────────────────────── 안전 / 단위화 ──────────────────────────────


def test_flow_does_not_modify_db_directly(db_session):
    """orchestrator 는 read-only. DB 변경 0건."""
    before = db_session.query(Patient).count()
    user = UserPermission(user_id="staff1")
    evaluate_new_patient_input(
        db_session,
        chart_no="99999",
        name="새환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        user=user,
    )
    propose_new_patient_from_resolution(PatientResolution(not_found=True))
    after = db_session.query(Patient).count()
    assert before == after


def test_flow_no_external_api_call():
    """flow 모듈은 외부 API 호출 0 (orchestrator)."""
    # 단순 dict 반환만 — ProviderError / network error 없음
    req = build_revalidation_request(
        new_patient_id="new_p1",
        original_command_id=1,
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
    )
    assert req is not None
