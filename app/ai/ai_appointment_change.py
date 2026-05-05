"""ai_appointment_change — Phase 7 예약 변경 / 취소 AI.

역할:
- intent: `update_appointment`, `cancel_appointment`
- 대상 예약 식별 (환자 + 날짜 + 시간 → Appointment row)
- 변경 전·후 비교 (diff)
- 취소: 기존 취소 상태 처리 로직 호출 (**물리 삭제 금지** — service callable 이 status='canceled' 변경)
- 승인 후 실행 (Gate 1 + Gate 2)

설계:
- 본 모듈은 **DB 직접 수정 금지** (read-only resolver / preview / diff + service callable 호출).
- service callable Protocol — caller (router) 가 기존 예약 변경 / 취소 service 주입.
- AI executor 와 동일한 의존성 역전 패턴.
- Phase 5 의 `validate_appointment_candidate(..., exclude_appointment_id=...)` 활용
  (자기 자신과의 시간 충돌 회피).

cross-reference:
- 13 필드 정의 → AI_FEATURE_MASTER_PLAN.md § 5.2 (update_appointment / cancel_appointment)
- Gate 1 / Gate 2 → AI_SAFETY_POLICY.md § 4
- 취소는 물리 삭제 금지 → AI_SAFETY_POLICY.md § 1.1 + AI_FEATURE_MASTER_PLAN § 5.2
- 변경 전·후 비교 → AI_IMPLEMENTATION_PHASES.md § Phase 7

하네스: tests/test_phase07_ai_update_cancel.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol

from app.ai.ai_command_schema import AiCommandStatus, TreatmentItem
from app.ai.ai_validator import (
    ValidationIssue,
    ValidationResult,
    validate_appointment_candidate,
)


# ────────────────────────────── 결과 데이터 ──────────────────────────────


@dataclass
class TargetAppointment:
    """대상 예약 1건 — 변경 / 취소 대상."""

    appointment_id: str
    patient_id: str
    therapist_id: str | None
    start_at: datetime
    end_at: datetime
    status: str
    treatment_codes: list[str] = field(default_factory=list)


@dataclass
class TargetResolution:
    """대상 예약 해결 결과.

    candidates 1건 → 자동 확정 (target).
    candidates 다수 → 사용자 선택 필요 (target=None).
    not_found → 대상 없음 (취소 / 변경 불가).
    """

    target: TargetAppointment | None = None
    candidates: list[TargetAppointment] = field(default_factory=list)
    not_found: bool = False


@dataclass
class AppointmentDiff:
    """변경 전·후 비교."""

    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class ChangeExecutionResult:
    """update / cancel 실행 결과 — Phase 5 ExecutionResult 와 동일 패턴."""

    success: bool
    new_status: str
    result_payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    revalidation: ValidationResult | None = None
    diff: AppointmentDiff | None = None


# ────────────────────────────── Service callable Protocol ──────────────────────────────


class AppointmentUpdateServiceCallable(Protocol):
    """기존 예약 변경 service callable. router 가 주입.

    AI executor 는 본 callable 만 호출. 직접 SQL 금지.
    """

    def __call__(
        self,
        *,
        appointment_id: str,
        therapist_id: str | None,
        target_date: date,
        start_hour: int,
        start_minute: int,
        duration_min: int,
        treatment_codes: list[str],
        memo: str | None,
        actor_user_id: str,
    ) -> dict[str, Any]: ...


class AppointmentCancelServiceCallable(Protocol):
    """기존 예약 취소 service callable. router 가 주입.

    물리 삭제 금지 — service callable 이 status='canceled' 변경.
    """

    def __call__(
        self,
        *,
        appointment_id: str,
        reason: str | None,
        actor_user_id: str,
    ) -> dict[str, Any]: ...


# ────────────────────────────── 1. 대상 예약 식별 ──────────────────────────────


def resolve_target_appointment(
    session: Any,
    *,
    patient_id: str | None,
    target_date: date | None,
    start_hour: int | None,
    start_minute: int = 0,
) -> TargetResolution:
    """환자 + 날짜 + (선택) 시간 → 단일 Appointment 검색.

    - 시간 명시: 같은 시간대 시작 예약 1건 검색.
    - 시간 누락: 같은 날짜 환자 예약 모두 → candidates.
    - 환자 누락 / 날짜 누락 → not_found.
    - status='canceled' 예약은 자동 제외.
    """
    if patient_id is None or target_date is None:
        return TargetResolution(not_found=True)

    from sqlalchemy import select

    from app.models.models import Appointment

    day_start = datetime.combine(target_date, time(0, 0))
    day_end = day_start + timedelta(days=1)

    rows = list(
        session.execute(
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .where(Appointment.start_at >= day_start)
            .where(Appointment.start_at < day_end)
        ).scalars()
    )

    # canceled 제외
    rows = [r for r in rows if getattr(r, "status", None) != "canceled"]

    candidates = [_to_target(r) for r in rows]

    # 시간 명시 시 정확 매칭 (시:분 동일) — 매칭 실패 시 자동 fallback 금지 (다른 시간 예약을 임의 확정 ⊥)
    if start_hour is not None:
        target_start = datetime.combine(target_date, time(start_hour, start_minute))
        exact = [c for c in candidates if c.start_at == target_start]
        if not exact:
            return TargetResolution(not_found=True)
        if len(exact) == 1:
            return TargetResolution(target=exact[0], candidates=exact)
        return TargetResolution(candidates=exact)

    # 시간 미명시 — 같은 날 환자 예약 전체 후보 반환
    if not candidates:
        return TargetResolution(not_found=True)
    if len(candidates) == 1:
        return TargetResolution(target=candidates[0], candidates=candidates)
    return TargetResolution(candidates=candidates)


def _to_target(row: Any) -> TargetAppointment:
    import json

    codes_raw = getattr(row, "treatment_codes", None) or "[]"
    try:
        codes = json.loads(codes_raw) if isinstance(codes_raw, str) else list(codes_raw)
    except (json.JSONDecodeError, TypeError):
        codes = []
    return TargetAppointment(
        appointment_id=row.id,
        patient_id=row.patient_id,
        therapist_id=row.therapist_id,
        start_at=row.start_at,
        end_at=row.end_at,
        status=getattr(row, "status", "reserved"),
        treatment_codes=codes,
    )


# ────────────────────────────── 2. 변경 전·후 비교 (diff) ──────────────────────────────


def build_appointment_diff(
    *,
    before: TargetAppointment,
    new_therapist_id: str | None = None,
    new_target_date: date | None = None,
    new_start_hour: int | None = None,
    new_start_minute: int | None = None,
    new_duration_min: int | None = None,
    new_treatment_codes: list[str] | None = None,
    new_memo: str | None = None,
) -> AppointmentDiff:
    """변경 전·후 비교 카드 데이터 생성.

    None 으로 들어온 필드는 변경 없음 — diff 의 changed_fields 에 포함하지 않음.
    """
    before_dict: dict[str, Any] = {
        "appointment_id": before.appointment_id,
        "patient_id": before.patient_id,
        "therapist_id": before.therapist_id,
        "start_at": before.start_at.isoformat(),
        "end_at": before.end_at.isoformat(),
        "treatment_codes": before.treatment_codes,
    }
    after_dict: dict[str, Any] = dict(before_dict)
    changed: list[str] = []

    if new_therapist_id is not None and new_therapist_id != before.therapist_id:
        after_dict["therapist_id"] = new_therapist_id
        changed.append("therapist_id")

    new_date = new_target_date or before.start_at.date()
    new_h = new_start_hour if new_start_hour is not None else before.start_at.hour
    new_m = new_start_minute if new_start_minute is not None else before.start_at.minute
    new_start = datetime.combine(new_date, time(new_h, new_m))
    if new_start != before.start_at:
        after_dict["start_at"] = new_start.isoformat()
        if "target_date" not in changed and new_date != before.start_at.date():
            changed.append("target_date")
        if new_h != before.start_at.hour or new_m != before.start_at.minute:
            changed.append("start_time")

    duration_existing = int((before.end_at - before.start_at).total_seconds() // 60)
    new_dur = new_duration_min if new_duration_min is not None else duration_existing
    new_end = new_start + timedelta(minutes=new_dur)
    if new_end != before.end_at:
        after_dict["end_at"] = new_end.isoformat()
        if "duration_min" not in changed and new_dur != duration_existing:
            changed.append("duration_min")

    if new_treatment_codes is not None and sorted(new_treatment_codes) != sorted(
        before.treatment_codes
    ):
        after_dict["treatment_codes"] = new_treatment_codes
        changed.append("treatment_codes")

    if new_memo is not None:
        after_dict["memo"] = new_memo
        changed.append("memo")

    return AppointmentDiff(before=before_dict, after=after_dict, changed_fields=changed)


# ────────────────────────────── 3. update 검증 + 실행 ──────────────────────────────


def validate_update_appointment(
    session: Any,
    *,
    target: TargetAppointment,
    new_therapist_id: str | None = None,
    new_target_date: date | None = None,
    new_start_hour: int | None = None,
    new_start_minute: int | None = None,
    new_duration_min: int | None = None,
    new_treatment_items: list[TreatmentItem] | None = None,
    is_past_date: bool = False,
) -> ValidationResult:
    """변경 후보 검증.

    - 변경 후 시간 / 치료사로 validate_appointment_candidate 호출 (자기 자신은 exclude).
    - new_treatment_items 미지정 시 기존 treatment_codes 를 db_verified 로 사용 (재검증).
    """
    therapist_id = (
        new_therapist_id if new_therapist_id is not None else target.therapist_id
    )
    target_date_eff = new_target_date or target.start_at.date()
    start_hour_eff = (
        new_start_hour if new_start_hour is not None else target.start_at.hour
    )
    start_minute_eff = (
        new_start_minute if new_start_minute is not None else target.start_at.minute
    )
    duration_existing = int((target.end_at - target.start_at).total_seconds() // 60)
    duration_eff = new_duration_min if new_duration_min is not None else duration_existing

    # treatment_items 미지정 시 기존 codes 를 db_verified 로 변환 (검증만 통과)
    if new_treatment_items is None:
        from app.ai.ai_command_schema import (
            DataSourceState,
            TreatmentItem,
            TreatmentItemStatus,
        )

        new_treatment_items = [
            TreatmentItem(
                raw_text=code,
                matched_treatment_id=code,
                matched_treatment_name=code,
                source=DataSourceState.DB_VERIFIED,
                status=TreatmentItemStatus.DB_VERIFIED,
            )
            for code in target.treatment_codes
        ]

    return validate_appointment_candidate(
        session,
        patient_id=target.patient_id,
        therapist_id=therapist_id,
        target_date=target_date_eff,
        start_hour=start_hour_eff,
        start_minute=start_minute_eff,
        duration_min=duration_eff,
        treatment_items=new_treatment_items,
        is_past_date=is_past_date,
        exclude_appointment_id=target.appointment_id,
    )


def execute_approved_update_appointment(
    session: Any,
    *,
    target: TargetAppointment,
    new_therapist_id: str | None = None,
    new_target_date: date | None = None,
    new_start_hour: int | None = None,
    new_start_minute: int | None = None,
    new_duration_min: int | None = None,
    new_treatment_items: list[TreatmentItem] | None = None,
    new_treatment_codes: list[str] | None = None,
    new_memo: str | None = None,
    actor_user_id: str,
    update_service: AppointmentUpdateServiceCallable,
    is_past_date: bool = False,
) -> ChangeExecutionResult:
    """승인된 변경 명령을 Gate 2 재검증 후 service callable 로 실행.

    DB 직접 수정 0 — update_service 가 UPDATE 담당.
    """
    revalidation = validate_update_appointment(
        session,
        target=target,
        new_therapist_id=new_therapist_id,
        new_target_date=new_target_date,
        new_start_hour=new_start_hour,
        new_start_minute=new_start_minute,
        new_duration_min=new_duration_min,
        new_treatment_items=new_treatment_items,
        is_past_date=is_past_date,
    )

    diff = build_appointment_diff(
        before=target,
        new_therapist_id=new_therapist_id,
        new_target_date=new_target_date,
        new_start_hour=new_start_hour,
        new_start_minute=new_start_minute,
        new_duration_min=new_duration_min,
        new_treatment_codes=(
            new_treatment_codes
            or (
                [
                    ti.matched_treatment_id
                    for ti in (new_treatment_items or [])
                    if ti.matched_treatment_id
                ]
                or None
            )
        ),
        new_memo=new_memo,
    )

    if not revalidation.can_approve:
        return ChangeExecutionResult(
            success=False,
            new_status=AiCommandStatus.VALIDATION_FAILED.value,
            error_message="승인 직전 최종 재검증 실패 (변경 후 충돌)",
            revalidation=revalidation,
            diff=diff,
        )

    if not diff.changed_fields:
        return ChangeExecutionResult(
            success=False,
            new_status=AiCommandStatus.VALIDATION_FAILED.value,
            error_message="변경 사항이 없습니다.",
            revalidation=revalidation,
            diff=diff,
        )

    # 실제 service 호출 인자 결정
    therapist_id_eff = (
        new_therapist_id if new_therapist_id is not None else target.therapist_id
    )
    target_date_eff = new_target_date or target.start_at.date()
    start_hour_eff = (
        new_start_hour if new_start_hour is not None else target.start_at.hour
    )
    start_minute_eff = (
        new_start_minute if new_start_minute is not None else target.start_at.minute
    )
    duration_existing = int((target.end_at - target.start_at).total_seconds() // 60)
    duration_eff = new_duration_min if new_duration_min is not None else duration_existing
    codes_eff = new_treatment_codes or (
        [
            ti.matched_treatment_id
            for ti in (new_treatment_items or [])
            if ti.matched_treatment_id
        ]
        or target.treatment_codes
    )

    try:
        result = update_service(
            appointment_id=target.appointment_id,
            therapist_id=therapist_id_eff,
            target_date=target_date_eff,
            start_hour=start_hour_eff,
            start_minute=start_minute_eff,
            duration_min=duration_eff,
            treatment_codes=codes_eff,
            memo=new_memo,
            actor_user_id=actor_user_id,
        )
    except Exception as e:  # noqa: BLE001
        return ChangeExecutionResult(
            success=False,
            new_status=AiCommandStatus.FAILED.value,
            error_message=f"예약 변경 service 호출 실패: {e}",
            revalidation=revalidation,
            diff=diff,
        )

    return ChangeExecutionResult(
        success=True,
        new_status=AiCommandStatus.EXECUTED.value,
        result_payload=result,
        revalidation=revalidation,
        diff=diff,
    )


# ────────────────────────────── 4. cancel 검증 + 실행 ──────────────────────────────


def validate_cancel_appointment(target: TargetAppointment | None) -> ValidationResult:
    """취소 검증 — 대상 단일 확정 + 이미 취소된 예약 차단."""
    result = ValidationResult()
    if target is None:
        result.issues.append(
            ValidationIssue("대상_미확정", "취소할 예약을 식별할 수 없습니다.")
        )
        result.checks["대상 예약 확정"] = False
        result.can_approve = False
        return result
    result.checks["대상 예약 확정"] = True
    if target.status == "canceled":
        result.issues.append(
            ValidationIssue("이미_취소됨", "이미 취소된 예약입니다.", severity="error")
        )
        result.checks["취소 가능 상태"] = False
        result.can_approve = False
        return result
    result.checks["취소 가능 상태"] = True
    result.can_approve = True
    return result


def execute_approved_cancel_appointment(
    *,
    target: TargetAppointment,
    reason: str | None,
    actor_user_id: str,
    cancel_service: AppointmentCancelServiceCallable,
) -> ChangeExecutionResult:
    """승인된 취소 명령을 service callable 로 실행.

    물리 삭제 금지 — cancel_service 가 status='canceled' 변경 담당.
    """
    revalidation = validate_cancel_appointment(target)
    if not revalidation.can_approve:
        return ChangeExecutionResult(
            success=False,
            new_status=AiCommandStatus.VALIDATION_FAILED.value,
            error_message="취소 불가",
            revalidation=revalidation,
        )

    try:
        result = cancel_service(
            appointment_id=target.appointment_id,
            reason=reason,
            actor_user_id=actor_user_id,
        )
    except Exception as e:  # noqa: BLE001
        return ChangeExecutionResult(
            success=False,
            new_status=AiCommandStatus.FAILED.value,
            error_message=f"예약 취소 service 호출 실패: {e}",
            revalidation=revalidation,
        )

    return ChangeExecutionResult(
        success=True,
        new_status=AiCommandStatus.EXECUTED.value,
        result_payload=result,
        revalidation=revalidation,
    )


# ────────────────────────────── 5. preview ──────────────────────────────


def build_update_preview(
    *,
    diff: AppointmentDiff,
    validation: ValidationResult,
) -> dict[str, Any]:
    """변경 후보 카드 — 변경 전·후 + 검증 결과."""
    return {
        "kind": "appointment_update_preview",
        "title": "예약 변경 후보",
        "diff": {
            "before": diff.before,
            "after": diff.after,
            "changed_fields": diff.changed_fields,
        },
        "validation": {
            "can_approve": validation.can_approve,
            "checks": validation.checks,
            "issues": [
                {"code": i.code, "message": i.message, "severity": i.severity}
                for i in validation.issues
            ],
        },
        "approval_disabled": (not validation.can_approve) or not diff.changed_fields,
        "actions": ["취소", "예약 변경"],
        "prompt": "변경 사항을 확인하고 승인하시겠습니까?",
    }


def build_cancel_preview(
    *,
    target: TargetAppointment | None,
    validation: ValidationResult,
    reason: str | None = None,
) -> dict[str, Any]:
    """취소 후보 카드."""
    return {
        "kind": "appointment_cancel_preview",
        "title": "예약 취소 후보",
        "appointment": (
            {
                "appointment_id": target.appointment_id,
                "patient_id": target.patient_id,
                "therapist_id": target.therapist_id,
                "start_at": target.start_at.isoformat(),
                "end_at": target.end_at.isoformat(),
                "status": target.status,
                "treatment_codes": target.treatment_codes,
            }
            if target
            else None
        ),
        "reason": reason,
        "validation": {
            "can_approve": validation.can_approve,
            "checks": validation.checks,
            "issues": [
                {"code": i.code, "message": i.message, "severity": i.severity}
                for i in validation.issues
            ],
        },
        "approval_disabled": not validation.can_approve,
        "actions": ["취소", "예약 취소"],
        "prompt": "이 예약을 취소하시겠습니까?",
    }
