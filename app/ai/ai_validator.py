"""ai_validator — 예약 가능 여부 검증 (Phase 3).

역할:
- 휴무 / 반차 / 예약 중복 / 시간 겹침 / 권한 검증
- 신환 등록 중복 검사 (차트번호 / 이름+생년월일 / 이름+연락처 / 연락처)
- 치료항목 다중 선택 / alias 충돌 검증
- 승인 가능 / 불가능 판단

주의:
- 본 모듈은 **read-only**. DB INSERT / UPDATE / DELETE 없음.
- 검증 결과는 ValidationResult 로 반환. caller 가 승인 화면 / needs_clarification 결정.
- AI executor 는 Phase 5 에서 본 검증 결과를 다시 호출 (승인 직전 최종 재검증).

cross-reference:
- 휴무 / 반차 검증 → AI_FEATURE_MASTER_PLAN.md § 6.2 (8 단계)
- 신환 등록 중복 검사 → AI_FEATURE_MASTER_PLAN.md § 10.1 (8 단계)
- 치료항목 alias 충돌 → AI_FEATURE_MASTER_PLAN.md § 11

하네스: tests/test_phase03_ai_validator_preview.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol

from app.ai.ai_command_schema import TreatmentItem, TreatmentItemStatus


# ────────────────────────────── 결과 데이터 ──────────────────────────────


@dataclass
class ValidationIssue:
    """검증 실패 항목 1건."""

    code: str  # "휴무_충돌" / "시간_겹침" / "치료항목_미확정" 등
    message: str
    severity: str = "error"  # error / warning


@dataclass
class ValidationResult:
    """예약 후보 검증 결과.

    can_approve=True 시 승인 가능. False 시 issues 안내 후 사용자 선택 / 수정 필요.
    """

    can_approve: bool = False
    issues: list[ValidationIssue] = field(default_factory=list)
    # 검증한 항목별 ok / fail 표시 (UI 체크리스트용)
    checks: dict[str, bool] = field(default_factory=dict)


@dataclass
class NewPatientDuplicateCheck:
    """신환 등록 중복 검사 결과."""

    has_duplicates: bool = False
    chart_no_duplicate: list[dict[str, Any]] = field(default_factory=list)
    name_birth_duplicate: list[dict[str, Any]] = field(default_factory=list)
    name_phone_duplicate: list[dict[str, Any]] = field(default_factory=list)
    phone_duplicate: list[dict[str, Any]] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)


# ────────────────────────────── DB 의존성 ──────────────────────────────


class DBSession(Protocol):
    def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any: ...


# ────────────────────────────── 예약 후보 검증 ──────────────────────────────


def validate_appointment_candidate(
    session: DBSession,
    *,
    patient_id: str | None,
    therapist_id: str | None,
    target_date: date | None,
    start_hour: int | None,
    start_minute: int = 0,
    duration_min: int = 30,
    treatment_items: list[TreatmentItem] | None = None,
    is_past_date: bool = False,
    exclude_appointment_id: str | None = None,
) -> ValidationResult:
    """예약 후보 종합 검증.

    검증 항목:
    1. 환자 / 치료사 / 날짜 / 시간 모두 확정
    2. 치료항목 모두 db_verified (alias 충돌 / 미확정 없음)
    3. 휴무 / 반차 충돌 없음
    4. 같은 치료사 시간 겹침 없음
    5. 과거 날짜 차단
    """
    result = ValidationResult()
    treatment_items = treatment_items or []

    # 1) 필수값
    if patient_id is None:
        result.issues.append(ValidationIssue("환자_미선택", "환자가 선택되지 않았습니다."))
        result.checks["환자 확인됨"] = False
    else:
        result.checks["환자 확인됨"] = True

    if target_date is None:
        result.issues.append(ValidationIssue("날짜_미확정", "날짜가 확정되지 않았습니다."))
        result.checks["날짜 확정"] = False
    else:
        result.checks["날짜 확정"] = True

    if start_hour is None:
        result.issues.append(ValidationIssue("시간_미확정", "시간이 확정되지 않았습니다."))
        result.checks["시간 확정"] = False
    else:
        result.checks["시간 확정"] = True

    # 2) 치료항목 — 하나라도 db_verified 가 아니면 승인 불가
    if not treatment_items:
        result.issues.append(ValidationIssue("치료항목_미선택", "치료항목이 선택되지 않았습니다."))
        result.checks["치료항목 확인됨"] = False
    else:
        unverified = [
            ti for ti in treatment_items if ti.status != TreatmentItemStatus.DB_VERIFIED
        ]
        if unverified:
            for ti in unverified:
                if ti.status == TreatmentItemStatus.ALIAS_CONFLICT:
                    result.issues.append(
                        ValidationIssue(
                            "치료항목_alias_충돌",
                            f"'{ti.raw_text}' 가 여러 치료항목과 일치합니다. 선택해주세요.",
                        )
                    )
                elif ti.status == TreatmentItemStatus.NOT_FOUND:
                    result.issues.append(
                        ValidationIssue(
                            "치료항목_없음",
                            f"'{ti.raw_text}' 에 해당하는 치료항목이 DB 에 없습니다.",
                        )
                    )
                else:
                    result.issues.append(
                        ValidationIssue(
                            "치료항목_미확정",
                            f"'{ti.raw_text}' 의 치료항목을 선택해주세요.",
                        )
                    )
            result.checks["치료항목 확인됨"] = False
        else:
            result.checks["치료항목 확인됨"] = True

    # 3) 과거 날짜
    if is_past_date:
        result.issues.append(
            ValidationIssue("과거_날짜", "과거 날짜로 예약할 수 없습니다.", severity="error")
        )
        result.checks["과거 날짜 아님"] = False
    else:
        result.checks["과거 날짜 아님"] = True

    # 4) 휴무 / 반차 충돌 (치료사 + 날짜 모두 확정 시)
    if therapist_id and target_date and start_hour is not None:
        leave_conflict = _check_leave_conflict(
            session, therapist_id=therapist_id, target_date=target_date, start_hour=start_hour
        )
        if leave_conflict:
            result.issues.append(
                ValidationIssue("휴무_충돌", f"치료사 휴무 / 반차 와 충돌: {leave_conflict}")
            )
            result.checks["휴무/반차 충돌 없음"] = False
        else:
            result.checks["휴무/반차 충돌 없음"] = True

    # 5) 시간 겹침 (치료사 + 날짜 + 시간 모두 확정 시)
    if therapist_id and target_date and start_hour is not None:
        overlap = _check_time_overlap(
            session,
            therapist_id=therapist_id,
            target_date=target_date,
            start_hour=start_hour,
            start_minute=start_minute,
            duration_min=duration_min,
            exclude_appointment_id=exclude_appointment_id,
        )
        if overlap:
            result.issues.append(
                ValidationIssue("시간_겹침", f"같은 치료사 시간대에 다른 예약: {overlap}")
            )
            result.checks["중복 예약 없음"] = False
            result.checks["시간 겹침 없음"] = False
        else:
            result.checks["중복 예약 없음"] = True
            result.checks["시간 겹침 없음"] = True

    # 모든 issue 가 error 가 아니어야 승인 가능
    result.can_approve = not any(i.severity == "error" for i in result.issues)
    return result


def _check_leave_conflict(
    session: DBSession, *, therapist_id: str, target_date: date, start_hour: int
) -> str | None:
    """치료사 휴무 / 반차 충돌 확인."""
    from sqlalchemy import select

    from app.models.models import EmployeeLeave

    rows = list(
        session.execute(
            select(EmployeeLeave)
            .where(EmployeeLeave.employee_id == therapist_id)
            .where(EmployeeLeave.leave_date == target_date.isoformat())
        ).scalars()
    )
    for row in rows:
        if row.leave_type == "full":
            return "종일 휴무"
        if row.leave_type == "am" and start_hour < 13:
            return "오전반차"
        if row.leave_type == "pm" and start_hour >= 13:
            return "오후반차"
    return None


def _check_time_overlap(
    session: DBSession,
    *,
    therapist_id: str,
    target_date: date,
    start_hour: int,
    start_minute: int = 0,
    duration_min: int = 30,
    exclude_appointment_id: str | None = None,
) -> str | None:
    """같은 치료사의 같은 날짜 시간 겹침 확인.

    exclude_appointment_id 가 주어지면 해당 예약은 검사에서 제외 (Phase 7 update 시 자기 자신과의
    충돌 회피). 또한 status='canceled' 예약은 자동 제외 (이미 취소된 예약).
    """
    from sqlalchemy import select

    from app.models.models import Appointment

    target_start = datetime.combine(target_date, time(start_hour, start_minute))
    target_end = target_start + timedelta(minutes=duration_min)

    day_start = datetime.combine(target_date, time(0, 0))
    day_end = day_start + timedelta(days=1)

    rows = list(
        session.execute(
            select(Appointment)
            .where(Appointment.therapist_id == therapist_id)
            .where(Appointment.start_at >= day_start)
            .where(Appointment.start_at < day_end)
        ).scalars()
    )
    for row in rows:
        if exclude_appointment_id and row.id == exclude_appointment_id:
            continue
        if getattr(row, "status", None) == "canceled":
            continue
        # 겹침: target_start < row.end_at AND row.start_at < target_end
        if target_start < row.end_at and row.start_at < target_end:
            return f"{row.start_at.strftime('%H:%M')} - {row.end_at.strftime('%H:%M')}"
    return None


# ────────────────────────────── 신환 등록 중복 검사 ──────────────────────────────


def check_new_patient_duplicates(
    session: DBSession,
    *,
    chart_no: str | None,
    name: str | None,
    birth_date: str | None,
    phone: str | None,
) -> NewPatientDuplicateCheck:
    """신환 등록 시 중복 의심 환자 검색 (AI_FEATURE_MASTER_PLAN § 10.1 8단계).

    중복 검사:
    - 차트번호 동일
    - 이름 + 생년월일 동일
    - 이름 + 연락처 동일
    - 연락처 동일
    필수값 누락도 함께 체크.
    """
    from sqlalchemy import select

    from app.models.models import Patient

    result = NewPatientDuplicateCheck()

    # 필수값 검사
    if not name:
        result.missing_required.append("이름")
    if not chart_no:
        result.missing_required.append("차트번호")

    # 차트번호 중복
    if chart_no:
        rows = list(
            session.execute(select(Patient).where(Patient.chart_no == chart_no)).scalars()
        )
        if rows:
            result.chart_no_duplicate = [_patient_dict(p) for p in rows]

    # 이름 + 생년월일 중복
    if name and birth_date:
        rows = list(
            session.execute(
                select(Patient)
                .where(Patient.name == name)
                .where(Patient.birth_date == birth_date)
            ).scalars()
        )
        if rows:
            result.name_birth_duplicate = [_patient_dict(p) for p in rows]

    # 이름 + 연락처 중복
    if name and phone:
        rows = list(
            session.execute(
                select(Patient).where(Patient.name == name).where(Patient.phone == phone)
            ).scalars()
        )
        if rows:
            result.name_phone_duplicate = [_patient_dict(p) for p in rows]

    # 연락처 중복
    if phone:
        rows = list(session.execute(select(Patient).where(Patient.phone == phone)).scalars())
        if rows:
            result.phone_duplicate = [_patient_dict(p) for p in rows]

    result.has_duplicates = bool(
        result.chart_no_duplicate
        or result.name_birth_duplicate
        or result.name_phone_duplicate
        or result.phone_duplicate
    )
    return result


def _patient_dict(p: Any) -> dict[str, Any]:
    return {
        "id": p.id,
        "chart_no": p.chart_no,
        "name": p.name,
        "birth_date": p.birth_date,
        "phone": p.phone,
    }
