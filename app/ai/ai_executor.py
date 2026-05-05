"""ai_executor — 사용자가 승인한 AI 명령만 기존 service 로 실행 (Phase 5).

역할:
- Gate 2 (승인 직전 최종 재검증) 수행
- 재검증 통과 시 caller 가 주입한 기존 service callable 호출 (직접 DB 조작 금지)
- 신환 등록 service 호출 + 예약 등록 service 호출 (각각 별도 로그)
- 실패 / 성공 모두 audit log 기록

주의:
- 본 모듈은 **DB 직접 수정 금지**. 기존 도메인 service 의 callable 을 인자로 받음
  (의존성 역전 — 본 모듈이 service.py / repository.py 를 직접 import 하지 않음).
- 외부 AI API 호출 0.
- 승인 직전 최종 재검증 미통과 시 service 호출 안 함.

cross-reference:
- 승인형 실행 게이트 → AI_SAFETY_POLICY.md § 4 (Gate 1, Gate 2)
- 호출해야 할 기존 service → AI_COMMAND_ARCHITECTURE.md § 8
- 별도 로그 → AI_FEATURE_MASTER_PLAN.md § 10.2

하네스: tests/test_phase05_ai_executor.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Protocol

from app.ai.ai_command_schema import AiCommandStatus, TreatmentItem
from app.ai.ai_validator import (
    ValidationResult,
    validate_appointment_candidate,
)


# ────────────────────────────── Service callable Protocol ──────────────────────────────


class AppointmentServiceCallable(Protocol):
    """기존 예약 등록 service callable. router 가 주입.

    AI executor 는 본 callable 을 호출만 하고 결과 dict 를 받음. 직접 INSERT 금지.
    """

    def __call__(
        self,
        *,
        patient_id: str,
        therapist_id: str | None,
        target_date: date,
        start_hour: int,
        start_minute: int,
        duration_min: int,
        treatment_codes: list[str],
        memo: str | None,
        actor_user_id: str,
    ) -> dict[str, Any]: ...


class PatientServiceCallable(Protocol):
    """기존 환자 등록 service callable. router 가 주입.

    중복 검사는 caller (router / Phase 4 의 evaluate_new_patient_input) 가 사전 수행.
    본 callable 은 INSERT 만 담당.
    """

    def __call__(
        self,
        *,
        chart_no: str,
        name: str,
        birth_date: str | None,
        phone: str | None,
        actor_user_id: str,
    ) -> dict[str, Any]: ...


# ────────────────────────────── 결과 데이터 ──────────────────────────────


@dataclass
class ExecutionResult:
    success: bool
    new_status: str  # AiCommandStatus 값
    result_payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    revalidation: ValidationResult | None = None  # Gate 2 결과


# ────────────────────────────── 예약 등록 executor ──────────────────────────────


def execute_approved_appointment(
    db_session: Any,
    *,
    patient_id: str,
    therapist_id: str | None,
    target_date: date | None,
    start_hour: int | None,
    start_minute: int = 0,
    duration_min: int = 30,
    treatment_items: list[TreatmentItem],
    memo: str | None,
    actor_user_id: str,
    appointment_service: AppointmentServiceCallable,
    is_past_date: bool = False,
) -> ExecutionResult:
    """승인된 예약 명령을 실행.

    1) Gate 2 — 승인 직전 최종 재검증 (다른 사용자가 끼어들었을 가능성)
    2) 재검증 통과 시 appointment_service 호출
    3) 실패 / 성공 모두 ExecutionResult 반환

    DB 직접 수정 0 — appointment_service 가 INSERT 담당.
    """
    # Gate 2: 최종 재검증
    revalidation = validate_appointment_candidate(
        db_session,
        patient_id=patient_id,
        therapist_id=therapist_id,
        target_date=target_date,
        start_hour=start_hour,
        start_minute=start_minute,
        duration_min=duration_min,
        treatment_items=treatment_items,
        is_past_date=is_past_date,
    )

    if not revalidation.can_approve:
        return ExecutionResult(
            success=False,
            new_status=AiCommandStatus.VALIDATION_FAILED.value,
            error_message="승인 직전 최종 재검증 실패",
            revalidation=revalidation,
        )

    # 필수값 모두 보장됨 (validator 가 통과했으므로)
    if target_date is None or start_hour is None or patient_id is None:
        # validator 가 can_approve=True 인데 None 이면 시스템 오류
        return ExecutionResult(
            success=False,
            new_status=AiCommandStatus.FAILED.value,
            error_message="시스템 오류: 검증 통과했으나 필수값 누락",
            revalidation=revalidation,
        )

    # 기존 service 호출 (DB 직접 수정 금지)
    treatment_codes = [
        ti.matched_treatment_id
        for ti in treatment_items
        if ti.matched_treatment_id is not None
    ]
    try:
        result = appointment_service(
            patient_id=patient_id,
            therapist_id=therapist_id,
            target_date=target_date,
            start_hour=start_hour,
            start_minute=start_minute,
            duration_min=duration_min,
            treatment_codes=treatment_codes,
            memo=memo,
            actor_user_id=actor_user_id,
        )
    except Exception as e:  # noqa: BLE001
        return ExecutionResult(
            success=False,
            new_status=AiCommandStatus.FAILED.value,
            error_message=f"예약 service 호출 실패: {e}",
            revalidation=revalidation,
        )

    return ExecutionResult(
        success=True,
        new_status=AiCommandStatus.EXECUTED.value,
        result_payload=result,
        revalidation=revalidation,
    )


# ────────────────────────────── 신환 등록 executor ──────────────────────────────


def execute_approved_new_patient(
    *,
    chart_no: str,
    name: str,
    birth_date: str | None,
    phone: str | None,
    actor_user_id: str,
    patient_service: PatientServiceCallable,
) -> ExecutionResult:
    """승인된 신환 등록 명령을 실행.

    중복 검사는 router / Phase 4 의 evaluate_new_patient_input 가 이미 수행 (Gate 1).
    본 함수는 caller 가 주입한 service 만 호출 (Gate 2 는 service 내부 unique 제약).

    DB 직접 수정 0.
    """
    if not chart_no or not name:
        return ExecutionResult(
            success=False,
            new_status=AiCommandStatus.PATIENT_REGISTRATION_FAILED.value,
            error_message="필수값 누락 (차트번호 / 이름)",
        )

    try:
        result = patient_service(
            chart_no=chart_no,
            name=name,
            birth_date=birth_date,
            phone=phone,
            actor_user_id=actor_user_id,
        )
    except Exception as e:  # noqa: BLE001
        return ExecutionResult(
            success=False,
            new_status=AiCommandStatus.PATIENT_REGISTRATION_FAILED.value,
            error_message=f"환자 등록 service 호출 실패: {e}",
        )

    return ExecutionResult(
        success=True,
        new_status=AiCommandStatus.PATIENT_REGISTERED.value,
        result_payload=result,
    )


# ────────────────────────────── audit 기록 헬퍼 ──────────────────────────────


def finalize_audit(
    audit_module: Any,
    conn: Any,
    *,
    command_id: int,
    execution: ExecutionResult,
) -> None:
    """ExecutionResult 를 ai_command_logs 에 반영 (status / executed_result / error)."""
    audit_module.update_log(
        conn,
        command_id,
        status=execution.new_status,
        executed_result=execution.result_payload if execution.success else None,
        error_message=execution.error_message,
        executed_at_now=execution.success,
        validation_result=(
            {
                "checks": execution.revalidation.checks,
                "issues": [
                    {"code": i.code, "message": i.message, "severity": i.severity}
                    for i in execution.revalidation.issues
                ],
                "can_approve": execution.revalidation.can_approve,
            }
            if execution.revalidation
            else None
        ),
    )
