"""ai_sms_prepare — Phase 9 예약문자 준비 AI (`prepare_sms` intent).

역할:
- 대상 날짜 (또는 "내일") 의 예약자 조회 → 환자별 문자 prefill 출력
- 체크박스 + 붙여넣기용 텍스트 생성
- **자동 발송 금지** (본 모듈은 발송 함수 자체를 노출하지 않음)
- 외부 AI API 호출 0 (provider 미사용)

설계:
- 본 모듈은 **read-only**. DB INSERT / UPDATE / DELETE / SMS 발송 ⊥.
- 환자 연락처 / 이름은 *내부 화면 표시용* — 외부 AI API 전송 ⊥
  (AI_SAFETY_POLICY § 3.2 환자 연락처 / 이름 전체 외부 전송 금지).
- 본 모듈을 외부 AI API provider 의 페이로드로 직접 사용 ⊥ — caller (router) 가 선별 후 외부 전송 결정.

cross-reference:
- 13 필드 정의 → AI_FEATURE_MASTER_PLAN.md § 5.3 (prepare_sms)
- 자동 발송 금지 → AI_SAFETY_POLICY.md § 1.1 #8 + § 1.2 #10 (연락처 전체 외부 전송 금지)
- 기존 sms_draft → app/services/ai/sms_draft.py (RAG 기반, 별개 도메인)

하네스: tests/test_phase09_ai_sms_prepare.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any


@dataclass
class SmsTargetRow:
    """문자 발송 대상 1건 — 환자별."""

    appointment_id: str
    patient_id: str
    patient_name: str
    patient_phone: str | None
    therapist_id: str | None
    therapist_name: str | None
    start_at: datetime
    treatment_codes: list[str] = field(default_factory=list)
    sms_text: str = ""
    selected: bool = True  # 체크박스 기본값


@dataclass
class SmsPreparation:
    """prepare_sms 결과 — 대상 + 출력 텍스트.

    output_paste 는 모든 selected=True 의 sms_text 를 줄바꿈으로 합친 *붙여넣기용* 출력.
    실제 발송은 사용자가 수동으로 외부 도구에 복사·붙여넣기.
    """

    target_date: date
    rows: list[SmsTargetRow] = field(default_factory=list)
    output_paste: str = ""
    note: str = ""


# ────────────────────────────── 1. 대상 조회 ──────────────────────────────


def prepare_sms_for_date(
    session: Any,
    *,
    target_date: date,
    therapist_id_filter: str | None = None,
    treatment_code_filter: str | None = None,
    template: str | None = None,
) -> SmsPreparation:
    """대상 날짜 예약자 조회 + 환자별 문자 prefill 생성.

    - status='canceled' 예약 자동 제외
    - therapist_id_filter / treatment_code_filter 선택 적용
    - template 기본값: "{name}님 안녕하세요. {date} {time} {therapist} {treatments} 예약 안내드립니다."
    - 대상 0명이면 note 에 안내 메시지 + rows 빈 리스트
    """
    from sqlalchemy import select

    from app.models.models import Appointment, Employee, Patient

    day_start = datetime.combine(target_date, time(0, 0))
    day_end = day_start + timedelta(days=1)

    stmt = (
        select(Appointment, Patient, Employee)
        .join(Patient, Patient.id == Appointment.patient_id)
        .outerjoin(Employee, Employee.id == Appointment.therapist_id)
        .where(Appointment.start_at >= day_start)
        .where(Appointment.start_at < day_end)
    )
    if therapist_id_filter:
        stmt = stmt.where(Appointment.therapist_id == therapist_id_filter)

    rows_db = list(session.execute(stmt).all())

    rows: list[SmsTargetRow] = []
    template_eff = template or _default_template()

    for appt, patient, therapist in rows_db:
        if getattr(appt, "status", None) == "canceled":
            continue
        codes = _parse_codes(appt.treatment_codes)
        if treatment_code_filter and treatment_code_filter not in codes:
            continue
        sms_text = _render(
            template_eff,
            name=patient.name,
            target_date=target_date,
            start_at=appt.start_at,
            therapist_name=therapist.name if therapist else "",
            treatment_codes=codes,
        )
        rows.append(
            SmsTargetRow(
                appointment_id=appt.id,
                patient_id=patient.id,
                patient_name=patient.name,
                patient_phone=patient.phone,
                therapist_id=therapist.id if therapist else None,
                therapist_name=therapist.name if therapist else None,
                start_at=appt.start_at,
                treatment_codes=codes,
                sms_text=sms_text,
                selected=True,
            )
        )

    rows.sort(key=lambda r: r.start_at)

    output_paste = "\n\n".join(r.sms_text for r in rows if r.selected)
    note = (
        "예약자가 0명입니다." if not rows else f"예약자 {len(rows)} 명 — 체크 후 복사·붙여넣기 하세요."
    )

    return SmsPreparation(
        target_date=target_date,
        rows=rows,
        output_paste=output_paste,
        note=note,
    )


def _default_template() -> str:
    return "{name}님 안녕하세요. {date} {time} {therapist} {treatments} 예약 안내드립니다."


def _parse_codes(raw: Any) -> list[str]:
    import json

    if not raw:
        return []
    if isinstance(raw, list):
        return list(raw)
    try:
        parsed = json.loads(raw)
        return list(parsed) if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _render(
    template: str,
    *,
    name: str,
    target_date: date,
    start_at: datetime,
    therapist_name: str,
    treatment_codes: list[str],
) -> str:
    return template.format(
        name=name,
        date=target_date.isoformat(),
        time=start_at.strftime("%H:%M"),
        therapist=therapist_name,
        treatments=" ".join(treatment_codes),
    ).strip()


# ────────────────────────────── 2. 체크박스 토글 ──────────────────────────────


def toggle_selection(
    preparation: SmsPreparation, *, appointment_ids: list[str]
) -> SmsPreparation:
    """선택된 appointment_id 의 selected 토글.

    output_paste 도 selected=True 만 합친 텍스트로 갱신.
    """
    target_ids = set(appointment_ids)
    for r in preparation.rows:
        if r.appointment_id in target_ids:
            r.selected = not r.selected
    preparation.output_paste = "\n\n".join(
        r.sms_text for r in preparation.rows if r.selected
    )
    return preparation


# ────────────────────────────── 3. preview ──────────────────────────────


def build_sms_preview(preparation: SmsPreparation) -> dict[str, Any]:
    """문자 준비 카드 — UI 직접 전달용.

    AI_SAFETY_POLICY § 1.1 #8 정합:
    - 발송 버튼은 caller (UI) 가 만들지 않거나, 만들더라도 본 모듈에서는 발송 함수 미제공.
    - 본 dict 의 actions 에 "발송" 없음 — 사용자가 직접 외부 도구 사용 (수동).
    """
    return {
        "kind": "sms_preparation",
        "title": "예약문자 준비",
        "target_date": preparation.target_date.isoformat(),
        "rows": [
            {
                "appointment_id": r.appointment_id,
                "patient_id": r.patient_id,
                "patient_name": r.patient_name,
                "patient_phone": r.patient_phone,
                "therapist_name": r.therapist_name,
                "start_at": r.start_at.isoformat(),
                "treatment_codes": r.treatment_codes,
                "sms_text": r.sms_text,
                "selected": r.selected,
            }
            for r in preparation.rows
        ],
        "output_paste": preparation.output_paste,
        "note": preparation.note,
        "actions": ["복사", "닫기"],  # "발송" 액션 ⊥
        "auto_send_disabled": True,
    }
