"""app.ai — 병원 예약관리 AI 명령 모듈 (Phase 1+).

설계 원칙 (docs/ai/AI_FEATURE_MASTER_PLAN.md 참조):
- AI 는 **후보 생성**만 담당 (자연어 → 구조화 JSON).
- 프로그램이 **DB 기준 검증**을 담당.
- 사용자가 **최종 승인**을 담당.
- **기존 서비스 로직** 이 실제 실행 담당 (AI executor 는 직접 DB 수정 금지).

본 패키지는 기존 `app.services.ai` (RAG / SMS draft / manual_qa 등) 와 **분리** 된
신규 AI 명령 (예약 / 휴무 도우미) 모듈입니다. 도메인이 다르므로 충돌하지 않습니다.

Phase 1 범위:
- ai_command_schema: 명령 데이터 / 상태값 정의 (실행 없음)
- ai_provider:       외부 AI API provider 추상화 (Mock + 실제)
- ai_audit:          ai_command_logs 저장 (DB 직접 수정 금지, repository 호출)

Phase 5 에서 executor 추가 예정.
"""

from app.ai.ai_command_schema import (
    AiCommandStatus,
    AiIntent,
    DataSourceState,
    ParsedCommand,
    TreatmentItemStatus,
)
from app.ai.ai_appointment_change import (
    AppointmentCancelServiceCallable,
    AppointmentDiff,
    AppointmentUpdateServiceCallable,
    ChangeExecutionResult,
    TargetAppointment,
    TargetResolution,
    build_appointment_diff,
    build_cancel_preview,
    build_update_preview,
    execute_approved_cancel_appointment,
    execute_approved_update_appointment,
    resolve_target_appointment,
    validate_cancel_appointment,
    validate_update_appointment,
)
from app.ai.ai_executor import (
    AppointmentServiceCallable,
    ExecutionResult,
    PatientServiceCallable,
    execute_approved_appointment,
    execute_approved_new_patient,
    finalize_audit,
)
from app.ai.ai_harness import (
    HallucinationCheckResult,
    HarnessRunResult,
    PrivacyCheckResult,
    assert_executor_did_not_modify_db,
    check_hallucination,
    check_privacy_payload,
    run_approval_and_execute,
    run_new_patient_and_appointment,
    run_pipeline,
    run_regression_smoke,
)
from app.ai.ai_new_patient_flow import (
    NewPatientFlowResult,
    RevalidationContext,
    UserPermission,
    build_revalidation_request,
    can_register_new_patient,
    evaluate_new_patient_input,
    log_appointment_after_new_patient,
    log_new_patient_registration,
    propose_new_patient_from_resolution,
)
from app.ai.ai_parser import parse_command
from app.ai.ai_preview import (
    build_appointment_preview,
    build_new_patient_proposal,
    build_patient_candidate_panel,
    build_treatment_candidate_panel,
)
from app.ai.ai_provider import (
    AIProvider,
    MockProvider,
    ProviderError,
    get_default_provider,
)
from app.ai.ai_resolver import (
    PatientCandidate,
    PatientResolution,
    resolve_date,
    resolve_patient,
    resolve_therapist,
    resolve_time,
    resolve_treatment_items,
)
from app.ai.ai_validator import (
    NewPatientDuplicateCheck,
    ValidationIssue,
    ValidationResult,
    check_new_patient_duplicates,
    validate_appointment_candidate,
)

__all__ = [
    # schema
    "AiCommandStatus",
    "AiIntent",
    "DataSourceState",
    "ParsedCommand",
    "TreatmentItemStatus",
    # provider
    "AIProvider",
    "MockProvider",
    "ProviderError",
    "get_default_provider",
    # parser
    "parse_command",
    # resolver
    "PatientCandidate",
    "PatientResolution",
    "resolve_date",
    "resolve_patient",
    "resolve_therapist",
    "resolve_time",
    "resolve_treatment_items",
    # validator
    "NewPatientDuplicateCheck",
    "ValidationIssue",
    "ValidationResult",
    "check_new_patient_duplicates",
    "validate_appointment_candidate",
    # preview
    "build_appointment_preview",
    "build_new_patient_proposal",
    "build_patient_candidate_panel",
    "build_treatment_candidate_panel",
    # new patient flow
    "NewPatientFlowResult",
    "RevalidationContext",
    "UserPermission",
    "build_revalidation_request",
    "can_register_new_patient",
    "evaluate_new_patient_input",
    "log_appointment_after_new_patient",
    "log_new_patient_registration",
    "propose_new_patient_from_resolution",
    # executor
    "AppointmentServiceCallable",
    "ExecutionResult",
    "PatientServiceCallable",
    "execute_approved_appointment",
    "execute_approved_new_patient",
    "finalize_audit",
    # appointment change (Phase 7)
    "AppointmentCancelServiceCallable",
    "AppointmentDiff",
    "AppointmentUpdateServiceCallable",
    "ChangeExecutionResult",
    "TargetAppointment",
    "TargetResolution",
    "build_appointment_diff",
    "build_cancel_preview",
    "build_update_preview",
    "execute_approved_cancel_appointment",
    "execute_approved_update_appointment",
    "resolve_target_appointment",
    "validate_cancel_appointment",
    "validate_update_appointment",
    # harness (Phase 6)
    "HallucinationCheckResult",
    "HarnessRunResult",
    "PrivacyCheckResult",
    "assert_executor_did_not_modify_db",
    "check_hallucination",
    "check_privacy_payload",
    "run_approval_and_execute",
    "run_new_patient_and_appointment",
    "run_pipeline",
    "run_regression_smoke",
]
