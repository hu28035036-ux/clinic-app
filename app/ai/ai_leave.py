"""ai_leave — Phase 8 휴무 / 반차 등록 AI (`create_leave` intent).

Post-Phase 11 보강: `run_leave_pipeline` 으로 parse + resolve + validate + preview 통합.
ai_harness.run_pipeline 의 휴무 도메인 변형. UI 통합 endpoint (commands_parse) 가 호출.

역할:
- 치료사 휴무 / 반차 등록 후보 생성 (종일 / 오전반차 / 오후반차)
- 휴무 유형 추출 (종일 / 연차 → full, 오전반차 → am, 오후반차 → pm)
- 같은 날짜 기존 휴무 중복 검사
- 해당 시간대 기존 예약 충돌 목록 (별도 고지용)
- 비활성 치료사 차단
- 승인 후 service callable 호출 (DB 직접 수정 ⊥)

설계:
- 본 모듈은 **read-only resolver / preview** + service callable 호출.
- LeaveServiceCallable Protocol — caller (router) 가 기존 휴무 등록 service 주입.
- 충돌 예약은 *차단 사유가 아닌 안내 정보* — 사용자가 본 정보를 보고 승인 / 취소 결정.
  (AI_FEATURE_MASTER_PLAN § 5.3 "충돌 예약은 별도 고지").

cross-reference:
- 13 필드 정의 → AI_FEATURE_MASTER_PLAN.md § 5.3
- Gate 1 / Gate 2 → AI_SAFETY_POLICY.md § 4
- 휴무 유형 → app.models.models.EmployeeLeave.leave_type ("full" / "am" / "pm")

하네스: tests/test_phase08_ai_leave.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol

from app.ai.ai_command_schema import AiCommandStatus
from app.ai.ai_validator import ValidationIssue, ValidationResult


# ────────────────────────────── 결과 데이터 ──────────────────────────────


# leave_type 코드 — EmployeeLeave 모델과 정합
LEAVE_TYPE_FULL = "full"
LEAVE_TYPE_AM = "am"
LEAVE_TYPE_PM = "pm"
VALID_LEAVE_TYPES: tuple[str, ...] = (LEAVE_TYPE_FULL, LEAVE_TYPE_AM, LEAVE_TYPE_PM)


@dataclass
class ConflictingAppointment:
    """휴무 등록 시 시간대 충돌 예약 1건 (안내용)."""

    appointment_id: str
    patient_id: str
    start_at: datetime
    end_at: datetime


@dataclass
class LeaveValidationResult:
    """휴무 검증 결과 — Phase 3 ValidationResult 의 휴무 도메인 변형."""

    can_approve: bool = False
    issues: list[ValidationIssue] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    duplicate_existing_leave: dict[str, Any] | None = None  # 동일 날짜 기존 휴무
    conflicting_appointments: list[ConflictingAppointment] = field(default_factory=list)


@dataclass
class LeaveExecutionResult:
    """휴무 등록 실행 결과."""

    success: bool
    new_status: str
    result_payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    revalidation: LeaveValidationResult | None = None


# ────────────────────────────── Service callable Protocol ──────────────────────────────


class LeaveServiceCallable(Protocol):
    """기존 휴무 등록 service callable. router 가 주입.

    AI executor 는 본 callable 만 호출. 직접 SQL ⊥.
    """

    def __call__(
        self,
        *,
        therapist_id: str,
        leave_date: date,
        leave_type: str,  # "full" / "am" / "pm"
        memo: str | None,
        actor_user_id: str,
    ) -> dict[str, Any]: ...


# ────────────────────────────── 1. 휴무 유형 추출 ──────────────────────────────


def parse_leave_type_from_text(text: str) -> str | None:
    """자연어에서 휴무 유형 추출.

    "종일 휴무" / "연차" → "full"
    "오전반차" / "am 반차" → "am"
    "오후반차" / "pm 반차" → "pm"
    """
    if not text:
        return None
    t = text.replace(" ", "")
    if "오전반차" in t or "오전반" in t or re.search(r"am\s*반", text, re.IGNORECASE):
        return LEAVE_TYPE_AM
    if "오후반차" in t or "오후반" in t or re.search(r"pm\s*반", text, re.IGNORECASE):
        return LEAVE_TYPE_PM
    if "종일" in t or "연차" in t or "오프" in t or "휴무" in t:
        return LEAVE_TYPE_FULL
    return None


# ────────────────────────────── 2. 검증 helper ──────────────────────────────


def _check_therapist_active(session: Any, therapist_id: str) -> tuple[bool, str | None]:
    """치료사 존재 + 활성 상태 검사. (ok, name)."""
    from sqlalchemy import select

    from app.models.models import Employee

    row = session.execute(
        select(Employee).where(Employee.id == therapist_id)
    ).scalar_one_or_none()
    if row is None:
        return False, None
    if not row.active:
        return False, row.name
    return True, row.name


def _check_existing_leave(
    session: Any, *, therapist_id: str, leave_date: date
) -> dict[str, Any] | None:
    """동일 치료사 + 동일 날짜 기존 휴무 검사."""
    from sqlalchemy import select

    from app.models.models import EmployeeLeave

    row = session.execute(
        select(EmployeeLeave)
        .where(EmployeeLeave.employee_id == therapist_id)
        .where(EmployeeLeave.leave_date == leave_date.isoformat())
    ).scalar_one_or_none()
    if row is None:
        return None
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "leave_date": row.leave_date,
        "leave_type": row.leave_type,
    }


def _find_conflicting_appointments(
    session: Any,
    *,
    therapist_id: str,
    leave_date: date,
    leave_type: str,
) -> list[ConflictingAppointment]:
    """휴무 시간대와 겹치는 기존 예약 (status != 'canceled') 목록."""
    from sqlalchemy import select

    from app.models.models import Appointment

    day_start = datetime.combine(leave_date, time(0, 0))
    day_end = day_start + timedelta(days=1)

    rows = list(
        session.execute(
            select(Appointment)
            .where(Appointment.therapist_id == therapist_id)
            .where(Appointment.start_at >= day_start)
            .where(Appointment.start_at < day_end)
        ).scalars()
    )

    conflicts: list[ConflictingAppointment] = []
    for r in rows:
        if getattr(r, "status", None) == "canceled":
            continue
        appt_hour = r.start_at.hour
        # full → 모든 예약 충돌. am → 오전 (< 13), pm → 오후 (>= 13).
        if leave_type == LEAVE_TYPE_FULL:
            included = True
        elif leave_type == LEAVE_TYPE_AM:
            included = appt_hour < 13
        elif leave_type == LEAVE_TYPE_PM:
            included = appt_hour >= 13
        else:
            included = False
        if included:
            conflicts.append(
                ConflictingAppointment(
                    appointment_id=r.id,
                    patient_id=r.patient_id,
                    start_at=r.start_at,
                    end_at=r.end_at,
                )
            )
    return conflicts


# ────────────────────────────── 3. 검증 ──────────────────────────────


def validate_leave_candidate(
    session: Any,
    *,
    therapist_id: str | None,
    leave_date: date | None,
    leave_type: str | None,
    is_past_date: bool = False,
    allow_existing_appointment_conflict: bool = True,
) -> LeaveValidationResult:
    """휴무 등록 후보 검증.

    검증 항목:
    1. 치료사 / 날짜 / 휴무 유형 모두 확정
    2. 휴무 유형 유효 (full / am / pm)
    3. 치료사 존재 + 활성
    4. 같은 날짜 기존 휴무 없음 (있으면 차단 — 사용자가 기존 휴무 수정으로 대응)
    5. 과거 날짜 차단
    6. 충돌 예약은 *안내* 만 (allow_existing_appointment_conflict=True 가 기본 — § 5.3 "별도 고지")
    """
    result = LeaveValidationResult()

    if therapist_id is None:
        result.issues.append(ValidationIssue("치료사_미선택", "치료사가 선택되지 않았습니다."))
        result.checks["치료사 확정"] = False
    else:
        result.checks["치료사 확정"] = True

    if leave_date is None:
        result.issues.append(ValidationIssue("날짜_미확정", "휴무 날짜가 확정되지 않았습니다."))
        result.checks["날짜 확정"] = False
    else:
        result.checks["날짜 확정"] = True

    if leave_type is None or leave_type not in VALID_LEAVE_TYPES:
        result.issues.append(
            ValidationIssue("휴무유형_모호", "휴무 유형 (종일 / 오전반차 / 오후반차) 이 명확하지 않습니다.")
        )
        result.checks["휴무 유형 확정"] = False
    else:
        result.checks["휴무 유형 확정"] = True

    # 치료사 활성
    if therapist_id is not None:
        ok, name = _check_therapist_active(session, therapist_id)
        if not ok:
            result.issues.append(
                ValidationIssue(
                    "치료사_비활성",
                    f"치료사 '{name or therapist_id}' 가 비활성이거나 존재하지 않습니다.",
                )
            )
            result.checks["치료사 활성"] = False
        else:
            result.checks["치료사 활성"] = True

    # 기존 휴무 중복
    if therapist_id is not None and leave_date is not None:
        existing = _check_existing_leave(
            session, therapist_id=therapist_id, leave_date=leave_date
        )
        if existing is not None:
            result.duplicate_existing_leave = existing
            result.issues.append(
                ValidationIssue(
                    "휴무_중복",
                    f"같은 날짜에 이미 등록된 휴무가 있습니다 (유형: {existing['leave_type']}).",
                )
            )
            result.checks["기존 휴무 중복 없음"] = False
        else:
            result.checks["기존 휴무 중복 없음"] = True

    # 과거 날짜
    if is_past_date:
        result.issues.append(
            ValidationIssue("과거_날짜", "과거 날짜로 휴무 등록할 수 없습니다.", severity="error")
        )
        result.checks["과거 날짜 아님"] = False
    else:
        result.checks["과거 날짜 아님"] = True

    # 충돌 예약 (안내)
    if therapist_id is not None and leave_date is not None and leave_type in VALID_LEAVE_TYPES:
        conflicts = _find_conflicting_appointments(
            session,
            therapist_id=therapist_id,
            leave_date=leave_date,
            leave_type=leave_type,
        )
        result.conflicting_appointments = conflicts
        if conflicts:
            severity = "warning" if allow_existing_appointment_conflict else "error"
            result.issues.append(
                ValidationIssue(
                    "예약_충돌",
                    f"해당 시간대에 기존 예약 {len(conflicts)} 건이 있습니다 (별도 고지).",
                    severity=severity,
                )
            )
            result.checks["충돌 예약 없음"] = False
        else:
            result.checks["충돌 예약 없음"] = True

    # error 가 아닌 issue 만 있으면 승인 가능 (warning 은 통과)
    result.can_approve = not any(i.severity == "error" for i in result.issues)
    return result


# ────────────────────────────── 4. 실행 ──────────────────────────────


def execute_approved_leave(
    session: Any,
    *,
    therapist_id: str,
    leave_date: date,
    leave_type: str,
    memo: str | None,
    actor_user_id: str,
    leave_service: LeaveServiceCallable,
    is_past_date: bool = False,
    allow_existing_appointment_conflict: bool = True,
) -> LeaveExecutionResult:
    """승인된 휴무 명령을 Gate 2 재검증 후 service callable 로 실행."""
    revalidation = validate_leave_candidate(
        session,
        therapist_id=therapist_id,
        leave_date=leave_date,
        leave_type=leave_type,
        is_past_date=is_past_date,
        allow_existing_appointment_conflict=allow_existing_appointment_conflict,
    )

    if not revalidation.can_approve:
        return LeaveExecutionResult(
            success=False,
            new_status=AiCommandStatus.VALIDATION_FAILED.value,
            error_message="승인 직전 최종 재검증 실패",
            revalidation=revalidation,
        )

    try:
        result = leave_service(
            therapist_id=therapist_id,
            leave_date=leave_date,
            leave_type=leave_type,
            memo=memo,
            actor_user_id=actor_user_id,
        )
    except Exception as e:  # noqa: BLE001
        return LeaveExecutionResult(
            success=False,
            new_status=AiCommandStatus.FAILED.value,
            error_message=f"휴무 service 호출 실패: {e}",
            revalidation=revalidation,
        )

    return LeaveExecutionResult(
        success=True,
        new_status=AiCommandStatus.EXECUTED.value,
        result_payload=result,
        revalidation=revalidation,
    )


# ────────────────────────────── 5. preview ──────────────────────────────


# ────────────────────────────── 통합 파이프라인 (parse + resolve + validate + preview) ──────────────────────────────


@dataclass
class LeaveRunResult:
    """run_leave_pipeline 결과 — UI / audit 직렬화용."""

    raw_text: str
    leave_type: str | None
    leave_date: date | None
    leave_date_text: str | None
    therapist_id: str | None
    therapist_name: str | None
    therapist_candidates: list[dict[str, Any]] = field(default_factory=list)
    therapist_not_found: bool = False
    validation: LeaveValidationResult | None = None
    preview: dict[str, Any] | None = None
    status: str = AiCommandStatus.PARSED.value


def run_leave_pipeline(
    db_session: Any,
    *,
    raw_text: str,
    current_calendar_year: int,
    current_calendar_month: int,
    today: date | None = None,
    selected_therapist_id: str | None = None,
) -> LeaveRunResult:
    """create_leave 통합 read-only 파이프라인.

    1) parse_leave_type_from_text → leave_type
    2) ai_parser._extract_therapist_name + ai_resolver.resolve_therapist
    3) ai_parser._extract_date_text + ai_resolver.resolve_date
    4) validate_leave_candidate
    5) build_leave_preview

    DB 직접 수정 0. 외부 AI API 호출 0 — 정규식 기반.
    """
    from app.ai.ai_parser import _extract_date_text, _extract_therapist_name
    from app.ai.ai_resolver import resolve_date, resolve_therapist

    # 1. leave_type 추출
    leave_type = parse_leave_type_from_text(raw_text)

    # 2. 치료사
    therapist_text = _extract_therapist_name(raw_text)
    therapist_res = resolve_therapist(db_session, therapist_name=therapist_text)
    therapist_id: str | None = None
    therapist_name: str | None = None
    therapist_candidates: list[dict[str, Any]] = []
    therapist_not_found = False

    if therapist_res.therapist_id and not therapist_res.candidates:
        therapist_id = therapist_res.therapist_id
        therapist_name = therapist_res.therapist_name
    elif therapist_res.candidates:
        therapist_candidates = therapist_res.candidates
        # 동명 치료사 + selected_therapist_id 가 있으면 확정
        if selected_therapist_id:
            for c in therapist_res.candidates:
                if c.get("id") == selected_therapist_id:
                    therapist_id = selected_therapist_id
                    therapist_name = c.get("name")
                    break
    elif therapist_res.not_found:
        therapist_not_found = True

    # 3. 날짜
    date_text = _extract_date_text(raw_text)
    date_res = resolve_date(
        date_text,
        current_calendar_year=current_calendar_year,
        current_calendar_month=current_calendar_month,
        today=today,
    )

    # 4. 검증 — 치료사 / 날짜 / 휴무 유형 모두 확정 시
    validation: LeaveValidationResult | None = None
    preview: dict[str, Any] | None = None
    if therapist_id and date_res.resolved_date and leave_type:
        validation = validate_leave_candidate(
            db_session,
            therapist_id=therapist_id,
            leave_date=date_res.resolved_date,
            leave_type=leave_type,
            is_past_date=date_res.is_past,
        )
        preview = build_leave_preview(
            therapist_id=therapist_id,
            therapist_name=therapist_name,
            leave_date=date_res.resolved_date,
            leave_type=leave_type,
            validation=validation,
        )

    # 5. status 결정
    if therapist_not_found:
        status = AiCommandStatus.NEEDS_CLARIFICATION.value
    elif therapist_candidates and not therapist_id:
        status = AiCommandStatus.PATIENT_SELECTION_REQUIRED.value  # 치료사 다중 후보 — UI 가 선택 필요로 인식
    elif not therapist_id or not date_res.resolved_date or not leave_type:
        status = AiCommandStatus.NEEDS_CLARIFICATION.value
    elif validation and validation.can_approve:
        status = AiCommandStatus.NEEDS_APPROVAL.value
    else:
        status = AiCommandStatus.VALIDATION_FAILED.value

    return LeaveRunResult(
        raw_text=raw_text,
        leave_type=leave_type,
        leave_date=date_res.resolved_date,
        leave_date_text=date_text,
        therapist_id=therapist_id,
        therapist_name=therapist_name,
        therapist_candidates=therapist_candidates,
        therapist_not_found=therapist_not_found,
        validation=validation,
        preview=preview,
        status=status,
    )


def build_leave_preview(
    *,
    therapist_id: str | None,
    therapist_name: str | None,
    leave_date: date | None,
    leave_type: str | None,
    validation: LeaveValidationResult,
    memo: str | None = None,
) -> dict[str, Any]:
    """휴무 등록 후보 카드 — 충돌 예약 별도 표시 (§ 5.3)."""
    leave_type_display = {
        LEAVE_TYPE_FULL: "종일 휴무",
        LEAVE_TYPE_AM: "오전반차",
        LEAVE_TYPE_PM: "오후반차",
    }.get(leave_type or "", "(미정)")

    return {
        "kind": "leave_preview",
        "title": "휴무 등록 후보",
        "fields": {
            "therapist_id": therapist_id,
            "therapist_name": therapist_name,
            "leave_date": leave_date.isoformat() if leave_date else None,
            "leave_type": leave_type,
            "leave_type_display": leave_type_display,
            "memo": memo,
        },
        "validation": {
            "can_approve": validation.can_approve,
            "checks": validation.checks,
            "issues": [
                {"code": i.code, "message": i.message, "severity": i.severity}
                for i in validation.issues
            ],
        },
        "duplicate_existing_leave": validation.duplicate_existing_leave,
        "conflicting_appointments": [
            {
                "appointment_id": c.appointment_id,
                "patient_id": c.patient_id,
                "start_at": c.start_at.isoformat(),
                "end_at": c.end_at.isoformat(),
            }
            for c in validation.conflicting_appointments
        ],
        "approval_disabled": not validation.can_approve,
        "actions": ["취소", "휴무 등록"],
        "prompt": "이 휴무를 등록하시겠습니까?",
    }
