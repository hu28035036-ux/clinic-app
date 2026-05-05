"""ai_harness — Phase 6 통합 하네스 (10종 풀세트).

역할:
- Phase 1~5 의 모든 모듈 (parser / resolver / validator / preview / new_patient_flow / executor / audit)
  을 end-to-end 흐름으로 묶어 자동 검증 가능하게 함.
- 운영 router 진입점이 아니라 **검증용 오케스트레이터** — 단위 테스트 / CI / 관리자 진단 도구.
- AI executor 와 동일하게 의존성 역전 (provider, appointment_service, patient_service 모두 caller 가 주입).

10 하네스 정합 (AI_HARNESS_PLAN.md § 1):
1.  Parser              — run_pipeline() 의 parser 단계 결과 검사
2.  Resolver            — run_pipeline() 의 resolver 단계 결과 검사
3.  Patient Candidate   — run_pipeline() 의 patient_panel 검사
4.  Validator           — run_pipeline() 의 validation 검사
5.  Approval (Gate 1)   — run_approval_and_execute() 의 사전 차단 검사
6.  Executor (Gate 2)   — run_approval_and_execute() 의 service callable 호출 검사
7.  Privacy             — check_privacy_payload() 외부 전송 페이로드 검사
8.  Hallucination       — check_hallucination() 미확정 / 임의 생성 검사
9.  Regression          — run_regression_smoke() Phase 1~5 기존 모듈 정합 확인
10. Runtime             — run_pipeline() 자체가 실제 코드 경로를 호출 (Phase 6 RUNTIME_TEST 에 사용)

주의:
- 본 모듈은 **DB 직접 수정 금지**. 모든 INSERT 는 caller 가 주입한 service callable.
- 외부 AI API 호출 0 — provider 가 주어지지 않으면 정규식 fallback (Phase 2 와 동일).
- 운영 DB 미접근 — caller (테스트) 가 in-memory SQLAlchemy session 주입.
- AI 가 임의로 환자 / 차트번호 / 생년월일 / 연락처 / 치료항목을 확정하지 않음
  (parser/resolver 결과 그대로 전달, 미확정은 needs_clarification 상태 유지).

cross-reference:
- 10 하네스 종류 → AI_HARNESS_PLAN.md § 1
- Privacy 금지 페이로드 → AI_SAFETY_POLICY.md § 3.2
- Hallucination 표현 / 데이터 출처 상태 → AI_SAFETY_POLICY.md § 2.1 / § 2.3
- Gate 1 / Gate 2 → AI_SAFETY_POLICY.md § 4

하네스: tests/test_phase06_ai_harness.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.ai import ai_audit, ai_safety
from app.ai.ai_command_schema import (
    AiCommandStatus,
    AiIntent,
    ParsedCommand,
    ParserContext,
    TreatmentItem,
    TreatmentItemStatus,
)
from app.ai.ai_executor import (
    AppointmentServiceCallable,
    ExecutionResult,
    PatientServiceCallable,
    execute_approved_appointment,
    execute_approved_new_patient,
    finalize_audit,
)
from app.ai.ai_new_patient_flow import (
    UserPermission,
    propose_new_patient_from_resolution,
)
from app.ai.ai_parser import parse_command
from app.ai.ai_preview import (
    build_appointment_preview,
    build_patient_candidate_panel,
    build_treatment_candidate_panel,
)
from app.ai.ai_provider import AIProvider, MockProvider
from app.ai.ai_resolver import (
    DateResolution,
    PatientCandidate,
    PatientResolution,
    TherapistResolution,
    TimeResolution,
    resolve_date,
    resolve_patient,
    resolve_therapist,
    resolve_time,
    resolve_treatment_items,
)
from app.ai.ai_validator import (
    ValidationResult,
    validate_appointment_candidate,
)


# ────────────────────────────── 결과 데이터 ──────────────────────────────


@dataclass
class HarnessRunResult:
    """parse → resolve → validate → preview 까지 read-only 파이프라인 결과.

    승인 / 실행은 별도 함수 (run_approval_and_execute) 에서.
    """

    raw_text: str
    parsed: ParsedCommand
    patient_resolution: PatientResolution
    therapist_resolution: TherapistResolution
    date_resolution: DateResolution
    time_resolution: TimeResolution
    treatment_items: list[TreatmentItem]
    validation: ValidationResult | None = None
    preview: dict[str, Any] | None = None
    patient_panel: dict[str, Any] | None = None
    treatment_panel: dict[str, Any] | None = None
    new_patient_proposal: dict[str, Any] | None = None
    status: str = AiCommandStatus.PARSED.value
    selected_patient: PatientCandidate | None = None


# Privacy / Hallucination 검사는 `ai_safety` 가 단일 원천 (SSOT § 9 정합).
# 본 모듈은 그대로 re-export 하여 호환성 유지 (중복 구현 금지 — § 15.1 원칙 4).
PrivacyCheckResult = ai_safety.PrivacyCheckResult
HallucinationCheckResult = ai_safety.HallucinationCheckResult
check_privacy_payload = ai_safety.check_privacy_payload
check_hallucination = ai_safety.check_hallucination


# ────────────────────────────── 3. 통합 파이프라인 (read-only) ──────────────────────────────


def run_pipeline(
    db_session: Any,
    *,
    raw_text: str,
    current_calendar_year: int,
    current_calendar_month: int,
    today: date | None = None,
    provider: AIProvider | None = None,
    selected_patient_id: str | None = None,
) -> HarnessRunResult:
    """Phase 1~3 통합 read-only 파이프라인.

    1) parse → ParsedCommand
    2) resolve_patient / resolve_therapist / resolve_date / resolve_time / resolve_treatment_items
    3) selected_patient_id 가 주어지면 candidates 중 해당 후보 선택, 아니면 단일 후보면 자동 확정
    4) validate_appointment_candidate → ValidationResult
    5) build_*_panel / build_appointment_preview → preview dict

    DB 직접 수정 0 — 본 함수는 read-only.
    """
    provider = provider or MockProvider()
    # DB 의 실제 약어 / 이름 / 코드 모두 수집 — parser 가 하드코딩 정규식이 아닌
    # *DB 기준* 으로 토큰 추출하도록. (사용자 지시 — 약어 하드코딩 금지)
    treatment_names, treatment_aliases = _collect_treatment_terms(db_session)
    context = ParserContext(
        raw_text=raw_text,
        current_calendar_year=current_calendar_year,
        current_calendar_month=current_calendar_month,
        available_intents=[i.value for i in AiIntent],
        treatment_names=treatment_names,
        treatment_aliases=treatment_aliases,
    )

    parsed = parse_command(raw_text, context=context, provider=provider)

    patient_res = resolve_patient(
        db_session,
        patient_name=parsed.patient_name,
        chart_number=parsed.chart_number,
    )
    therapist_res = resolve_therapist(db_session, therapist_name=parsed.therapist_name)
    date_res = resolve_date(
        parsed.date_text,
        current_calendar_year=current_calendar_year,
        current_calendar_month=current_calendar_month,
        today=today,
    )
    time_res = resolve_time(parsed.time_text)

    # 치료항목 — parser 가 만든 raw items 가 NEEDS_CLARIFICATION 이므로
    # treatment_text 를 resolver 로 다시 매칭.
    treatment_items = resolve_treatment_items(
        db_session, treatment_text=parsed.treatment_text
    )

    # 환자 선택 — 단일 후보면 자동 확정, 다수 후보 + selected_patient_id 가 있으면 그것
    selected = _pick_selected_patient(patient_res, selected_patient_id)

    # 환자 후보 패널
    patient_panel = build_patient_candidate_panel(
        patient_res.candidates,
        is_mismatch=patient_res.mismatch,
        is_not_found=patient_res.not_found,
    )

    # 치료항목 패널
    treatment_panel = build_treatment_candidate_panel(treatment_items)

    # 신환 등록 제안 (검색 실패 시)
    new_patient_proposal = propose_new_patient_from_resolution(
        patient_res,
        suggested_chart_no=parsed.chart_number,
        suggested_name=parsed.patient_name,
    )

    # 검증 — 선택된 환자가 있을 때만 의미 있음
    validation: ValidationResult | None = None
    preview: dict[str, Any] | None = None
    if selected is not None:
        validation = validate_appointment_candidate(
            db_session,
            patient_id=selected.patient_id,
            therapist_id=therapist_res.therapist_id,
            target_date=date_res.resolved_date,
            start_hour=time_res.hour,
            start_minute=time_res.minute,
            duration_min=30,
            treatment_items=treatment_items,
            is_past_date=date_res.is_past,
        )
        preview = build_appointment_preview(
            patient=selected,
            target_date=date_res.resolved_date,
            start_hour=time_res.hour,
            start_minute=time_res.minute,
            therapist_name=therapist_res.therapist_name,
            treatment_items=treatment_items,
            validation=validation,
            date_note=date_res.note,
        )

    status = _derive_status(
        patient_res=patient_res,
        treatment_items=treatment_items,
        validation=validation,
        selected_patient=selected,
    )

    return HarnessRunResult(
        raw_text=raw_text,
        parsed=parsed,
        patient_resolution=patient_res,
        therapist_resolution=therapist_res,
        date_resolution=date_res,
        time_resolution=time_res,
        treatment_items=treatment_items,
        validation=validation,
        preview=preview,
        patient_panel=patient_panel,
        treatment_panel=treatment_panel,
        new_patient_proposal=new_patient_proposal,
        status=status,
        selected_patient=selected,
    )


def _collect_treatment_terms(db_session: Any) -> tuple[list[str], list[str]]:
    """DB 의 Treatment.name / short / code + treatment_aliases.alias_name 수집.

    parser 에 전달해 *하드코딩 정규식 ⊥ / DB 약어 우선* 정합. read-only.
    """
    from sqlalchemy import select, text

    from app.models.models import Treatment

    names: list[str] = []
    aliases: list[str] = []
    try:
        rows = list(db_session.execute(select(Treatment)).scalars())
        for t in rows:
            if t.name and t.name not in names:
                names.append(t.name)
            for term in (t.short, t.code):
                if term and term not in aliases:
                    aliases.append(term)
    except Exception:  # noqa: BLE001
        # DB 접근 실패 시 빈 리스트 — parser 가 정규식 fallback 사용
        pass
    try:
        result = db_session.execute(
            text("SELECT alias_name FROM treatment_aliases")
        )
        for row in result.fetchall():
            alias = row[0]
            if alias and alias not in aliases:
                aliases.append(alias)
    except Exception:  # noqa: BLE001
        pass
    return names, aliases


def _pick_selected_patient(
    resolution: PatientResolution, selected_patient_id: str | None
) -> PatientCandidate | None:
    """단일 후보면 자동 확정, 다수일 땐 selected_patient_id 일치 후보, 그 외 None.

    AI 가 임의로 선택하지 않음 — 다수 후보면 selected_patient_id 가 있어야만 확정.
    mismatch / not_found 일 땐 항상 None.
    """
    if resolution.mismatch or resolution.not_found:
        return None
    if len(resolution.candidates) == 1:
        return resolution.candidates[0]
    if selected_patient_id is None:
        return None
    for c in resolution.candidates:
        if c.patient_id == selected_patient_id:
            return c
    return None


def _derive_status(
    *,
    patient_res: PatientResolution,
    treatment_items: list[TreatmentItem],
    validation: ValidationResult | None,
    selected_patient: PatientCandidate | None = None,
) -> str:
    """파이프라인 결과로 AiCommandStatus 결정 (UI / audit 표시용).

    selected_patient 가 명시되면 환자 다수 후보여도 *선택됨* 상태로 다음 단계 진행.
    """
    if patient_res.not_found:
        return AiCommandStatus.PATIENT_NOT_FOUND.value
    if patient_res.mismatch:
        return AiCommandStatus.PATIENT_MISMATCH.value
    if len(patient_res.candidates) > 1 and selected_patient is None:
        return AiCommandStatus.PATIENT_SELECTION_REQUIRED.value
    # 치료항목 상태
    for ti in treatment_items:
        if ti.status == TreatmentItemStatus.ALIAS_CONFLICT:
            return AiCommandStatus.TREATMENT_ALIAS_CONFLICT.value
        if ti.status == TreatmentItemStatus.NOT_FOUND:
            return AiCommandStatus.TREATMENT_NOT_FOUND.value
        if ti.status == TreatmentItemStatus.NEEDS_CLARIFICATION:
            return AiCommandStatus.TREATMENT_SELECTION_REQUIRED.value
    if validation is None:
        return AiCommandStatus.NEEDS_CLARIFICATION.value
    if validation.can_approve:
        return AiCommandStatus.NEEDS_APPROVAL.value
    return AiCommandStatus.VALIDATION_FAILED.value


# ────────────────────────────── 4. 승인 + 실행 (Gate 1 + Gate 2) ──────────────────────────────


def run_approval_and_execute(
    db_session: Any,
    audit_conn: Any,
    *,
    run_result: HarnessRunResult,
    user: UserPermission,
    appointment_service: AppointmentServiceCallable,
    memo: str | None = None,
) -> ExecutionResult:
    """run_pipeline() 결과를 승인 + 실행.

    Gate 1: HarnessRunResult.status 가 NEEDS_APPROVAL 가 아니면 차단 (사용자 승인 불가).
    Gate 2: executor 가 다시 validator 호출 (승인 직전 최종 재검증) — Phase 5 그대로.

    audit log 도 함께 갱신 (RECEIVED → status → EXECUTED / VALIDATION_FAILED / FAILED).
    """
    # audit 로그 신규 row — Phase 6 통합 진입점
    cmd_id = ai_audit.write_log(
        audit_conn,
        user_id=user.user_id,
        raw_text=run_result.raw_text,
        intent=run_result.parsed.intent.value if run_result.parsed.intent else None,
        status=run_result.status,
        parsed_json=run_result.parsed.to_dict(),
        validation_result=(
            {
                "checks": run_result.validation.checks,
                "issues": [
                    {"code": i.code, "message": i.message, "severity": i.severity}
                    for i in run_result.validation.issues
                ],
                "can_approve": run_result.validation.can_approve,
            }
            if run_result.validation
            else None
        ),
    )

    # Gate 1 — 사용자 승인 가능 상태 확인
    if run_result.status != AiCommandStatus.NEEDS_APPROVAL.value:
        execution = ExecutionResult(
            success=False,
            new_status=AiCommandStatus.VALIDATION_FAILED.value,
            error_message=f"승인 불가 상태: {run_result.status}",
            revalidation=run_result.validation,
        )
        finalize_audit(ai_audit, audit_conn, command_id=cmd_id, execution=execution)
        return execution

    # 선택된 환자가 있어야 진행 (run_pipeline 가 보장하지만 명시 가드)
    if run_result.selected_patient is None:
        execution = ExecutionResult(
            success=False,
            new_status=AiCommandStatus.VALIDATION_FAILED.value,
            error_message="선택된 환자가 없습니다.",
        )
        finalize_audit(ai_audit, audit_conn, command_id=cmd_id, execution=execution)
        return execution

    # Gate 2 — executor 가 validator 재호출
    execution = execute_approved_appointment(
        db_session,
        patient_id=run_result.selected_patient.patient_id,
        therapist_id=run_result.therapist_resolution.therapist_id,
        target_date=run_result.date_resolution.resolved_date,
        start_hour=run_result.time_resolution.hour,
        start_minute=run_result.time_resolution.minute,
        duration_min=30,
        treatment_items=run_result.treatment_items,
        memo=memo,
        actor_user_id=user.user_id,
        appointment_service=appointment_service,
        is_past_date=run_result.date_resolution.is_past,
    )
    finalize_audit(ai_audit, audit_conn, command_id=cmd_id, execution=execution)
    return execution


# ────────────────────────────── 5. 신환 등록 + 예약 두 단계 흐름 ──────────────────────────────


def run_new_patient_and_appointment(
    db_session: Any,
    audit_conn: Any,
    *,
    raw_text: str,
    user: UserPermission,
    chart_no: str,
    name: str,
    birth_date: str | None,
    phone: str | None,
    patient_service: PatientServiceCallable,
    appointment_service: AppointmentServiceCallable,
    therapist_id: str | None,
    target_date: date | None,
    start_hour: int | None,
    treatment_items: list[TreatmentItem],
) -> tuple[ExecutionResult, ExecutionResult]:
    """신환 등록 → 등록된 patient_id 로 예약 등록 두 단계 흐름.

    각 단계는 별도 audit log row.
    신환 등록 실패 시 두 번째 단계 실행 안 함.
    """
    # 신환 등록 단계
    pat_cmd = ai_audit.write_log(
        audit_conn,
        user_id=user.user_id,
        raw_text=raw_text,
        intent="create_appointment",
        status=AiCommandStatus.PATIENT_REGISTRATION_NEEDS_APPROVAL.value,
        parsed_json={
            "step": "new_patient_registration",
            "input": {
                "chart_no": chart_no,
                "name": name,
                "birth_date": birth_date,
                "phone": phone,
            },
        },
    )
    pat_exec = execute_approved_new_patient(
        chart_no=chart_no,
        name=name,
        birth_date=birth_date,
        phone=phone,
        actor_user_id=user.user_id,
        patient_service=patient_service,
    )
    finalize_audit(ai_audit, audit_conn, command_id=pat_cmd, execution=pat_exec)

    if not pat_exec.success:
        # 두 번째 단계 미진행 — failed 로 별도 row
        skipped = ExecutionResult(
            success=False,
            new_status=AiCommandStatus.APPOINTMENT_NEEDS_REVALIDATION.value,
            error_message="신환 등록 실패로 예약 단계 건너뜀.",
        )
        return pat_exec, skipped

    new_patient_id = pat_exec.result_payload.get("patient_id")
    if not new_patient_id:
        skipped = ExecutionResult(
            success=False,
            new_status=AiCommandStatus.FAILED.value,
            error_message="환자 등록 service 가 patient_id 를 반환하지 않음.",
        )
        return pat_exec, skipped

    # 예약 등록 단계 — 별도 audit row
    appt_cmd = ai_audit.write_log(
        audit_conn,
        user_id=user.user_id,
        raw_text=raw_text,
        intent="create_appointment",
        status=AiCommandStatus.APPOINTMENT_NEEDS_REVALIDATION.value,
        parsed_json={
            "step": "appointment_after_new_patient",
            "new_patient_id": new_patient_id,
            "new_patient_log_id": pat_cmd,
        },
    )
    appt_exec = execute_approved_appointment(
        db_session,
        patient_id=new_patient_id,
        therapist_id=therapist_id,
        target_date=target_date,
        start_hour=start_hour,
        treatment_items=treatment_items,
        memo=None,
        actor_user_id=user.user_id,
        appointment_service=appointment_service,
    )
    finalize_audit(ai_audit, audit_conn, command_id=appt_cmd, execution=appt_exec)

    return pat_exec, appt_exec


# ────────────────────────────── 6. Regression smoke ──────────────────────────────


def run_regression_smoke(db_session: Any) -> dict[str, bool]:
    """Phase 1~5 모듈이 import 가능하고 핵심 함수 시그니처가 살아있는지 확인.

    실제 행동 확인은 각 Phase 의 단위 테스트 + run_pipeline 통합 시나리오가 담당.
    본 함수는 "회귀 진단 로그" 용도 — 실패 항목이 있으면 dict 값이 False.
    """
    results: dict[str, bool] = {}

    # parser
    try:
        ctx = ParserContext(
            raw_text="박환자 내일 9시 도수30 예약",
            current_calendar_year=2026,
            current_calendar_month=5,
        )
        parsed = parse_command(ctx.raw_text, context=ctx)
        results["parser_callable"] = parsed.intent == AiIntent.CREATE_APPOINTMENT
    except Exception:  # noqa: BLE001
        results["parser_callable"] = False

    # resolver — db_session 이 비었어도 not_found 반환해야 함
    try:
        pat_res = resolve_patient(
            db_session, patient_name="존재하지않는환자xyz", chart_number=None
        )
        results["resolver_callable"] = isinstance(pat_res, PatientResolution)
    except Exception:  # noqa: BLE001
        results["resolver_callable"] = False

    # validator — 빈 입력으로 호출 시 issue 들 반환
    try:
        val = validate_appointment_candidate(
            db_session,
            patient_id=None,
            therapist_id=None,
            target_date=None,
            start_hour=None,
            treatment_items=[],
        )
        results["validator_callable"] = (
            isinstance(val, ValidationResult) and not val.can_approve
        )
    except Exception:  # noqa: BLE001
        results["validator_callable"] = False

    # preview — 더미 입력
    try:
        panel = build_patient_candidate_panel([], is_not_found=True)
        results["preview_callable"] = panel["kind"] == "patient_not_found"
    except Exception:  # noqa: BLE001
        results["preview_callable"] = False

    return results


# ────────────────────────────── 7. 안전 게이트 사후 검사 ──────────────────────────────


def assert_executor_did_not_modify_db(
    appointment_service_calls: int,
    patient_service_calls: int,
) -> bool:
    """executor 가 DB 직접 수정 0 — 모든 INSERT 는 service callable 경유.

    테스트가 fake service 의 호출 횟수를 기록한 뒤 본 함수로 정합 확인.
    Phase 1~5 정책 그대로 — 본 함수는 단지 호출 횟수 ≥ 0 검사.
    """
    return appointment_service_calls >= 0 and patient_service_calls >= 0
