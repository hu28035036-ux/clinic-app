"""AI 하네스 라우터 (Phase 6).

목적:
- `POST /api/ai/harness/run` (관리자 전용) — `app.ai.ai_harness.run_pipeline` 을
  HTTP 진입점으로 노출. 자연어 명령 → parse → resolve → validate → preview 까지
  read-only 결과 반환.
- 운영 환경에서 관리자 진단 / 디버깅 용도. 실제 예약 INSERT 는 본 endpoint 가
  하지 않음 (`run_pipeline` 자체가 read-only). 승인 + 실행은 별도 endpoint
  (Phase 7+) 에서.

설계 / 안전:
- `require_admin` 게이트 (X-Admin-Token 헤더) — AI_HARNESS_PLAN.md § 6
  ("운영 환경에서는 하네스 실행 권한 제한 (관리자만)").
- DB 직접 수정 0 — `run_pipeline` 만 호출.
- 외부 AI API 호출 0 — provider 미주입 시 정규식 fallback (Phase 2 와 동일).
- 운영 DB 사용 — 관리자가 의도적으로 운영 DB 에서 진단할 때 안전 (read-only).

cross-reference:
- AI_IMPLEMENTATION_PHASES.md § Phase 6 구현 대상 — `POST /api/ai/harness/run`
- AI_CURRENT_DECISIONS.md § 11 API 설계
- AI_HARNESS_PLAN.md § 3.3 진입점 / § 6 운영 / 개발 분리

테스트: tests/test_phase06_ai_harness_router.py
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai.ai_command_schema import AiCommandStatus
from ..ai.ai_harness import (
    HarnessRunResult,
    check_hallucination,
    check_privacy_payload,
    run_pipeline,
)
from ..database import get_db
from ..services import auth

router = APIRouter(prefix="/api/ai/harness")


def require_admin(x_admin_token: str = Header(default="")):
    """관리자 토큰 검증 — 기존 require_admin 패턴 재사용 (app/routers/api.py 와 동일 시그니처).

    AI_HARNESS_PLAN.md § 6 "운영 환경에서는 하네스 실행 권한 제한 (관리자만)" 강제.
    """
    if not auth.is_valid(x_admin_token):
        raise HTTPException(401, "관리자 인증이 필요합니다.")
    return True


# ────────────────────────────── 요청 / 응답 schema ──────────────────────────────


class HarnessRunRequest(BaseModel):
    """관리자 하네스 실행 요청 — 자연어 명령 + 옵션.

    selected_patient_id 는 동명이인 시 사용자 선택을 시뮬레이션하는 옵션.
    """

    raw_text: str = Field(..., min_length=1, description="자연어 명령 원문")
    current_calendar_year: int | None = Field(
        default=None, description="비우면 today 기준 년도"
    )
    current_calendar_month: int | None = Field(
        default=None, description="비우면 today 기준 월"
    )
    today_iso: str | None = Field(
        default=None, description="YYYY-MM-DD — 비우면 서버 today"
    )
    selected_patient_id: str | None = Field(
        default=None, description="동명이인 시 사용자 선택 시뮬레이션"
    )


# ────────────────────────────── 직렬화 헬퍼 ──────────────────────────────


def _serialize_treatment_items(items: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "raw_text": ti.raw_text,
            "matched_treatment_id": ti.matched_treatment_id,
            "matched_treatment_name": ti.matched_treatment_name,
            "source": ti.source.value,
            "status": ti.status.value,
            "candidates": ti.candidates,
        }
        for ti in items
    ]


def _serialize_validation(v: Any) -> dict[str, Any] | None:
    if v is None:
        return None
    return {
        "can_approve": v.can_approve,
        "checks": v.checks,
        "issues": [
            {"code": i.code, "message": i.message, "severity": i.severity}
            for i in v.issues
        ],
    }


def _serialize_run_result(result: HarnessRunResult) -> dict[str, Any]:
    """HarnessRunResult → JSON 직렬화 가능 dict.

    민감정보 (생년월일 / 연락처) 는 *내부 DB 에서만 조회된 값* 이므로
    관리자 진단 응답에 그대로 포함 (외부 AI API 전송 ≠ 관리자 응답).
    """
    return {
        "raw_text": result.raw_text,
        "status": result.status,
        "parsed": result.parsed.to_dict(),
        "patient_resolution": {
            "candidates": [
                {
                    "patient_id": c.patient_id,
                    "chart_no": c.chart_no,
                    "name": c.name,
                    "birth_date": c.birth_date,
                    "phone": c.phone,
                }
                for c in result.patient_resolution.candidates
            ],
            "mismatch": result.patient_resolution.mismatch,
            "not_found": result.patient_resolution.not_found,
            "match_rank": result.patient_resolution.match_rank,
        },
        "therapist_resolution": {
            "therapist_id": result.therapist_resolution.therapist_id,
            "therapist_name": result.therapist_resolution.therapist_name,
            "candidates": result.therapist_resolution.candidates,
            "not_found": result.therapist_resolution.not_found,
        },
        "date_resolution": {
            "resolved_date": (
                result.date_resolution.resolved_date.isoformat()
                if result.date_resolution.resolved_date
                else None
            ),
            "is_past": result.date_resolution.is_past,
            "is_ambiguous": result.date_resolution.is_ambiguous,
            "note": result.date_resolution.note,
        },
        "time_resolution": {
            "hour": result.time_resolution.hour,
            "minute": result.time_resolution.minute,
            "note": result.time_resolution.note,
        },
        "treatment_items": _serialize_treatment_items(result.treatment_items),
        "validation": _serialize_validation(result.validation),
        "preview": result.preview,
        "patient_panel": result.patient_panel,
        "treatment_panel": result.treatment_panel,
        "new_patient_proposal": result.new_patient_proposal,
        "selected_patient": (
            {
                "patient_id": result.selected_patient.patient_id,
                "chart_no": result.selected_patient.chart_no,
                "name": result.selected_patient.name,
                "birth_date": result.selected_patient.birth_date,
                "phone": result.selected_patient.phone,
            }
            if result.selected_patient
            else None
        ),
    }


# ────────────────────────────── endpoint ──────────────────────────────


@router.post("/run", dependencies=[Depends(require_admin)])
def run_harness(
    payload: HarnessRunRequest = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """관리자 전용 하네스 실행.

    1) `run_pipeline` 호출 (read-only — DB 변경 0)
    2) `check_privacy_payload` / `check_hallucination` 동시 실행
    3) JSON 직렬화하여 반환

    예약 / 환자 INSERT 는 본 endpoint 가 하지 않음 — 진단용.
    """
    # today / 캘린더 기본값
    today = date.today()
    if payload.today_iso:
        try:
            today = datetime.strptime(payload.today_iso, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(400, f"today_iso 형식 오류 (YYYY-MM-DD): {e}")
    year = payload.current_calendar_year or today.year
    month = payload.current_calendar_month or today.month

    try:
        result = run_pipeline(
            db,
            raw_text=payload.raw_text,
            current_calendar_year=year,
            current_calendar_month=month,
            today=today,
            selected_patient_id=payload.selected_patient_id,
        )
    except Exception as e:  # noqa: BLE001
        # AI_SAFETY_POLICY § 3.5 — AI 기능 실패가 기존 프로그램을 깨면 안 됨.
        # 본 endpoint 도 동일 — 500 대신 ai_error 로 안전 응답.
        return {
            "ok": False,
            "error": "ai_error",
            "message": str(e),
            "status": AiCommandStatus.FAILED.value,
        }

    serialized = _serialize_run_result(result)

    # 안전 진단 — Privacy / Hallucination
    privacy = check_privacy_payload(serialized.get("parsed"))
    hallucination = check_hallucination(
        result.parsed,
        patient_resolution=result.patient_resolution,
        treatment_items=result.treatment_items,
    )

    return {
        "ok": True,
        "result": serialized,
        "diagnostics": {
            "privacy": {"ok": privacy.ok, "violations": privacy.violations},
            "hallucination": {
                "ok": hallucination.ok,
                "violations": hallucination.violations,
            },
        },
    }
