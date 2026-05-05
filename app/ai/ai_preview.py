"""ai_preview — 사용자 승인 화면 데이터 생성 (Phase 3).

역할:
- 예약 후보 카드 / 환자 후보 카드 / 치료항목 후보 카드 / 신환 등록 후보 카드 데이터 생성.
- 환자 정보 차트번호 / 이름 / 생년월일 / 연락처 포함.
- 검증 결과 / 경고 메시지 포함.
- "해당 날짜에 예약 등록할까요?" 메시지 포함.

주의:
- 본 모듈은 **read-only**. DB 직접 조작 / 외부 API 호출 0.
- 승인 전에는 "예약 후보" / "예약 등록 후보" 라고 표시. "예약 완료" 표현 금지.
- 생년월일 / 연락처는 내부 DB 에서만 조회된 값을 사용 (ai_resolver 결과 활용).

cross-reference:
- 예약 후보 승인 화면 예시 → AI_FEATURE_MASTER_PLAN.md § 9
- 환자 후보 다수 처리 규칙 → AI_FEATURE_MASTER_PLAN.md § 8
- "예약 완료" 표현 금지 → AI_SAFETY_POLICY.md § 2.2

하네스: tests/test_phase03_ai_validator_preview.py
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from app.ai.ai_command_schema import TreatmentItem
from app.ai.ai_resolver import PatientCandidate
from app.ai.ai_validator import NewPatientDuplicateCheck, ValidationResult


# ────────────────────────────── 환자 후보 카드 ──────────────────────────────


def build_patient_candidate_panel(
    candidates: list[PatientCandidate],
    *,
    is_mismatch: bool = False,
    is_not_found: bool = False,
) -> dict[str, Any]:
    """환자 후보 선택 패널 데이터.

    - 후보 1건: 자동 확정 메시지
    - 후보 다수: 사용자 선택 요구 (예약 등록 버튼 비활성화)
    - mismatch: 차트번호 + 이름 불일치 — 승인 불가
    - not_found: 신환 등록 제안
    """
    if is_not_found:
        return {
            "kind": "patient_not_found",
            "message": "검색된 환자가 없습니다. 신환으로 등록한 뒤 예약을 계속 진행할까요?",
            "candidates": [],
            "approval_disabled": True,
            "actions": ["취소", "신환 등록"],
        }

    if is_mismatch:
        return {
            "kind": "patient_mismatch",
            "message": "차트번호와 환자명이 서로 다른 환자를 가리킵니다. 승인 불가.",
            "candidates": [_candidate_dict(c) for c in candidates],
            "approval_disabled": True,
            "actions": ["취소"],
        }

    if len(candidates) > 1:
        return {
            "kind": "patient_selection_required",
            "message": f"{candidates[0].name} 환자가 여러 명 검색되었습니다. 예약할 환자를 선택해주세요.",
            "candidates": [_candidate_dict(c) for c in candidates],
            "approval_disabled": True,
            "note": "환자를 선택해야 예약을 등록할 수 있습니다.",
        }

    if len(candidates) == 1:
        return {
            "kind": "patient_confirmed",
            "candidates": [_candidate_dict(candidates[0])],
            "approval_disabled": False,
        }

    return {
        "kind": "patient_unknown",
        "candidates": [],
        "approval_disabled": True,
    }


def _candidate_dict(c: PatientCandidate) -> dict[str, Any]:
    return {
        "patient_id": c.patient_id,
        "chart_no": c.chart_no,
        "name": c.name,
        "birth_date": c.birth_date,
        "phone": c.phone,
    }


# ────────────────────────────── 치료항목 후보 카드 ──────────────────────────────


def build_treatment_candidate_panel(items: list[TreatmentItem]) -> dict[str, Any]:
    """치료항목 후보 패널.

    각 항목별: raw_text → matched_treatment_name (확인됨 / 선택 필요 / 충돌 / 없음).
    하나라도 미확정이면 approval_disabled=True.
    """
    rows = []
    needs_selection = False
    for ti in items:
        rows.append(
            {
                "raw_text": ti.raw_text,
                "matched_treatment_id": ti.matched_treatment_id,
                "matched_treatment_name": ti.matched_treatment_name,
                "status": ti.status.value,
                "candidates": ti.candidates,
            }
        )
        if ti.status.value != "db_verified":
            needs_selection = True

    return {
        "kind": "treatment_panel",
        "items": rows,
        "approval_disabled": needs_selection,
        "note": "치료항목을 모두 선택해야 예약을 등록할 수 있습니다." if needs_selection else "",
    }


# ────────────────────────────── 신환 등록 후보 카드 ──────────────────────────────


def build_new_patient_proposal(
    *,
    chart_no: str | None,
    name: str | None,
    birth_date: str | None,
    phone: str | None,
    duplicates: NewPatientDuplicateCheck,
    is_admin: bool = False,
) -> dict[str, Any]:
    """신환 등록 승인 카드 데이터.

    중복 검사 결과에 따라:
    - 중복 없음: 일반 직원 권한으로 승인 가능
    - 중복 있음: 관리자 권한 필요 (강제 등록)
    - 필수값 누락: 승인 불가
    """
    can_approve = (not duplicates.has_duplicates and not duplicates.missing_required) or (
        is_admin and not duplicates.missing_required
    )

    return {
        "kind": "new_patient_proposal",
        "title": "아래 환자를 신규 등록할까요?",
        "fields": {
            "chart_no": chart_no,
            "name": name,
            "birth_date": birth_date,
            "phone": phone,
        },
        "duplicates": asdict(duplicates),
        "approval_disabled": not can_approve,
        "needs_admin": duplicates.has_duplicates and not is_admin,
        "actions": ["취소", "신환 등록 승인" if can_approve else "관리자 승인 필요"],
    }


# ────────────────────────────── 최종 예약 후보 카드 ──────────────────────────────


def build_appointment_preview(
    *,
    patient: PatientCandidate | None,
    target_date: date | None,
    start_hour: int | None,
    start_minute: int = 0,
    therapist_name: str | None,
    treatment_items: list[TreatmentItem],
    validation: ValidationResult,
    date_note: str = "",
) -> dict[str, Any]:
    """최종 예약 후보 카드 — 환자 / 예약 정보 / 검증 결과 + 승인 / 취소 버튼.

    AI_FEATURE_MASTER_PLAN § 9 의 화면 예시 정합.
    """
    return {
        "kind": "appointment_preview",
        "title": "예약 후보",  # "예약 완료" 표현 금지
        "patient_info": _candidate_dict(patient) if patient else None,
        "appointment_info": {
            "date": target_date.isoformat() if target_date else None,
            "date_note": date_note,
            "time": (
                f"{start_hour:02d}:{start_minute:02d}"
                if start_hour is not None
                else None
            ),
            "therapist_name": therapist_name,
            "treatment_items": [
                {
                    "raw_text": ti.raw_text,
                    "matched_treatment_name": ti.matched_treatment_name,
                }
                for ti in treatment_items
            ],
        },
        "validation": {
            "can_approve": validation.can_approve,
            "checks": validation.checks,
            "issues": [
                {"code": i.code, "message": i.message, "severity": i.severity}
                for i in validation.issues
            ],
        },
        "prompt": "해당 날짜에 예약 등록할까요?",
        "approval_disabled": not validation.can_approve,
        "actions": ["취소", "예약 등록"],
    }
