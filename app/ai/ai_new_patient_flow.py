"""ai_new_patient_flow — 신환 등록 연계 흐름 (Phase 4).

역할:
- 환자 검색 실패 시 신환 등록 제안 → 입력 → 중복 검사 → 승인 → 예약 후보 재검증.
- 신환 등록과 예약 등록은 **각각 별도 로그** 로 기록 (AI_FEATURE_MASTER_PLAN § 10.2).
- 권한 정책 적용:
  * 일반 직원: 중복 없는 신환 등록 + 예약 등록 가능
  * 관리자: 중복 무시 / 강제 등록 / 환자 삭제 / 환자 병합 / 차트번호 변경

주의:
- 본 모듈은 **오케스트레이터** — 새 DB 로직 도입하지 않고 기존 모듈 (resolver / validator / preview / audit) 호출.
- 실제 환자 INSERT 는 **사용자 승인 후** 기존 환자 등록 service 가 담당 (Phase 5 의 executor 통합).
- AI 가 차트번호 / 생년월일 / 연락처를 임의 생성하지 않음 (사용자 입력만).
- 신환 등록 후 예약은 **자동 저장 금지** — 재검증 후 별도 승인.

cross-reference:
- 신환 등록 흐름 14 단계 → AI_FEATURE_MASTER_PLAN.md § 10.1
- 권한 정책 → AI_FEATURE_MASTER_PLAN.md § 10.3
- 별도 로그 → AI_FEATURE_MASTER_PLAN.md § 10.2 / AI_COMMAND_ARCHITECTURE.md § 5.2

하네스: tests/test_phase04_ai_new_patient_flow.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from app.ai.ai_command_schema import AiCommandStatus
from app.ai.ai_preview import (
    build_new_patient_proposal,
    build_patient_candidate_panel,
)
from app.ai.ai_resolver import PatientCandidate, PatientResolution
from app.ai.ai_validator import (
    NewPatientDuplicateCheck,
    check_new_patient_duplicates,
)


# ────────────────────────────── 권한 ──────────────────────────────


@dataclass
class UserPermission:
    """사용자 권한 — Phase 5 의 router 가 require_admin 로 강제 (여기서는 데이터로 받음)."""

    user_id: str
    is_admin: bool = False


def can_register_new_patient(
    duplicates: NewPatientDuplicateCheck, user: UserPermission
) -> tuple[bool, str | None]:
    """신환 등록 권한 검사.

    - 중복 없음 + 필수값 충족 → 일반 직원 권한 OK
    - 중복 있음 → 관리자 권한 필요
    - 필수값 누락 → 권한 무관 불가
    """
    if duplicates.missing_required:
        return False, f"필수값 누락: {', '.join(duplicates.missing_required)}"
    if duplicates.has_duplicates and not user.is_admin:
        return False, "중복 의심 환자 발견 — 관리자 승인 필요"
    return True, None


# ────────────────────────────── 1단계: 환자 검색 실패 → 제안 ──────────────────────────────


def propose_new_patient_from_resolution(
    resolution: PatientResolution,
    *,
    suggested_chart_no: str | None = None,
    suggested_name: str | None = None,
) -> dict[str, Any] | None:
    """resolver 결과가 not_found 면 신환 등록 제안 카드 반환. 아니면 None.

    AI 가 차트번호 / 생년월일 / 연락처를 자동 생성하지 않음 — 사용자가 입력해야 함.
    suggested_* 는 parser 가 추출한 raw 값 (참고용 prefill, 사용자 수정 가능).
    """
    if not resolution.not_found:
        return None

    panel = build_patient_candidate_panel([], is_not_found=True)
    panel["status"] = AiCommandStatus.PATIENT_REGISTRATION_PROPOSED.value
    panel["prefill"] = {
        "chart_no": suggested_chart_no,
        "name": suggested_name,
        # 생년월일 / 연락처는 AI 가 추측하지 않음 — 사용자가 직접 입력
        "birth_date": None,
        "phone": None,
    }
    return panel


# ────────────────────────────── 2단계: 신환 등록 제안 + 중복 검사 ──────────────────────────────


@dataclass
class NewPatientFlowResult:
    """신환 등록 흐름 1 단계 결과."""

    status: str  # AiCommandStatus 값
    proposal_panel: dict[str, Any] | None = None
    duplicates: NewPatientDuplicateCheck | None = None
    can_approve: bool = False
    needs_admin: bool = False
    error_message: str | None = None


def evaluate_new_patient_input(
    session: Any,
    *,
    chart_no: str | None,
    name: str | None,
    birth_date: str | None,
    phone: str | None,
    user: UserPermission,
) -> NewPatientFlowResult:
    """사용자가 입력한 신환 정보를 검사하고 승인 카드 데이터 반환.

    승인 가능 / 관리자 권한 필요 / 필수값 누락 등을 결정.
    """
    duplicates = check_new_patient_duplicates(
        session, chart_no=chart_no, name=name, birth_date=birth_date, phone=phone
    )

    can_register, reason = can_register_new_patient(duplicates, user)

    if duplicates.missing_required:
        status = AiCommandStatus.PATIENT_REGISTRATION_FAILED.value
    elif can_register:
        status = AiCommandStatus.PATIENT_REGISTRATION_NEEDS_APPROVAL.value
    else:
        status = AiCommandStatus.PATIENT_REGISTRATION_NEEDS_APPROVAL.value  # 관리자 승인 대기

    panel = build_new_patient_proposal(
        chart_no=chart_no,
        name=name,
        birth_date=birth_date,
        phone=phone,
        duplicates=duplicates,
        is_admin=user.is_admin,
    )

    return NewPatientFlowResult(
        status=status,
        proposal_panel=panel,
        duplicates=duplicates,
        can_approve=can_register,
        needs_admin=duplicates.has_duplicates and not user.is_admin,
        error_message=reason if not can_register else None,
    )


# ────────────────────────────── 3단계: 신환 등록 후 예약 후보 재검증 트리거 ──────────────────────────────


@dataclass
class RevalidationContext:
    """신환 등록 후 예약 후보를 다시 만들 때 필요한 컨텍스트."""

    new_patient_id: str
    therapist_id: str | None
    target_date: date | None
    start_hour: int | None
    start_minute: int = 0


def build_revalidation_request(
    *,
    new_patient_id: str,
    original_command_id: int,
    therapist_id: str | None,
    target_date: date | None,
    start_hour: int | None,
    start_minute: int = 0,
) -> dict[str, Any]:
    """신환 등록 완료 후 예약 후보 재검증 요청 구조.

    caller (router) 가 본 데이터로 validator 를 다시 호출 + preview 재생성.
    """
    return {
        "status": AiCommandStatus.APPOINTMENT_NEEDS_REVALIDATION.value,
        "original_command_id": original_command_id,
        "new_patient_id": new_patient_id,
        "appointment_context": {
            "therapist_id": therapist_id,
            "target_date": target_date.isoformat() if target_date else None,
            "start_hour": start_hour,
            "start_minute": start_minute,
        },
        "note": "신환 등록이 완료되었습니다. 예약 후보를 다시 확인합니다.",
    }


# ────────────────────────────── 별도 로그 기록 헬퍼 ──────────────────────────────


def log_new_patient_registration(
    audit_module: Any,
    conn: Any,
    *,
    user: UserPermission,
    raw_text: str,
    chart_no: str | None,
    name: str | None,
    birth_date: str | None,
    phone: str | None,
    duplicates: NewPatientDuplicateCheck,
    status: str,
) -> int:
    """신환 등록 시도를 별도 로그 row 로 기록.

    예약 등록 로그와 분리 — 재현 / 감사 시 신환 등록 단독 추적 가능.
    """
    return audit_module.write_log(
        conn,
        user_id=user.user_id,
        raw_text=raw_text,
        intent="create_appointment",  # 신환 흐름은 create_appointment 의 부분 단계
        status=status,
        parsed_json={
            "step": "new_patient_registration",
            "input": {
                "chart_no": chart_no,
                "name": name,
                "birth_date": birth_date,
                "phone": phone,
            },
        },
        validation_result={
            "has_duplicates": duplicates.has_duplicates,
            "missing_required": duplicates.missing_required,
            "duplicates_count": (
                len(duplicates.chart_no_duplicate)
                + len(duplicates.name_birth_duplicate)
                + len(duplicates.name_phone_duplicate)
                + len(duplicates.phone_duplicate)
            ),
        },
    )


def log_appointment_after_new_patient(
    audit_module: Any,
    conn: Any,
    *,
    user: UserPermission,
    raw_text: str,
    new_patient_id: str,
    new_patient_log_id: int,
    status: str,
) -> int:
    """신환 등록 직후 예약 후보 로그를 별도 row 로 기록.

    parsed_json 에 new_patient_log_id 를 cross-reference 로 저장.
    """
    return audit_module.write_log(
        conn,
        user_id=user.user_id,
        raw_text=raw_text,
        intent="create_appointment",
        status=status,
        parsed_json={
            "step": "appointment_after_new_patient",
            "new_patient_id": new_patient_id,
            "new_patient_log_id": new_patient_log_id,
        },
    )


# ────────────────────────────── DB 의존성 추상화 ──────────────────────────────


class DBSession(Protocol):
    def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any: ...
