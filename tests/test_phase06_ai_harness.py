"""Phase 6 — ai_harness 통합 시나리오 테스트 (10종 풀세트).

검증 항목 (AI_HARNESS_PLAN.md § 1):
1.  Parser              — run_pipeline 의 parser 단계
2.  Resolver            — run_pipeline 의 resolver 단계
3.  Patient Candidate   — 동명이인 / mismatch / not_found 패널
4.  Validator           — 휴무 / 시간 겹침 / 과거 날짜
5.  Approval (Gate 1)   — run_approval_and_execute 의 사전 차단
6.  Executor (Gate 2)   — service callable 호출 / DB 직접 수정 0
7.  Privacy             — 외부 전송 페이로드 PII 미포함
8.  Hallucination       — 단정 표현 / 미확정 → matched_id 채움 차단
9.  Regression          — Phase 1~5 모듈 import / 호출 가능
10. Runtime             — 본 테스트 자체가 실제 코드 경로 호출

파이프라인 통합:
- 박환자 5월 30일 9시 박치료사 도수30 예약 (정상)
- 박환자 (동명이인) → patient_selection_required 상태
- 차트번호+이름 mismatch → patient_mismatch
- 신환 (검색 실패) → patient_not_found + 신환 등록 제안 카드
- 시간 겹침 / 휴무 충돌 → validation_failed
- 신환 등록 + 예약 두 단계 흐름
- DB 직접 수정 0 / 외부 AI API 호출 0
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.ai.ai_command_schema import (
    AiCommandStatus,
    DataSourceState,
    ParserContext,
    TreatmentItem,
    TreatmentItemStatus,
)
from app.ai.ai_harness import (
    check_hallucination,
    check_privacy_payload,
    run_approval_and_execute,
    run_new_patient_and_appointment,
    run_pipeline,
    run_regression_smoke,
)
from app.ai.ai_new_patient_flow import UserPermission
from app.migrations.m019_ai_command_logs import up as up19
from app.migrations.m020_treatment_aliases import up as up20
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
    """in-memory SQLite + 시드 (환자 / 직원 / 치료항목 / alias)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    # 환자 — 박환자 동명이인 2명, 김민수 1명
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.add(Patient(id="p2", name="박환자", chart_no="22345", birth_date="1975-09-02", phone="010-3333-4444"))
    sess.add(Patient(id="p3", name="김민수", chart_no="33333", birth_date="1990-01-01", phone="010-5555-6666"))
    # 치료사
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Employee(id="e2", name="김치료사", role="therapist", color="#9CA3AF", active=True))
    # 치료항목
    sess.add(Treatment(id="t1", code="manual_30", name="도수치료 30분", short="도30", count_increment=1))
    sess.add(Treatment(id="t2", code="manual_60", name="도수치료 60분", short="도60", count_increment=1))
    sess.add(Treatment(id="t3", code="eswt", name="체외충격파", short="ESWT", count_increment=1))
    sess.add(Treatment(id="t4", code="injection", name="주사치료", short="주사", count_increment=1))
    # alias 테이블 raw SQL
    sess.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS treatment_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treatment_id TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(treatment_id, alias_name)
            )
            """
        )
    )
    aliases = [
        ("t1", "도30"), ("t1", "도수30"),
        ("t2", "도60"), ("t2", "도수60"),
        ("t3", "체외"), ("t3", "충격파"), ("t3", "ESWT"), ("t3", "충"),
        ("t4", "주사"), ("t4", "주"),
    ]
    for tid, alias in aliases:
        sess.execute(
            text("INSERT INTO treatment_aliases (treatment_id, alias_name) VALUES (:tid, :alias)"),
            {"tid": tid, "alias": alias},
        )
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


# ────────────────────────────── 1. Parser + Resolver + Validator 통합 ──────────────────────────────


def test_pipeline_full_normal_path_single_patient(db_session):
    """차트번호로 단일 환자 확정 → validation 통과 → NEEDS_APPROVAL.

    "차트번호 12345 5월 30일 9시 박치료사 도수30 예약"
    """
    today = date(2026, 5, 1)
    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=today,
    )
    assert res.parsed.chart_number == "12345"
    assert res.parsed.therapist_name == "박치료사"
    assert res.patient_resolution.match_rank == 1
    assert res.selected_patient is not None
    assert res.selected_patient.patient_id == "p1"
    assert res.therapist_resolution.therapist_id == "e1"
    assert res.date_resolution.resolved_date == date(2026, 5, 30)
    assert res.time_resolution.hour == 9
    assert len(res.treatment_items) == 1
    assert res.treatment_items[0].matched_treatment_id == "t1"
    assert res.validation is not None
    assert res.validation.can_approve is True
    assert res.status == AiCommandStatus.NEEDS_APPROVAL.value
    assert res.preview is not None
    assert res.preview["title"] == "예약 후보"  # "예약 완료" 표현 금지


def test_pipeline_homonym_requires_selection(db_session):
    """박환자 동명이인 → patient_selection_required (자동 확정 금지)."""
    res = run_pipeline(
        db_session,
        raw_text="박환자 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert len(res.patient_resolution.candidates) == 2
    assert res.selected_patient is None  # AI 가 임의 선택 안 함
    assert res.status == AiCommandStatus.PATIENT_SELECTION_REQUIRED.value
    assert res.patient_panel["kind"] == "patient_selection_required"
    assert res.patient_panel["approval_disabled"] is True
    # 후보 목록에 차트번호 / 이름 / 생년월일 / 연락처 모두 포함
    for c in res.patient_panel["candidates"]:
        assert c["chart_no"]
        assert c["name"]
        assert c["birth_date"]
        assert c["phone"]


def test_pipeline_homonym_with_selected_patient_id(db_session):
    """동명이인 중 selected_patient_id 로 확정 → validation 진행."""
    res = run_pipeline(
        db_session,
        raw_text="박환자 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
        selected_patient_id="p2",
    )
    assert res.selected_patient is not None
    assert res.selected_patient.patient_id == "p2"
    assert res.validation is not None
    assert res.validation.can_approve is True


def test_pipeline_chart_name_mismatch(db_session):
    """차트번호 12345 + 김민수 → mismatch."""
    res = run_pipeline(
        db_session,
        raw_text="김민수 차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.patient_resolution.mismatch is True
    assert res.status == AiCommandStatus.PATIENT_MISMATCH.value
    assert res.patient_panel["kind"] == "patient_mismatch"
    assert res.patient_panel["approval_disabled"] is True


def test_pipeline_patient_not_found_proposes_new(db_session):
    """검색 실패 환자 → patient_not_found + 신환 등록 제안 카드."""
    res = run_pipeline(
        db_session,
        raw_text="신환자xyz 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.patient_resolution.not_found is True
    assert res.status == AiCommandStatus.PATIENT_NOT_FOUND.value
    assert res.new_patient_proposal is not None
    assert res.new_patient_proposal["kind"] == "patient_not_found"
    # AI 가 생년월일 / 연락처 임의 생성 안 함
    assert res.new_patient_proposal["prefill"]["birth_date"] is None
    assert res.new_patient_proposal["prefill"]["phone"] is None


def test_pipeline_treatment_alias_conflict(db_session):
    """alias '주' 가 t4(주사) 이미 매핑. t2(도수60) 에도 추가하면 충돌."""
    db_session.execute(
        text("INSERT INTO treatment_aliases (treatment_id, alias_name) VALUES ('t2', '주')")
    )
    db_session.commit()
    res = run_pipeline(
        db_session,
        raw_text="박환자 차트번호 12345 5월30일 9시 박치료사 주 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert any(
        ti.status == TreatmentItemStatus.ALIAS_CONFLICT for ti in res.treatment_items
    )
    assert res.status == AiCommandStatus.TREATMENT_ALIAS_CONFLICT.value


def test_pipeline_time_overlap_blocks_approval(db_session):
    """기존 예약과 시간 겹침 → validation_failed."""
    # 기존 예약: 박치료사 5월30일 9:00 - 9:30
    target = datetime(2026, 5, 30, 9, 0)
    db_session.add(
        Appointment(
            id="a1",
            patient_id="p1",
            therapist_id="e1",
            start_at=target,
            end_at=target + timedelta(minutes=30),
            status="reserved",
            treatment_codes="[\"manual_30\"]",
        )
    )
    db_session.commit()

    res = run_pipeline(
        db_session,
        raw_text="차트번호 22345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.validation is not None
    assert res.validation.can_approve is False
    assert any(i.code == "시간_겹침" for i in res.validation.issues)
    assert res.status == AiCommandStatus.VALIDATION_FAILED.value


def test_pipeline_leave_conflict_blocks_approval(db_session):
    """치료사 휴무 → validation_failed."""
    db_session.add(
        EmployeeLeave(
            id="l1",
            employee_id="e1",
            leave_date="2026-05-30",
            leave_type="full",
        )
    )
    db_session.commit()
    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.validation is not None
    assert res.validation.can_approve is False
    assert any(i.code == "휴무_충돌" for i in res.validation.issues)


# ────────────────────────────── 2. Approval + Executor (Gate 1 / Gate 2) ──────────────────────────────


def test_approval_and_execute_normal_path(db_session, audit_conn):
    """정상 경로 — Gate 1 통과 + Gate 2 통과 + service 호출 + audit 기록."""
    captured = {}

    def fake_appointment_service(**kwargs):
        captured.update(kwargs)
        return {"appointment_id": "a-new", "status": "scheduled"}

    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.status == AiCommandStatus.NEEDS_APPROVAL.value

    user = UserPermission(user_id="staff1", is_admin=False)
    execution = run_approval_and_execute(
        db_session,
        audit_conn,
        run_result=res,
        user=user,
        appointment_service=fake_appointment_service,
        memo="첫 방문",
    )
    assert execution.success is True
    assert execution.new_status == AiCommandStatus.EXECUTED.value
    assert captured["patient_id"] == "p1"
    assert captured["therapist_id"] == "e1"
    assert captured["target_date"] == date(2026, 5, 30)
    assert captured["start_hour"] == 9
    assert captured["treatment_codes"] == ["t1"]
    assert captured["memo"] == "첫 방문"

    # audit log 확인
    cur = audit_conn.cursor()
    cur.execute("SELECT status, executed_at FROM ai_command_logs ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    assert row[0] == AiCommandStatus.EXECUTED.value
    assert row[1] is not None  # executed_at 기록


def test_approval_blocks_when_status_not_needs_approval(db_session, audit_conn):
    """Gate 1 — needs_approval 가 아니면 service 호출 0."""
    calls = {"count": 0}

    def fake_service(**kwargs):
        calls["count"] += 1
        return {"appointment_id": "a-x"}

    # 동명이인 → patient_selection_required → 승인 차단되어야 함
    res = run_pipeline(
        db_session,
        raw_text="박환자 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.status == AiCommandStatus.PATIENT_SELECTION_REQUIRED.value

    user = UserPermission(user_id="staff1", is_admin=False)
    execution = run_approval_and_execute(
        db_session,
        audit_conn,
        run_result=res,
        user=user,
        appointment_service=fake_service,
    )
    assert execution.success is False
    assert calls["count"] == 0  # Gate 1 차단


def test_approval_executor_blocks_when_revalidation_fails(db_session, audit_conn):
    """Gate 2 — 승인 후 다른 사용자가 끼어든 시간 겹침을 검출."""
    calls = {"count": 0}

    def fake_service(**kwargs):
        calls["count"] += 1
        return {"appointment_id": "a-x"}

    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.status == AiCommandStatus.NEEDS_APPROVAL.value

    # run_pipeline 후, run_approval_and_execute 직전에 다른 사용자가 같은 시간에 예약
    target = datetime(2026, 5, 30, 9, 0)
    db_session.add(
        Appointment(
            id="conflict",
            patient_id="p3",
            therapist_id="e1",
            start_at=target,
            end_at=target + timedelta(minutes=30),
            status="reserved",
            treatment_codes="[\"manual_30\"]",
        )
    )
    db_session.commit()

    user = UserPermission(user_id="staff1", is_admin=False)
    execution = run_approval_and_execute(
        db_session,
        audit_conn,
        run_result=res,
        user=user,
        appointment_service=fake_service,
    )
    assert execution.success is False
    assert execution.new_status == AiCommandStatus.VALIDATION_FAILED.value
    assert calls["count"] == 0  # Gate 2 차단


def test_approval_executor_handles_service_exception(db_session, audit_conn):
    """service 예외 → ExecutionResult.success=False, 기존 프로그램 보호."""
    def failing_service(**kwargs):
        raise RuntimeError("DB write failed")

    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    user = UserPermission(user_id="staff1", is_admin=False)
    execution = run_approval_and_execute(
        db_session,
        audit_conn,
        run_result=res,
        user=user,
        appointment_service=failing_service,
    )
    assert execution.success is False
    assert execution.new_status == AiCommandStatus.FAILED.value
    assert "DB write failed" in (execution.error_message or "")


# ────────────────────────────── 3. 신환 등록 + 예약 두 단계 흐름 ──────────────────────────────


def test_new_patient_then_appointment_two_stages(db_session, audit_conn):
    """신환 등록 → 등록된 patient_id 로 예약 등록. 별도 audit row 2개."""
    pat_calls = {"count": 0}
    appt_calls = {"count": 0}

    def fake_patient_service(**kwargs):
        pat_calls["count"] += 1
        return {"patient_id": "p-new", "chart_no": kwargs["chart_no"]}

    def fake_appointment_service(**kwargs):
        appt_calls["count"] += 1
        return {"appointment_id": "a-new"}

    user = UserPermission(user_id="staff1", is_admin=False)
    treatment = TreatmentItem(
        raw_text="도수30",
        matched_treatment_id="t1",
        matched_treatment_name="도수치료 30분",
        source=DataSourceState.DB_VERIFIED,
        status=TreatmentItemStatus.DB_VERIFIED,
    )
    pat_exec, appt_exec = run_new_patient_and_appointment(
        db_session,
        audit_conn,
        raw_text="신환자xyz 5월30일 9시 박치료사 도수30 예약",
        user=user,
        chart_no="99999",
        name="신환자xyz",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        patient_service=fake_patient_service,
        appointment_service=fake_appointment_service,
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[treatment],
    )
    assert pat_exec.success is True
    assert pat_exec.new_status == AiCommandStatus.PATIENT_REGISTERED.value
    assert appt_exec.success is True
    assert appt_exec.new_status == AiCommandStatus.EXECUTED.value
    assert pat_calls["count"] == 1
    assert appt_calls["count"] == 1

    # audit log 2 row (신환 + 예약)
    cur = audit_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ai_command_logs")
    assert cur.fetchone()[0] == 2


def test_new_patient_failure_skips_appointment(db_session, audit_conn):
    """신환 등록 실패 → 예약 단계 건너뜀."""
    appt_calls = {"count": 0}

    def failing_patient(**kwargs):
        raise ValueError("unique constraint failed")

    def fake_appt(**kwargs):
        appt_calls["count"] += 1
        return {}

    user = UserPermission(user_id="staff1", is_admin=False)
    pat_exec, appt_exec = run_new_patient_and_appointment(
        db_session,
        audit_conn,
        raw_text="중복환자",
        user=user,
        chart_no="99999",
        name="중복환자",
        birth_date="2000-01-01",
        phone="010-9999-9999",
        patient_service=failing_patient,
        appointment_service=fake_appt,
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[],
    )
    assert pat_exec.success is False
    assert appt_exec.success is False
    assert appt_calls["count"] == 0  # 예약 service 호출 0


# ────────────────────────────── 4. Privacy 하네스 ──────────────────────────────


def test_privacy_check_clean_payload():
    """ParserContext 는 raw_text + 캘린더 + intent 목록만 — PII 없음."""
    ctx = ParserContext(
        raw_text="박환자 내일 9시 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        available_intents=["create_appointment"],
        treatment_names=["도수치료 30분"],
    )
    result = check_privacy_payload(ctx)
    assert result.ok is True
    assert result.violations == []


def test_privacy_check_detects_patient_list():
    payload = {
        "raw_text": "박환자",
        "patient_list": [
            {"name": "박환자", "phone": "010-1111-2222"},
            {"name": "김민수", "phone": "010-2222-3333"},
        ],
    }
    result = check_privacy_payload(payload)
    assert result.ok is False
    assert any("patient_list" in v for v in result.violations)


def test_privacy_check_detects_phone_and_birth_lists():
    payload = {
        "raw_text": "박환자",
        "context": {
            "all_phones": ["010-1111-2222"],
            "all_birth_dates": ["1980-04-15"],
        },
    }
    result = check_privacy_payload(payload)
    assert result.ok is False
    assert len(result.violations) == 2


def test_privacy_check_detects_patient_memo():
    payload = {"patient_memo": "통증 심함, 만성"}
    result = check_privacy_payload(payload)
    assert result.ok is False


def test_privacy_check_nested_violation():
    payload = {
        "outer": {
            "inner": {"appointment_memo": "민감 내용"},
        }
    }
    result = check_privacy_payload(payload)
    assert result.ok is False
    assert any("appointment_memo" in v for v in result.violations)


def test_privacy_pipeline_does_not_send_pii_to_provider(db_session):
    """run_pipeline 에서 provider 에 전달되는 ParserContext 는 PII 미포함."""
    captured = {}

    class CapturingProvider:
        name = "capture"

        def parse_command(self, raw_text, context):
            captured["context"] = context
            from app.ai.ai_command_schema import ParsedCommand
            return ParsedCommand(raw_text=raw_text)

    run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
        provider=CapturingProvider(),
    )
    assert "context" in captured
    privacy = check_privacy_payload(captured["context"])
    assert privacy.ok is True


# ────────────────────────────── 5. Hallucination 하네스 ──────────────────────────────


def test_hallucination_detects_completion_phrase(db_session):
    """응답 텍스트에 '예약 완료' 가 포함되면 위반."""
    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    bad = check_hallucination(
        res.parsed,
        patient_resolution=res.patient_resolution,
        treatment_items=res.treatment_items,
        response_text="예약 완료했습니다.",
    )
    assert bad.ok is False
    good = check_hallucination(
        res.parsed,
        patient_resolution=res.patient_resolution,
        treatment_items=res.treatment_items,
        response_text="예약 후보를 만들었습니다. 승인하면 예약이 등록됩니다.",
    )
    assert good.ok is True


def test_hallucination_detects_inconsistent_treatment_status():
    """치료항목 status=needs_clarification 인데 matched_id 가 채워진 경우 위반."""
    bad_item = TreatmentItem(
        raw_text="주",
        matched_treatment_id="t4",  # 채워짐
        status=TreatmentItemStatus.NEEDS_CLARIFICATION,  # 미확정
    )
    from app.ai.ai_command_schema import ParsedCommand

    result = check_hallucination(
        ParsedCommand(raw_text="박환자 내일 9시 주 예약"),
        treatment_items=[bad_item],
    )
    assert result.ok is False


def test_hallucination_detects_db_verified_without_id():
    """status=db_verified 인데 matched_id 가 None 인 경우 위반."""
    bad_item = TreatmentItem(
        raw_text="도수30",
        matched_treatment_id=None,  # 누락
        status=TreatmentItemStatus.DB_VERIFIED,
    )
    from app.ai.ai_command_schema import ParsedCommand

    result = check_hallucination(
        ParsedCommand(raw_text="박환자 내일 9시 도수30 예약"),
        treatment_items=[bad_item],
    )
    assert result.ok is False


def test_hallucination_clean_run_pipeline_result(db_session):
    """정상 파이프라인 결과는 hallucination 위반 0."""
    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    result = check_hallucination(
        res.parsed,
        patient_resolution=res.patient_resolution,
        treatment_items=res.treatment_items,
    )
    assert result.ok is True


# ────────────────────────────── 6. Regression smoke ──────────────────────────────


def test_regression_smoke_phase_1_to_5_callable(db_session):
    """Phase 1~5 모듈 import + 핵심 함수 시그니처 살아있음."""
    results = run_regression_smoke(db_session)
    assert results == {
        "parser_callable": True,
        "resolver_callable": True,
        "validator_callable": True,
        "preview_callable": True,
    }


# ────────────────────────────── 7. 안전 — DB 직접 수정 0 / 외부 API 0 ──────────────────────────────


def test_pipeline_no_db_modification(db_session):
    """run_pipeline 호출 후 DB row 변화 0."""
    before_p = db_session.query(Patient).count()
    before_a = db_session.query(Appointment).count()
    run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert db_session.query(Patient).count() == before_p
    assert db_session.query(Appointment).count() == before_a


def test_pipeline_no_external_api_call(db_session):
    """provider 없이 호출 — 외부 호출 0 (정규식 fallback)."""
    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.parsed.intent is not None  # 정규식 fallback 으로 intent 추출됨


def test_provider_failure_still_completes_pipeline(db_session):
    """provider 가 실패해도 정규식 fallback 으로 파이프라인 끝까지 진행 (기존 프로그램 보호)."""
    from app.ai.ai_provider import ProviderError

    class FailingProvider:
        name = "failing"

        def parse_command(self, raw_text, context):
            raise ProviderError("simulated failure")

    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
        provider=FailingProvider(),
    )
    # fallback 경로로 동일하게 동작
    assert res.parsed.chart_number == "12345"
    assert res.selected_patient is not None
    assert res.selected_patient.patient_id == "p1"


# ────────────────────────────── 8. 표현 / 메시지 정합 ──────────────────────────────


def test_preview_uses_safe_phrasing(db_session):
    """preview['title'] 가 '예약 후보' (예약 완료 표현 금지)."""
    res = run_pipeline(
        db_session,
        raw_text="차트번호 12345 5월30일 9시 박치료사 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
        today=date(2026, 5, 1),
    )
    assert res.preview is not None
    assert "예약 완료" not in res.preview["title"]
    assert res.preview["title"] == "예약 후보"
    # prompt 메시지도 확인
    assert "예약 등록" in res.preview["prompt"]
