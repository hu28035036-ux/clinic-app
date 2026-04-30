"""AI 예약문자 초안 생성 서비스 (v1.3 단계 4 / 세션 04, 세션 09 보강).

엄수 정책:
  - AI 가 SMS 를 직접 발송하지 않음 (POST /api/sms/send 호출 금지)
  - AI 가 DB 를 수정하지 않음 (read-only)
  - LLM 으로 PII 미전송: 전화번호 / 생년월일 / 차트번호 / 환자 메모 / 예약 메모 /
    직원 개인정보. 환자명은 토큰('환자A') 화 후 전달, 응답에서 실명 복원.
  - 취소 예약은 초안 생성 X — "취소 상태라 ..." 안내만.
  - 결과는 사용자 확인 후 발송하는 구조 (`needs_user_confirm=True`).

세션 09 보강:
  - extra_note 에 PII 가 포함되면 차단 (기존엔 safe_ctx 만 검사).
  - LLM 응답을 DB 컨텍스트와 비교 — 환각 치료사명 / 변경된 시간 / 실행 완료 표현
    탐지 시 차단.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ...models import models
from . import pii as pii_mod
from . import prompts as prompts_mod
from . import provider as provider_mod
from ..rag import search as rag_search


_KOR_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


# ── 응답 검증 패턴 (세션 09) ──
# 실행 완료 오인 표현 — AI 가 직접 발송/변경했다고 거짓 진술하면 위험
_RE_DRAFT_EXECUTION_CLAIM = re.compile(
    r"(문자\s*[를을]?\s*발송했|예약\s*[을를]?\s*변경했|"
    r"발송\s*완료\s*했|예약\s*확정\s*했|"
    r"설정\s*[을를]?\s*변경했|환자\s*정보\s*[를을]?\s*변경했)"
)

# 의료 단정 표현 (sms 안에 들어가면 위험)
_RE_DRAFT_MEDICAL_CLAIM = re.compile(
    r"(완치|반드시\s*치료|확실히\s*효과|진단됩니다)"
)

# 시간 패턴 (M월 D일, HH:MM)
_RE_DATE = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_RE_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")

# 치료사 추측 패턴 — "<한글이름> 선생|원장|치료사"
_RE_FAKE_THERAPIST = re.compile(
    r"([가-힣]{2,4})\s*(선생님|원장|치료사|기사|기사님|쌤)"
)


@dataclass
class DraftContext:
    """초안 생성 컨텍스트.

    `safe_ctx` 는 LLM 으로 보내는 부분, `real_name` 은 서버에만 보관.
    """
    appointment_id: str
    real_name: str = ""
    patient_token: str = "환자A"
    treatment_summary: str = ""
    reserved_at_label: str = ""
    therapist_name: str = ""
    clinic_name: str = ""
    clinic_phone: str = ""
    status: str = ""
    missing_fields: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    safe_ctx: dict = field(default_factory=dict)


def _format_reserved_at(start_at: Optional[datetime]) -> str:
    if start_at is None:
        return ""
    wd = _KOR_WEEKDAYS[start_at.weekday()]
    return f"{start_at.month}월 {start_at.day}일 ({wd}) {start_at.hour:02d}:{start_at.minute:02d}"


def _treatment_names(db: Session, codes: list) -> list:
    if not codes:
        return []
    rows = (
        db.query(models.Treatment)
        .filter(models.Treatment.code.in_(codes))
        .all()
    )
    by_code = {r.code: r.name for r in rows}
    return [by_code.get(c, c) for c in codes]


def build_draft_context(db: Session, appointment_id: str) -> DraftContext:
    """예약 1건 → DraftContext.

    LLM 호출 전 단계. 누락/취소 등 정책 위반은 호출자가 판단할 수 있도록
    status / missing_fields / warnings 에 기록.
    """
    sms_setting = (
        db.query(models.SmsSetting)
        .filter(models.SmsSetting.id == 1)
        .first()
    )
    clinic_name = (sms_setting.clinic_name if sms_setting else "") or ""
    clinic_phone = (sms_setting.clinic_phone if sms_setting else "") or ""

    appt = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == str(appointment_id))
        .first()
    )
    if appt is None:
        return DraftContext(
            appointment_id=str(appointment_id),
            clinic_name=clinic_name,
            clinic_phone=clinic_phone,
            status="not_found",
            missing_fields=["appointment"],
        )

    patient = appt.patient
    real_name = (patient.name if patient else "") or ""
    patient_token = pii_mod.tokenize_patient_name(real_name, 0)

    try:
        codes = json.loads(appt.treatment_codes or "[]")
        if not isinstance(codes, list):
            codes = []
    except Exception:
        codes = []
    treatment_names = _treatment_names(db, codes)
    treatment_summary = ", ".join(treatment_names)

    therapist_name = ""
    if appt.therapist_id:
        therapist = (
            db.query(models.Employee)
            .filter(models.Employee.id == appt.therapist_id)
            .first()
        )
        therapist_name = (therapist.name if therapist else "") or ""

    reserved_at_label = _format_reserved_at(appt.start_at)

    missing_fields: list = []
    warnings: list = []
    if not appt.start_at:
        missing_fields.append("예약시간")
    if not codes:
        warnings.append("치료항목이 비어 있어 일반 안내 문구로 작성됩니다.")
        missing_fields.append("치료항목")
    if not therapist_name:
        warnings.append("담당 치료사가 미배정 상태입니다. 치료사명 없이 작성됩니다.")

    safe_ctx = pii_mod.build_safe_appointment_context(
        patient_name_token=patient_token,
        treatment_summary=treatment_summary,
        reserved_at_label=reserved_at_label,
        clinic_name=clinic_name,
        clinic_phone=clinic_phone,
    )
    if therapist_name:
        # 배정된 경우만 포함 — 미배정이면 LLM 이 추측 못 하도록 키 자체 미존재
        safe_ctx["therapist"] = therapist_name

    return DraftContext(
        appointment_id=str(appointment_id),
        real_name=real_name,
        patient_token=patient_token,
        treatment_summary=treatment_summary,
        reserved_at_label=reserved_at_label,
        therapist_name=therapist_name,
        clinic_name=clinic_name,
        clinic_phone=clinic_phone,
        status=appt.status or "",
        missing_fields=missing_fields,
        warnings=warnings,
        safe_ctx=safe_ctx,
    )


def _build_prompt(
    ctx: DraftContext,
    *,
    tone: str,
    extra_note: str,
    rag_snippets: list,
) -> tuple[str, str]:
    tone_label = "친근하고 정중한" if tone == "friendly" else "정중하고 격식 있는"
    therapist_clause = (
        f"치료사명: {ctx.therapist_name}"
        if ctx.therapist_name
        else "치료사: (미배정 — 치료사명을 절대 추측해 만들지 말 것. 치료사 관련 문구 자체 생략)"
    )
    treatment_clause = (
        f"치료항목: {ctx.treatment_summary}"
        if ctx.treatment_summary
        else "치료항목: (미지정 — 일반 안내로 작성)"
    )

    rag_block = ""
    if rag_snippets:
        rag_block = "\n\n[톤 가이드 참고]\n"
        for s in rag_snippets[:3]:
            title = s.get("title", "")
            snippet = (s.get("snippet", "") or "")[:240]
            rag_block += f"- {title}\n{snippet}\n"

    user_prompt = (
        f"다음 예약에 대한 SMS 본문 1개를 {tone_label} 톤으로 작성하세요.\n"
        f"환자(토큰): {ctx.patient_token}  ← 응답에 이 토큰을 그대로 사용\n"
        f"병원명: {ctx.clinic_name}\n"
        f"병원전화: {ctx.clinic_phone}\n"
        f"예약시간: {ctx.reserved_at_label}\n"
        f"{treatment_clause}\n"
        f"{therapist_clause}\n"
    )
    if extra_note:
        user_prompt += f"추가 안내: {extra_note}\n"
    user_prompt += (
        "\n조건:\n"
        f"- 70~120자 (CP949 인코딩 기준)\n"
        f"- 환자명은 '{ctx.patient_token}' 토큰을 그대로 사용 (실명 추측 금지)\n"
        "- 치료사 미배정이면 치료사 관련 문구 생략 (이름 만들어 쓰기 금지)\n"
        "- 이모지 / 영문 특수기호 사용 금지\n"
        "- 본문만 출력 (제목/주석/설명 금지)\n"
        + rag_block
    )

    return prompts_mod.SMS_SUGGEST_SYSTEM, user_prompt


def _restore_name(text: str, token: str, real_name: str) -> str:
    if not text or not real_name or not token:
        return text or ""
    return text.replace(token, real_name)


def _verify_draft_against_ctx(text: str, ctx: "DraftContext") -> dict:
    """LLM 응답을 DB 컨텍스트와 비교 — 환각 / 실행 오인 / 의료 단정 탐지.

    반환:
      {
        "blocked": bool,
        "reason": str,           # 영문 short, error_detail 용
        "warnings": list[str],   # 사용자에게 보여줄 경고 (한국어, 차단까지는 아닌 것)
        "guard_hits": int,
      }
    """
    out = {"blocked": False, "reason": "", "warnings": [], "guard_hits": 0}
    if not text:
        return out

    # 1) 실행 완료 오인 표현
    if _RE_DRAFT_EXECUTION_CLAIM.search(text):
        out["blocked"] = True
        out["reason"] = "execution claim blocked"
        out["guard_hits"] += 1
        return out

    # 2) 의료 단정 표현
    if _RE_DRAFT_MEDICAL_CLAIM.search(text):
        out["blocked"] = True
        out["reason"] = "unsafe medical advice"
        out["guard_hits"] += 1
        return out

    # 3) 치료사 미배정인데 응답에 치료사 이름이 있으면 차단
    if not ctx.therapist_name:
        m = _RE_FAKE_THERAPIST.search(text)
        if m:
            out["blocked"] = True
            out["reason"] = "invented therapist"
            out["guard_hits"] += 1
            return out

    # 4) 예약 시간이 DB 와 다르면 차단
    if ctx.reserved_at_label:
        date_m = _RE_DATE.search(ctx.reserved_at_label)
        time_m = _RE_TIME.search(ctx.reserved_at_label)
        # 응답에 들어 있는 다른 시간 패턴
        for tm in _RE_TIME.finditer(text):
            if time_m and (tm.group(1), tm.group(2)) != (time_m.group(1), time_m.group(2)):
                out["blocked"] = True
                out["reason"] = "invented appointment time"
                out["guard_hits"] += 1
                return out
        for dm in _RE_DATE.finditer(text):
            if date_m and (dm.group(1), dm.group(2)) != (date_m.group(1), date_m.group(2)):
                out["blocked"] = True
                out["reason"] = "invented appointment date"
                out["guard_hits"] += 1
                return out

    return out


def make_draft(
    db: Session,
    *,
    appointment_id: str,
    tone: str = "friendly",
    extra_note: str = "",
    provider_override: Optional[provider_mod.AiProvider] = None,
) -> dict:
    """초안 생성 진입점.

    반환 dict 필드:
      draft              : 본문 또는 안내 문구
      warnings           : 사용자에게 보여줄 주의사항
      missing_fields     : 누락된 필드 목록
      context_used       : LLM 으로 보낸 컨텍스트 (실명 제외)
      needs_user_confirm : 사용자 확인 후 발송 필요 (항상 True, 단 skipped=True 면 False)
      skipped            : 초안 생성을 건너뛰었는지
      skip_reason        : '' | 'cancelled' | 'no_appointment' | 'no_appt_time'
    """
    ctx = build_draft_context(db, appointment_id)

    # ── 정책: 취소 예약은 초안 생성 X (LLM 호출 X) ──
    if ctx.status == "canceled":
        return {
            "draft": "취소 상태라 예약문자 초안 생성 대상이 아닙니다.",
            "warnings": [],
            "missing_fields": [],
            "context_used": {
                "appointment_id": ctx.appointment_id,
                "status": "canceled",
            },
            "needs_user_confirm": False,
            "skipped": True,
            "skip_reason": "cancelled",
        }

    # ── 예약 자체가 없음 ──
    if ctx.status == "not_found":
        return {
            "draft": "해당 예약을 찾을 수 없습니다.",
            "warnings": [],
            "missing_fields": ctx.missing_fields,
            "context_used": {"appointment_id": ctx.appointment_id},
            "needs_user_confirm": False,
            "skipped": True,
            "skip_reason": "no_appointment",
        }

    # ── 예약시간 누락 → 생성 거부 ──
    if not ctx.reserved_at_label:
        return {
            "draft": (
                "예약 시간이 지정되지 않아 초안을 생성할 수 없습니다. "
                "예약 시간을 먼저 입력해 주세요."
            ),
            "warnings": list(ctx.warnings),
            "missing_fields": ctx.missing_fields,
            "context_used": {
                "appointment_id": ctx.appointment_id,
                "patient_token": ctx.patient_token,
            },
            "needs_user_confirm": False,
            "skipped": True,
            "skip_reason": "no_appt_time",
        }

    # ── extra_note PII 검사 (세션 09 신규 / 세션 10 보강) ──
    # 사용자가 추가 안내에 환자 전화번호/생년월일을 적어 넣어 LLM 으로 새는 경로 차단.
    # 차트번호(chart_no_maybe)는 has_blocking 대상은 아니지만 마스킹된 cleaned 값을
    # LLM 으로 보내야 함 — 원본을 그대로 보내면 차트번호 원문이 외부 LLM 으로 유출됨.
    sanitized_note = ""
    if extra_note:
        note_scan = pii_mod.assert_safe_for_external(extra_note)
        if note_scan.has_blocking:
            raise ValueError(
                "PII 가드: 추가 안내(extra_note)에 차단 대상이 포함됨 "
                f"(종류: {sorted(note_scan.found.keys())})"
            )
        sanitized_note = note_scan.cleaned

    # ── PII 가드 (마지막 안전망) ──
    # clinic_phone 은 공공 정보 (병원 대표번호) — 환자/직원 PII 가 아니므로 스캔 제외.
    # 환자/직원 전화·생년월일·차트번호 가 safe_ctx 어딘가에 침투했을 때만 차단.
    scan_target = {
        k: v for k, v in ctx.safe_ctx.items()
        if k != "clinic_phone"
    }
    safe_payload_str = json.dumps(scan_target, ensure_ascii=False)
    pii_scan = pii_mod.assert_safe_for_external(safe_payload_str)
    if pii_scan.has_blocking:
        raise ValueError(
            "PII 가드: 외부 LLM 으로 전송할 컨텍스트에 차단 대상이 포함됨 "
            f"(종류: {sorted(pii_scan.found.keys())})"
        )

    # ── RAG: 톤 가이드 검색 (실패해도 LLM 호출은 진행) ──
    rag_results: list = []
    try:
        rag_results = rag_search.search(
            f"tone_{tone}",
            category="sms_guides",
            limit=3,
        )
    except Exception:
        rag_results = []

    # ── LLM 호출 ──
    if provider_override is None:
        raise RuntimeError(
            "provider_override 가 None — 라우터에서 provider 인스턴스를 주입해야 합니다."
        )
    system_prompt, user_prompt = _build_prompt(
        ctx, tone=tone, extra_note=sanitized_note,
        rag_snippets=rag_results,
    )
    result = provider_override.generate(user_prompt, system=system_prompt)
    raw_text = (result.text or "").strip()

    # 토큰 → 실명 복원 (서버 측에서만)
    draft_text = _restore_name(raw_text, ctx.patient_token, ctx.real_name)

    # 응답 텍스트 PII 후처리 안전망 — LLM 환각으로 만들어진 전화/생년월일은 마스킹
    out_scan = pii_mod.scan(draft_text)
    pii_hits_in_resp = sum(len(v) for v in out_scan.found.values()) if out_scan.found else 0
    if out_scan.has_blocking:
        draft_text = out_scan.cleaned

    # ── 응답 검증 (세션 09 신규) ──
    verify = _verify_draft_against_ctx(draft_text, ctx)
    extra_warnings: list = []
    blocked = bool(verify.get("blocked"))
    blocked_reason = verify.get("reason", "")
    if blocked:
        # 차단된 응답은 안내문구로 대체 — 사용자는 발송 불가 상태로 알게 됨
        draft_text = (
            "AI 초안이 검증 단계에서 차단되었습니다. "
            "예약 정보를 다시 확인하고 직접 작성해 주세요."
        )
        extra_warnings.append(
            "AI 응답 검증 실패: " + (blocked_reason or "unknown")
        )

    context_used = {
        "appointment_id": ctx.appointment_id,
        "patient_token": ctx.patient_token,
        "treatment_summary": ctx.treatment_summary,
        "reserved_at_label": ctx.reserved_at_label,
        "therapist_name": ctx.therapist_name,
        "clinic_name": ctx.clinic_name,
        "tone": tone,
        "rag_sources": [r.get("path", "") for r in rag_results],
    }

    return {
        "draft": draft_text,
        "warnings": list(ctx.warnings) + extra_warnings,
        "missing_fields": ctx.missing_fields,
        "context_used": context_used,
        "needs_user_confirm": not blocked,
        "skipped": False,
        "skip_reason": "",
        # 세션 09 — 라우터/로깅용 (UI 무시 가능)
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "guard_hits": pii_hits_in_resp + int(verify.get("guard_hits", 0)),
        "prompt_text": user_prompt,
        "response_text": draft_text,
    }
