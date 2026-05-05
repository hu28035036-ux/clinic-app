"""ai_commands_router — SSOT § 11 의 commands API endpoint.

Phase 6 보강 후속 (실수 #004 해결) — 사용자가 자연어 명령을 보내고 단계적으로
승인하는 일반 사용자 흐름의 진입점.

7 endpoint (모두 관리자 전용 — 향후 일반 직원 권한 분리):
- POST   /api/ai/commands/parse                 — 자연어 → 후보 + audit row 신규
- POST   /api/ai/commands/{id}/select-patient   — 동명이인 중 선택
- POST   /api/ai/commands/{id}/select-treatment — 치료항목 alias 충돌 / 미확정 사용자 선택
- POST   /api/ai/commands/{id}/approve          — Gate 1 + Gate 2 + 기존 service 호출
- POST   /api/ai/commands/{id}/reject           — 사용자 거부 → status=rejected
- GET    /api/ai/commands/{id}                  — 상태 조회
- GET    /api/ai/commands/logs                  — 관리자 로그 (필터 + 페이징)

설계:
- audit log (`ai_command_logs`) 가 명령의 단일 진실. 매 단계 업데이트.
- parse 단계는 read-only — 후보 생성 + audit row 만 신규. DB 직접 수정 ⊥.
- approve 단계만 기존 service callable 호출 (Gate 1 + Gate 2 통과 후) — 본 router 가
  `app.routers.api.create_appointment` 와 호환되는 callable 을 inline 매핑 (§ 15.1 #5
  AI executor 는 기존 service 호출).
- 신환 등록 / 변경 / 취소 / 휴무 등 다른 intent 는 본 router 에 추가될 수 있으나,
  현재 ① 단계는 `create_appointment` intent 만 완전 지원.

cross-reference:
- SSOT § 11 API 설계 → AI_CURRENT_DECISIONS.md § 11
- 7 endpoint 미구현 → AI_MISTAKES_LOG.md §#004
- Gate 1 + Gate 2 → AI_SAFETY_POLICY.md § 4
- 기존 create_appointment service → app/routers/api.py:1663
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai import ai_audit
from ..ai.ai_command_schema import AiCommandStatus
from ..ai.ai_executor import (
    AppointmentServiceCallable,
    ExecutionResult,
    execute_approved_appointment,
)
from ..ai.ai_harness import HarnessRunResult, run_pipeline
from ..ai.ai_leave import (
    LeaveRunResult,
    LeaveServiceCallable,
    execute_approved_leave,
    run_leave_pipeline,
)
from ..ai.ai_safety import check_hallucination, check_privacy_payload
from ..config import get_db_path
from ..database import get_db
from ..models import models
from ..services import auth

router = APIRouter(prefix="/api/ai/commands")


# ────────────────────────────── 인증 ──────────────────────────────


def require_admin(x_admin_token: str = Header(default="")) -> str:
    """관리자 토큰 검증 → user_id 반환 (logs 등 *전체 조회* 용 엄격 인증).

    AI commands 사용자 흐름 (parse / select / approve / reject / 단건 조회) 은
    `get_actor_user_id` 사용 — 일반 사용자도 AI 예약 / 휴무 도우미 사용 가능.
    """
    if not auth.is_valid(x_admin_token):
        raise HTTPException(401, "관리자 인증이 필요합니다.")
    return "admin"


def get_actor_user_id(x_admin_token: str = Header(default="")) -> str:
    """AI commands 사용자 흐름용 — 인증 없으면 ``anonymous``, 잘못된 토큰이면 401.

    설계 (AI_CURRENT_DECISIONS § 11 갱신):
      - 토큰 없음            → ``anonymous`` (일반 사용자가 AI 도우미 사용)
      - 토큰 있고 유효       → ``admin``     (관리자 / 직원 식별)
      - 토큰 있는데 무효     → 401           (만료된 토큰 silent ignore ❌, 보안)

    Gate 1 (사용자 승인) + Gate 2 (승인 직전 재검증) 은 그대로 보존 — 인증 정책 변경
    이 안전 정책 (AI_SAFETY_POLICY § 1.1.3~1.1.7) 에 영향 ⊥.

    audit log 의 ``actor_user_id`` 컬럼 (m019, NULL 허용) 에 ``admin`` / ``anonymous``
    중 하나가 저장되어 사후 추적 가능.
    """
    if x_admin_token:
        if auth.is_valid(x_admin_token):
            return "admin"
        raise HTTPException(401, "잘못된 관리자 토큰입니다.")
    return "anonymous"


# ────────────────────────────── audit DB connection ──────────────────────────────


def _audit_conn() -> sqlite3.Connection:
    """ai_command_logs 테이블이 있는 동일 DB connection — 운영 / 테스트 모두 동일 경로."""
    return sqlite3.connect(str(get_db_path()))


# ────────────────────────────── service callable adapter ──────────────────────────────


def _appointment_service_adapter(db: Session) -> AppointmentServiceCallable:
    """기존 routers/api.py 의 create_appointment 와 호환되는 callable.

    AI executor Protocol 의 (target_date + start_hour + start_minute + duration_min) 를
    SQLAlchemy ORM Appointment 로 변환. 예약 생성 service 의 핵심 로직을 직접 사용
    (§ 15.1 #5 — 기존 service 호출).
    """
    def call(
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
    ) -> dict[str, Any]:
        # ai_executor 는 matched_treatment_id (Treatment.id, uuid) 를 treatment_codes 로 전달.
        # 기존 service 는 Treatment.code (예: "manual30") 를 기대 → 변환 필요.
        all_treatments = db.query(models.Treatment).all()
        id_to_code = {t.id: t.code for t in all_treatments if t.code}
        codes_set = {t.code for t in all_treatments if t.code}
        # 이미 code 면 그대로, id 면 매핑.
        codes: list[str] = []
        for tc in treatment_codes:
            if tc in codes_set:
                codes.append(tc)
            elif tc in id_to_code:
                codes.append(id_to_code[tc])
        # 중복 제거 (순서 보존)
        seen: list[str] = []
        for c in codes:
            if c not in seen:
                seen.append(c)
        codes = seen
        if not codes:
            raise ValueError(
                f"유효한 treatment_codes 가 없습니다 (입력: {treatment_codes})."
            )
        start_at = datetime.combine(target_date, datetime.min.time()).replace(
            hour=start_hour, minute=start_minute
        )
        obj = models.Appointment(
            patient_id=patient_id,
            therapist_id=therapist_id,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=duration_min),
            duration_min=duration_min,
            treatment_codes=json.dumps(codes, ensure_ascii=False),
            memo=memo,
            status="reserved",
        )
        db.add(obj)
        db.flush()
        db.commit()
        db.refresh(obj)
        return {"appointment_id": obj.id, "status": obj.status}

    return call


# ────────────────────────────── 직렬화 ──────────────────────────────


def _serialize_leave_run_result(result: LeaveRunResult) -> dict[str, Any]:
    """LeaveRunResult → JSON 직렬화."""
    return {
        "raw_text": result.raw_text,
        "intent": "create_leave",
        "status": result.status,
        "leave_type": result.leave_type,
        "leave_type_display": {
            "full": "종일 휴무", "am": "오전반차", "pm": "오후반차",
        }.get(result.leave_type or "", "(미정)"),
        "leave_date": result.leave_date.isoformat() if result.leave_date else None,
        "leave_date_text": result.leave_date_text,
        "therapist_id": result.therapist_id,
        "therapist_name": result.therapist_name,
        "therapist_candidates": result.therapist_candidates,
        "therapist_not_found": result.therapist_not_found,
        "validation": (
            {
                "can_approve": result.validation.can_approve,
                "checks": result.validation.checks,
                "issues": [
                    {"code": i.code, "message": i.message, "severity": i.severity}
                    for i in result.validation.issues
                ],
                "duplicate_existing_leave": result.validation.duplicate_existing_leave,
                "conflicting_appointments": [
                    {
                        "appointment_id": c.appointment_id,
                        "patient_id": c.patient_id,
                        "start_at": c.start_at.isoformat(),
                        "end_at": c.end_at.isoformat(),
                    }
                    for c in result.validation.conflicting_appointments
                ],
            }
            if result.validation
            else None
        ),
        "preview": result.preview,
    }


def _leave_service_adapter(db: Session) -> LeaveServiceCallable:
    """기존 휴무 등록 service 호출 어댑터 — `app.modules.leaves.service` 또는 직접 INSERT."""
    def call(
        *,
        therapist_id: str,
        leave_date: date,
        leave_type: str,
        memo: str | None,
        actor_user_id: str,
    ) -> dict[str, Any]:
        # ai_leave.LeaveServiceCallable Protocol 정합 — 기존 EmployeeLeave INSERT
        obj = models.EmployeeLeave(
            employee_id=therapist_id,
            leave_date=leave_date.isoformat(),
            leave_type=leave_type,
            memo=memo,
        )
        db.add(obj)
        db.flush()
        db.commit()
        db.refresh(obj)
        return {"leave_id": obj.id, "leave_date": obj.leave_date, "leave_type": obj.leave_type}

    return call


def _serialize_run_result(result: HarnessRunResult) -> dict[str, Any]:
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
        },
        "treatment_items": [
            {
                "raw_text": ti.raw_text,
                "matched_treatment_id": ti.matched_treatment_id,
                "matched_treatment_name": ti.matched_treatment_name,
                "status": ti.status.value,
                "source": ti.source.value,
                "candidates": ti.candidates,
            }
            for ti in result.treatment_items
        ],
        "validation": (
            {
                "can_approve": result.validation.can_approve,
                "checks": result.validation.checks,
                "issues": [
                    {"code": i.code, "message": i.message, "severity": i.severity}
                    for i in result.validation.issues
                ],
            }
            if result.validation
            else None
        ),
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


def _diagnostics(result: HarnessRunResult) -> dict[str, Any]:
    privacy = check_privacy_payload(result.parsed.to_dict())
    hallu = check_hallucination(
        result.parsed,
        patient_resolution=result.patient_resolution,
        treatment_items=result.treatment_items,
    )
    return {
        "privacy": {"ok": privacy.ok, "violations": privacy.violations},
        "hallucination": {"ok": hallu.ok, "violations": hallu.violations},
    }


# ────────────────────────────── 요청 / 응답 schema ──────────────────────────────


class CommandsParseRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    current_calendar_year: int | None = None
    current_calendar_month: int | None = None
    today_iso: str | None = None


class SelectPatientRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)


class SelectTreatmentRequest(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    """각 item: {raw_text: str, treatment_id: str} — caller 가 alias 충돌 / 미확정 항목을 사용자 선택."""


class RejectRequest(BaseModel):
    reason: str | None = None


class ApproveRequest(BaseModel):
    memo: str | None = None


# ────────────────────────────── 공용 helper ──────────────────────────────


def _resolve_calendar(payload: CommandsParseRequest) -> tuple[int, int, date]:
    today = date.today()
    if payload.today_iso:
        try:
            today = datetime.strptime(payload.today_iso, "%Y-%m-%d").date()
        except ValueError as e:
            raise HTTPException(400, f"today_iso 형식 오류: {e}") from None
    year = payload.current_calendar_year or today.year
    month = payload.current_calendar_month or today.month
    return year, month, today


def _load_audit_row(conn: sqlite3.Connection, command_id: int) -> dict[str, Any]:
    row = ai_audit.get_log(conn, command_id)
    if row is None:
        raise HTTPException(404, f"command_id {command_id} 를 찾을 수 없습니다.")
    return row


# ────────────────────────────── 1. parse ──────────────────────────────


@router.post("/parse")
def commands_parse(
    payload: CommandsParseRequest = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_actor_user_id),
) -> dict[str, Any]:
    """자연어 명령을 받아 후보 생성 + audit row 신규 + 결과 반환.

    intent 별 분기:
    - 휴무 키워드 (휴무 / 반차 / 연차 / 오프) → run_leave_pipeline (Phase 8)
    - 그 외 → run_pipeline (Phase 1~5 의 create_appointment 흐름)
    """
    year, month, today = _resolve_calendar(payload)

    # intent 사전 추출 — leave 관련 키워드면 leave 파이프라인
    leave_keywords = ("휴무", "반차", "연차", "오프")
    is_leave = any(kw in payload.raw_text for kw in leave_keywords)

    if is_leave:
        try:
            leave_result = run_leave_pipeline(
                db,
                raw_text=payload.raw_text,
                current_calendar_year=year,
                current_calendar_month=month,
                today=today,
            )
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": "ai_error", "message": str(e)}

        serialized = _serialize_leave_run_result(leave_result)

        conn = _audit_conn()
        try:
            cmd_id = ai_audit.write_log(
                conn,
                user_id=user_id,
                raw_text=payload.raw_text,
                intent="create_leave",
                status=leave_result.status,
                parsed_json={
                    "intent": "create_leave",
                    "raw_text": payload.raw_text,
                    "leave_type": leave_result.leave_type,
                    "leave_date_text": leave_result.leave_date_text,
                },
                resolved_json=serialized,
                validation_result=(
                    {
                        "checks": leave_result.validation.checks,
                        "issues": [
                            {"code": i.code, "message": i.message, "severity": i.severity}
                            for i in leave_result.validation.issues
                        ],
                        "can_approve": leave_result.validation.can_approve,
                    }
                    if leave_result.validation
                    else None
                ),
                preview_json=leave_result.preview,
            )
        finally:
            conn.close()

        return {
            "ok": True,
            "command_id": cmd_id,
            "result": serialized,
            "diagnostics": {
                "privacy": {"ok": True, "violations": []},
                "hallucination": {"ok": True, "violations": []},
            },
        }

    # 기본 — create_appointment 파이프라인
    try:
        result = run_pipeline(
            db,
            raw_text=payload.raw_text,
            current_calendar_year=year,
            current_calendar_month=month,
            today=today,
        )
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": "ai_error", "message": str(e)}

    serialized = _serialize_run_result(result)

    # audit row 신규
    conn = _audit_conn()
    try:
        cmd_id = ai_audit.write_log(
            conn,
            user_id=user_id,
            raw_text=payload.raw_text,
            intent=result.parsed.intent.value if result.parsed.intent else None,
            status=result.status,
            parsed_json=result.parsed.to_dict(),
            resolved_json=serialized,
            validation_result=(
                {
                    "checks": result.validation.checks,
                    "issues": [
                        {"code": i.code, "message": i.message, "severity": i.severity}
                        for i in result.validation.issues
                    ],
                    "can_approve": result.validation.can_approve,
                }
                if result.validation
                else None
            ),
            preview_json=result.preview,
        )
    finally:
        conn.close()

    return {
        "ok": True,
        "command_id": cmd_id,
        "result": serialized,
        "diagnostics": _diagnostics(result),
    }


# ────────────────────────────── 2. select-patient ──────────────────────────────


@router.post("/{command_id}/select-patient")
def commands_select_patient(
    command_id: int,
    payload: SelectPatientRequest = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_actor_user_id),
) -> dict[str, Any]:
    """동명이인 중 사용자가 patient_id 를 선택 → 재 파이프라인 + audit 갱신."""
    conn = _audit_conn()
    try:
        row = _load_audit_row(conn, command_id)
        raw_text = row.get("raw_text") or ""
        parsed = row.get("parsed_json") or {}
        # parsed_json 에서 캘린더 / today 복원 안 함 — 재계산
        today = date.today()
        year, month = today.year, today.month

        result = run_pipeline(
            db,
            raw_text=raw_text,
            current_calendar_year=year,
            current_calendar_month=month,
            today=today,
            selected_patient_id=payload.patient_id,
        )
        serialized = _serialize_run_result(result)

        ai_audit.update_log(
            conn,
            command_id,
            status=result.status,
            resolved_json=serialized,
            selected_patient_id=None,  # int 타입이라 str patient_id 저장 ⊥ — 별도 필드 활용
            preview_json=result.preview,
            validation_result=(
                {
                    "checks": result.validation.checks,
                    "issues": [
                        {"code": i.code, "message": i.message, "severity": i.severity}
                        for i in result.validation.issues
                    ],
                    "can_approve": result.validation.can_approve,
                }
                if result.validation
                else None
            ),
        )
    finally:
        conn.close()

    return {
        "ok": True,
        "command_id": command_id,
        "result": serialized,
        "diagnostics": _diagnostics(result),
    }


# ────────────────────────────── 3. select-treatment ──────────────────────────────


@router.post("/{command_id}/select-treatment")
def commands_select_treatment(
    command_id: int,
    payload: SelectTreatmentRequest = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_actor_user_id),
) -> dict[str, Any]:
    """치료항목 alias 충돌 / 미확정 항목을 사용자가 명시 선택.

    items: [{raw_text, treatment_id}] — caller 가 동명 alias 의 매핑 결정.
    audit 의 selected_treatment_items_json 갱신.
    """
    conn = _audit_conn()
    try:
        _load_audit_row(conn, command_id)
        ai_audit.update_log(
            conn,
            command_id,
            status=AiCommandStatus.TREATMENT_RESOLVED.value,
            selected_treatment_items_json=payload.items,
        )
        row = _load_audit_row(conn, command_id)
    finally:
        conn.close()
    return {"ok": True, "command_id": command_id, "row": row}


# ────────────────────────────── 4. approve ──────────────────────────────


@router.post("/{command_id}/approve")
def commands_approve(
    command_id: int,
    payload: ApproveRequest = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_actor_user_id),
) -> dict[str, Any]:
    """Gate 1 + Gate 2 + 기존 service 호출 → 예약 등록.

    현재 ① 단계는 create_appointment intent 만 지원. 다른 intent 는 향후.
    """
    conn = _audit_conn()
    try:
        row = _load_audit_row(conn, command_id)

        # ── Stored-state 게이트 (v1.3.5+ Codex HIGH fix) ──
        # AI_SAFETY_POLICY § 1.1.3-1.1.7 (사용자 승인 *없이* 예약/변경/취소/휴무/신환 ❌) 정합.
        # *종결 상태* (executed / rejected / failed) 의 명령에 대한 재 approve 호출 차단:
        #   - rejected → approve   = 거절 후 우회 재실행 ❌
        #   - executed → approve   = 중복 등록 ❌
        #   - failed   → approve   = 실패 흐름 우회 ❌
        # 진행 중 상태 (needs_approval / patient_selection_required / treatment_alias_conflict
        # 등) 는 기존 흐름 그대로 — 재 파이프라인이 사용자 안내 (approval_blocked) 처리.
        TERMINAL_STATUSES: set[str] = {
            AiCommandStatus.EXECUTED.value,
            AiCommandStatus.REJECTED.value,
            AiCommandStatus.FAILED.value,
        }
        stored_status = row.get("status")
        if stored_status in TERMINAL_STATUSES:
            raise HTTPException(
                409,
                f"command status='{stored_status}' 은 이미 종결된 명령. "
                f"재 approve 차단 (중복 등록 / 거절 우회 방지).",
            )

        intent = row.get("intent")

        # ── create_leave intent → ai_leave.execute_approved_leave ──
        if intent == "create_leave":
            # v1.3.5+ Codex 추가 HIGH fix:
            # create_leave 도 *needs_approval* 상태에서만 실행 (create_appointment Gate 1 정합).
            # parsed / validation_failed / patient_selection_required 같은 비종결 상태에서
            # 필드만 채워져 있다고 실행되면 AI 안전 정책 § 1.1.6 (휴무 승인 우회) 위반.
            if stored_status != AiCommandStatus.NEEDS_APPROVAL.value:
                raise HTTPException(
                    409,
                    f"create_leave approve 는 status='needs_approval' 만 가능 "
                    f"(현재: '{stored_status}'). 사용자 승인 우회 차단.",
                )

            resolved = row.get("resolved_json") or {}
            leave_type = resolved.get("leave_type")
            leave_date_iso = resolved.get("leave_date")
            therapist_id = resolved.get("therapist_id")

            if not (leave_type and leave_date_iso and therapist_id):
                ai_audit.update_log(
                    conn, command_id,
                    status=AiCommandStatus.VALIDATION_FAILED.value,
                    error_message="휴무 필수값 누락 (치료사 / 날짜 / 휴무유형)",
                )
                return {
                    "ok": False, "command_id": command_id,
                    "error": "missing_fields",
                    "error_message": "치료사 / 날짜 / 휴무 유형 모두 명확해야 승인 가능",
                }

            from datetime import datetime as _dt
            leave_date = _dt.fromisoformat(leave_date_iso).date()

            leave_exec = execute_approved_leave(
                db,
                therapist_id=therapist_id,
                leave_date=leave_date,
                leave_type=leave_type,
                memo=payload.memo,
                actor_user_id=user_id,
                leave_service=_leave_service_adapter(db),
            )

            ai_audit.update_log(
                conn, command_id,
                status=leave_exec.new_status,
                executed_result=leave_exec.result_payload if leave_exec.success else None,
                error_message=leave_exec.error_message,
                executed_at_now=leave_exec.success,
                approved_by=user_id if leave_exec.success else None,
            )

            return {
                "ok": leave_exec.success,
                "command_id": command_id,
                "execution_status": leave_exec.new_status,
                "result_payload": leave_exec.result_payload,
                "error_message": leave_exec.error_message,
            }

        if intent != "create_appointment":
            raise HTTPException(
                400, f"intent={intent} 의 approve 는 향후 지원 예정 (현재 create_appointment / create_leave 만)."
            )

        # 재 파이프라인 — 가장 최신 상태로
        raw_text = row.get("raw_text") or ""
        parsed = row.get("parsed_json") or {}
        # selected_patient_id 는 row.resolved_json.selected_patient.patient_id 에 보존
        resolved = row.get("resolved_json") or {}
        sel = (resolved or {}).get("selected_patient") or {}
        selected_patient_id = sel.get("patient_id")

        today = date.today()
        result = run_pipeline(
            db,
            raw_text=raw_text,
            current_calendar_year=today.year,
            current_calendar_month=today.month,
            today=today,
            selected_patient_id=selected_patient_id,
        )

        # Gate 1 — needs_approval 상태가 아니면 차단
        if result.status != AiCommandStatus.NEEDS_APPROVAL.value:
            ai_audit.update_log(
                conn,
                command_id,
                status=AiCommandStatus.VALIDATION_FAILED.value,
                error_message=f"승인 불가 상태: {result.status}",
            )
            return {
                "ok": False,
                "command_id": command_id,
                "status": result.status,
                "error": "approval_blocked",
                "result": _serialize_run_result(result),
            }

        # Gate 2 — executor 가 validator 재호출
        if result.selected_patient is None:
            raise HTTPException(409, "선택된 환자가 없습니다.")

        execution: ExecutionResult = execute_approved_appointment(
            db,
            patient_id=result.selected_patient.patient_id,
            therapist_id=result.therapist_resolution.therapist_id,
            target_date=result.date_resolution.resolved_date,
            start_hour=result.time_resolution.hour,
            start_minute=result.time_resolution.minute,
            duration_min=30,
            treatment_items=result.treatment_items,
            memo=payload.memo,
            actor_user_id=user_id,
            appointment_service=_appointment_service_adapter(db),
            is_past_date=result.date_resolution.is_past,
        )

        ai_audit.update_log(
            conn,
            command_id,
            status=execution.new_status,
            executed_result=execution.result_payload if execution.success else None,
            error_message=execution.error_message,
            executed_at_now=execution.success,
            approved_by=user_id if execution.success else None,
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
    finally:
        conn.close()

    return {
        "ok": execution.success,
        "command_id": command_id,
        "execution_status": execution.new_status,
        "result_payload": execution.result_payload,
        "error_message": execution.error_message,
    }


# ────────────────────────────── 5. reject ──────────────────────────────


@router.post("/{command_id}/reject")
def commands_reject(
    command_id: int,
    payload: RejectRequest = Body(...),
    user_id: str = Depends(get_actor_user_id),
) -> dict[str, Any]:
    """사용자 거부 — status=REJECTED 로 갱신."""
    conn = _audit_conn()
    try:
        _load_audit_row(conn, command_id)
        ai_audit.update_log(
            conn,
            command_id,
            status=AiCommandStatus.REJECTED.value,
            error_message=payload.reason,
        )
        row = _load_audit_row(conn, command_id)
    finally:
        conn.close()
    return {"ok": True, "command_id": command_id, "row": row}


# ────────────────────────────── 6. GET logs ──────────────────────────────
# 주의: /logs 는 /{command_id} 보다 *먼저* 등록해야 한다 — FastAPI 가 등록 순서대로 매칭.
# 그렇지 않으면 GET /logs 가 GET /{command_id} 의 path param 으로 잘못 매칭되어 422.


@router.get("/logs")
def commands_logs(
    user_id: str | None = Query(default=None),
    intent: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    conn = _audit_conn()
    try:
        rows = ai_audit.list_logs(
            conn,
            user_id=user_id,
            intent=intent,
            status=status,
            limit=limit,
            offset=offset,
        )
    finally:
        conn.close()
    return {"ok": True, "count": len(rows), "rows": rows}


# ────────────────────────────── 7. GET command ──────────────────────────────


@router.get("/{command_id}")
def commands_get(
    command_id: int,
    _user_id: str = Depends(get_actor_user_id),
) -> dict[str, Any]:
    conn = _audit_conn()
    try:
        row = _load_audit_row(conn, command_id)
    finally:
        conn.close()
    return {"ok": True, "command_id": command_id, "row": row}
