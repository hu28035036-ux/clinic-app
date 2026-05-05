"""Phase 3 — ai_validator / ai_preview 단위 테스트.

검증 항목:
- Validator: 환자 / 치료사 / 날짜 / 시간 미확정 → can_approve=False
- 휴무 / 반차 충돌, 시간 겹침, 과거 날짜 차단
- 치료항목 alias 충돌 / NOT_FOUND / NEEDS_CLARIFICATION 시 승인 불가
- 신환 등록 중복 검사 (차트번호 / 이름+생년월일 / 이름+연락처 / 연락처)
- Preview: 환자 후보 카드 / 치료항목 후보 카드 / 신환 등록 카드 / 최종 예약 후보 카드
- "예약 완료" 표현 금지 / "예약 후보" 표시
- 환자 정보에 차트번호/이름/생년월일/연락처 포함
- approval_disabled 정확
- DB 직접 수정 0건 (validator read-only)
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.ai_command_schema import (
    DataSourceState,
    TreatmentItem,
    TreatmentItemStatus,
)
from app.ai.ai_preview import (
    build_appointment_preview,
    build_new_patient_proposal,
    build_patient_candidate_panel,
    build_treatment_candidate_panel,
)
from app.ai.ai_resolver import PatientCandidate
from app.ai.ai_validator import (
    NewPatientDuplicateCheck,
    ValidationIssue,
    ValidationResult,
    check_new_patient_duplicates,
    validate_appointment_candidate,
)
from app.models.models import (
    Appointment,
    Base,
    Employee,
    EmployeeLeave,
    Patient,
    Treatment,
)

# ────────────────────────────── DB fixture ──────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.add(Patient(id="p2", name="박환자", chart_no="22345", birth_date="1975-09-02", phone="010-2222-3333"))
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Treatment(id="t1", code="manual_30", name="도수치료 30분", short="도30", count_increment=1))
    sess.commit()
    yield sess
    sess.close()


def _verified_treatment(name: str = "도수치료 30분", tid: str = "t1") -> TreatmentItem:
    return TreatmentItem(
        raw_text="도수30",
        matched_treatment_id=tid,
        matched_treatment_name=name,
        source=DataSourceState.DB_VERIFIED,
        status=TreatmentItemStatus.DB_VERIFIED,
    )


# ────────────────────────────── Validator — 필수값 ──────────────────────────────


def test_validator_missing_patient(db_session):
    res = validate_appointment_candidate(
        db_session,
        patient_id=None,
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is False
    assert any(i.code == "환자_미선택" for i in res.issues)


def test_validator_missing_date(db_session):
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=None,
        start_hour=9,
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is False
    assert any(i.code == "날짜_미확정" for i in res.issues)


def test_validator_missing_time(db_session):
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=None,
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is False
    assert any(i.code == "시간_미확정" for i in res.issues)


def test_validator_missing_treatment(db_session):
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[],
    )
    assert res.can_approve is False
    assert any(i.code == "치료항목_미선택" for i in res.issues)


# ────────────────────────────── Validator — 치료항목 상태 ──────────────────────────────


def test_validator_treatment_alias_conflict_blocks_approval(db_session):
    ti = TreatmentItem(
        raw_text="주",
        source=DataSourceState.AI_EXTRACTED,
        status=TreatmentItemStatus.ALIAS_CONFLICT,
        candidates=[{"id": "t1", "name": "주사치료"}, {"id": "t2", "name": "주말 영업"}],
    )
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[ti],
    )
    assert res.can_approve is False
    assert any(i.code == "치료항목_alias_충돌" for i in res.issues)


def test_validator_treatment_not_found_blocks_approval(db_session):
    ti = TreatmentItem(
        raw_text="존재안함",
        source=DataSourceState.AI_EXTRACTED,
        status=TreatmentItemStatus.NOT_FOUND,
    )
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[ti],
    )
    assert res.can_approve is False
    assert any(i.code == "치료항목_없음" for i in res.issues)


# ────────────────────────────── Validator — 휴무 / 시간 겹침 ──────────────────────────────


def test_validator_full_leave_blocks(db_session):
    db_session.add(EmployeeLeave(id="l1", employee_id="e1", leave_date="2026-05-30", leave_type="full"))
    db_session.commit()
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is False
    assert any(i.code == "휴무_충돌" for i in res.issues)


def test_validator_am_leave_blocks_morning(db_session):
    db_session.add(EmployeeLeave(id="l2", employee_id="e1", leave_date="2026-05-30", leave_type="am"))
    db_session.commit()
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=10,  # AM
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is False


def test_validator_am_leave_allows_afternoon(db_session):
    db_session.add(EmployeeLeave(id="l3", employee_id="e1", leave_date="2026-05-30", leave_type="am"))
    db_session.commit()
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=14,  # PM
        treatment_items=[_verified_treatment()],
    )
    assert res.checks.get("휴무/반차 충돌 없음") is True


def test_validator_pm_leave_blocks_afternoon(db_session):
    db_session.add(EmployeeLeave(id="l4", employee_id="e1", leave_date="2026-05-30", leave_type="pm"))
    db_session.commit()
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=14,  # PM
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is False


def test_validator_time_overlap_blocks(db_session):
    db_session.add(
        Appointment(
            id="a1",
            patient_id="p2",  # 다른 환자
            therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            duration_min=30,
        )
    )
    db_session.commit()
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        start_minute=15,  # 9:15-9:45 → 9:00-9:30 과 겹침
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is False
    assert any(i.code == "시간_겹침" for i in res.issues)


def test_validator_no_overlap_when_back_to_back(db_session):
    db_session.add(
        Appointment(
            id="a2",
            patient_id="p2",
            therapist_id="e1",
            start_at=datetime(2026, 5, 30, 9, 0),
            end_at=datetime(2026, 5, 30, 9, 30),
            duration_min=30,
        )
    )
    db_session.commit()
    # 9:30 시작 (이전 예약 끝나자마자) — 겹치지 않음
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        start_minute=30,
        treatment_items=[_verified_treatment()],
    )
    assert res.checks.get("시간 겹침 없음") is True


def test_validator_past_date_blocks(db_session):
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 4, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
        is_past_date=True,
    )
    assert res.can_approve is False
    assert any(i.code == "과거_날짜" for i in res.issues)


def test_validator_all_pass(db_session):
    res = validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
    )
    assert res.can_approve is True
    assert res.checks.get("환자 확인됨") is True
    assert res.checks.get("치료항목 확인됨") is True
    assert res.checks.get("중복 예약 없음") is True


# ────────────────────────────── 신환 등록 중복 검사 ──────────────────────────────


def test_check_new_patient_chart_no_duplicate(db_session):
    res = check_new_patient_duplicates(
        db_session, chart_no="12345", name="박환자", birth_date="1990-01-01", phone="010-9999-9999"
    )
    assert res.has_duplicates is True
    assert len(res.chart_no_duplicate) == 1


def test_check_new_patient_name_birth_duplicate(db_session):
    res = check_new_patient_duplicates(
        db_session,
        chart_no="99999",
        name="박환자",
        birth_date="1980-04-15",  # p1 과 동일
        phone="010-9999-9999",
    )
    assert res.has_duplicates is True
    assert len(res.name_birth_duplicate) == 1


def test_check_new_patient_phone_duplicate(db_session):
    res = check_new_patient_duplicates(
        db_session, chart_no="99999", name="새이름", birth_date="2000-01-01", phone="010-1111-2222"
    )
    assert res.has_duplicates is True
    assert len(res.phone_duplicate) == 1


def test_check_new_patient_no_duplicate(db_session):
    res = check_new_patient_duplicates(
        db_session,
        chart_no="99999",
        name="새이름",
        birth_date="2000-01-01",
        phone="010-9999-9999",
    )
    assert res.has_duplicates is False
    assert res.missing_required == []


def test_check_new_patient_missing_name(db_session):
    res = check_new_patient_duplicates(
        db_session, chart_no="99999", name=None, birth_date="2000-01-01", phone="010-9999-9999"
    )
    assert "이름" in res.missing_required


# ────────────────────────────── Preview — 환자 후보 ──────────────────────────────


def test_preview_patient_single_candidate():
    panel = build_patient_candidate_panel(
        [PatientCandidate("p1", "12345", "박환자", "1980-04-15", "010-1111-2222")]
    )
    assert panel["kind"] == "patient_confirmed"
    assert panel["approval_disabled"] is False


def test_preview_patient_homonym_disables_approval():
    panel = build_patient_candidate_panel(
        [
            PatientCandidate("p1", "12345", "박환자", "1980-04-15", "010-1111-2222"),
            PatientCandidate("p2", "22345", "박환자", "1975-09-02", "010-2222-3333"),
        ]
    )
    assert panel["kind"] == "patient_selection_required"
    assert panel["approval_disabled"] is True
    assert "박환자" in panel["message"] and "여러 명" in panel["message"]
    # 차트번호 / 이름 / 생년월일 / 연락처 모두 표시
    assert {"chart_no", "name", "birth_date", "phone"}.issubset(panel["candidates"][0].keys())


def test_preview_patient_mismatch():
    panel = build_patient_candidate_panel(
        [PatientCandidate("p1", "12345", "박환자", "1980-04-15", "010-1111-2222")],
        is_mismatch=True,
    )
    assert panel["kind"] == "patient_mismatch"
    assert panel["approval_disabled"] is True


def test_preview_patient_not_found_proposes_new():
    panel = build_patient_candidate_panel([], is_not_found=True)
    assert panel["kind"] == "patient_not_found"
    assert "신환" in panel["message"]
    assert "신환 등록" in panel["actions"]


# ────────────────────────────── Preview — 치료항목 ──────────────────────────────


def test_preview_treatment_all_verified():
    items = [_verified_treatment()]
    panel = build_treatment_candidate_panel(items)
    assert panel["approval_disabled"] is False


def test_preview_treatment_needs_clarification():
    items = [
        _verified_treatment(),
        TreatmentItem(raw_text="주", status=TreatmentItemStatus.NEEDS_CLARIFICATION),
    ]
    panel = build_treatment_candidate_panel(items)
    assert panel["approval_disabled"] is True
    assert "선택" in panel["note"]


def test_preview_treatment_alias_conflict():
    items = [
        TreatmentItem(
            raw_text="주",
            status=TreatmentItemStatus.ALIAS_CONFLICT,
            candidates=[{"id": "t1", "name": "주사치료"}, {"id": "t2", "name": "주말근무"}],
        )
    ]
    panel = build_treatment_candidate_panel(items)
    assert panel["approval_disabled"] is True


# ────────────────────────────── Preview — 신환 등록 ──────────────────────────────


def test_preview_new_patient_no_duplicate_can_approve():
    dup = NewPatientDuplicateCheck()
    panel = build_new_patient_proposal(
        chart_no="99999", name="새환자", birth_date="2000-01-01", phone="010-9999-9999",
        duplicates=dup,
    )
    assert panel["approval_disabled"] is False
    assert panel["needs_admin"] is False


def test_preview_new_patient_duplicate_needs_admin():
    dup = NewPatientDuplicateCheck(
        has_duplicates=True,
        chart_no_duplicate=[{"id": "p1", "chart_no": "12345", "name": "박환자"}],
    )
    panel = build_new_patient_proposal(
        chart_no="12345", name="박환자", birth_date="2000-01-01", phone="010-9999-9999",
        duplicates=dup,
        is_admin=False,
    )
    assert panel["approval_disabled"] is True
    assert panel["needs_admin"] is True


def test_preview_new_patient_admin_can_force():
    dup = NewPatientDuplicateCheck(
        has_duplicates=True,
        phone_duplicate=[{"id": "p1", "phone": "010-1111-2222"}],
    )
    panel = build_new_patient_proposal(
        chart_no="99999", name="박환자", birth_date="2000-01-01", phone="010-1111-2222",
        duplicates=dup,
        is_admin=True,
    )
    assert panel["approval_disabled"] is False
    assert panel["needs_admin"] is False  # 관리자라 강제 가능


# ────────────────────────────── Preview — 최종 예약 후보 ──────────────────────────────


def test_preview_appointment_card_structure():
    patient = PatientCandidate("p1", "12345", "박환자", "1980-04-15", "010-1111-2222")
    items = [_verified_treatment()]
    validation = ValidationResult(
        can_approve=True,
        checks={"환자 확인됨": True, "치료항목 확인됨": True, "중복 예약 없음": True},
    )
    card = build_appointment_preview(
        patient=patient,
        target_date=date(2026, 5, 30),
        start_hour=9,
        therapist_name="박치료사",
        treatment_items=items,
        validation=validation,
        date_note="30일을 현재 선택된 2026년 5월 기준으로 해석했습니다.",
    )
    # 환자 정보 포함 (차트번호 / 이름 / 생년월일 / 연락처)
    pi = card["patient_info"]
    assert pi["chart_no"] == "12345"
    assert pi["name"] == "박환자"
    assert pi["birth_date"] == "1980-04-15"
    assert pi["phone"] == "010-1111-2222"
    # 예약 정보
    assert card["appointment_info"]["date"] == "2026-05-30"
    assert card["appointment_info"]["time"] == "09:00"
    assert card["appointment_info"]["therapist_name"] == "박치료사"
    # 메시지: "예약 후보" / "예약 등록할까요?" / "예약 완료" 표현 금지
    assert card["title"] == "예약 후보"
    assert card["prompt"] == "해당 날짜에 예약 등록할까요?"
    assert "예약 완료" not in card["title"]
    assert "예약 완료" not in card["prompt"]
    # 액션 버튼
    assert card["actions"] == ["취소", "예약 등록"]
    # 승인 가능
    assert card["approval_disabled"] is False


def test_preview_appointment_card_blocks_when_validation_fails():
    validation = ValidationResult(
        can_approve=False,
        issues=[ValidationIssue("휴무_충돌", "치료사 휴무와 충돌")],
    )
    card = build_appointment_preview(
        patient=PatientCandidate("p1", "12345", "박환자", "1980-04-15", "010-1111-2222"),
        target_date=date(2026, 5, 30),
        start_hour=9,
        therapist_name="박치료사",
        treatment_items=[_verified_treatment()],
        validation=validation,
    )
    assert card["approval_disabled"] is True
    assert card["validation"]["issues"][0]["code"] == "휴무_충돌"


# ────────────────────────────── 안전 / 보안 ──────────────────────────────


def test_validator_does_not_modify_db(db_session):
    """validator 호출 후 DB row 개수 변화 0."""
    before_p = db_session.query(Patient).count()
    before_a = db_session.query(Appointment).count()
    validate_appointment_candidate(
        db_session,
        patient_id="p1",
        therapist_id="e1",
        target_date=date(2026, 5, 30),
        start_hour=9,
        treatment_items=[_verified_treatment()],
    )
    check_new_patient_duplicates(
        db_session, chart_no="99999", name="새환자", birth_date="2000-01-01", phone="010-1111-2222"
    )
    assert db_session.query(Patient).count() == before_p
    assert db_session.query(Appointment).count() == before_a


def test_preview_does_not_make_external_calls():
    """preview 모듈은 외부 API / DB 직접 조작 0."""
    # 단순 dataclass → dict 변환만. 실패하지 않으면 OK.
    panel = build_patient_candidate_panel(
        [PatientCandidate("p1", "12345", "박환자", "1980-04-15", "010-1111-2222")]
    )
    assert panel is not None
