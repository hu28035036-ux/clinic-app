"""modules.notes.service — 메모 read/write 통합 헬퍼 (post-19-P / 20-2 F-12).

19-7 의 ``rules.py`` (분류 / PII 마스킹) 위에 *환자 메모 + 예약 메모 통합 read/write*
헬퍼를 신설.

# COMPAT: 기존 ``api.py:update_patient_memo`` (PATCH /api/patients/{pid}/memo) 동작
#         보존 — 본 service 는 *별도 헬퍼* 진입점 (호출지에서 점진 위임).
#         응답 dict / API URL 변경 ⊥.

# SAFETY: 메모 원문 그대로 저장 (UI 가 평문 표시). 로그 / AI prompt 에는 본
#         service 미사용 — rules.mask_memo_for_log 별도 호출.

# NOTE: 사용자 §4-B 권장값 (a) — 19-7 notes/rules.py 와 통합. service 에서는
#       Patient.memo / Appointment.memo 둘 다 처리 (NOTE_KIND_* enum 정합).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Appointment, Patient
from app.modules.notes.rules import (
    NOTE_KIND_APPOINTMENT,
    NOTE_KIND_PATIENT,
    append_cancel_memo,
)


def get_patient_memo(db: Session, patient_id: str) -> Optional[str]:
    """Patient.memo 조회. 환자 부재 시 None."""
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    return p.memo if p else None


def update_patient_memo(db: Session, patient_id: str, memo: str) -> bool:
    """Patient.memo 갱신. 환자 부재 시 False, 갱신 성공 시 True.

    COMPAT: ``api.py:update_patient_memo`` (PATCH /api/patients/{pid}/memo)
    line 1444-1453 와 byte-equivalent 동작.
    """
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if p is None:
        return False
    p.memo = memo or ""
    db.commit()
    return True


def get_appointment_memo(db: Session, appointment_id: str) -> Optional[str]:
    """Appointment.memo 조회. 예약 부재 시 None."""
    a = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    return a.memo if a else None


def update_appointment_memo(db: Session, appointment_id: str, memo: str) -> bool:
    """Appointment.memo 갱신. 예약 부재 시 False, 갱신 성공 시 True."""
    a = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if a is None:
        return False
    a.memo = memo or ""
    db.commit()
    return True


def apply_cancel_memo_prefix(
    db: Session,
    appointment_id: str,
    cancel_reason: Optional[str] = None,
) -> bool:
    """취소 시 ``\\n[취소]`` 또는 ``\\n[취소] {reason}`` 자동 prefix.

    COMPAT: ``api.py:cancel_appointment`` line 2016 패턴 — rules.append_cancel_memo
    사용.
    """
    a = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if a is None:
        return False
    a.memo = append_cancel_memo(a.memo, cancel_reason)
    db.commit()
    return True


# 메모 종류별 read 헬퍼 (NOTE_KIND_* enum 분기)


def get_memo_by_kind(
    db: Session,
    *,
    note_kind: str,
    entity_id: str,
) -> Optional[str]:
    """NOTE_KIND 분기 — entity_id 기준 메모 조회.

    note_kind=patient → Patient.memo / appointment → Appointment.memo.
    부재 entity / 미지원 kind → None.
    """
    if note_kind == NOTE_KIND_PATIENT:
        return get_patient_memo(db, entity_id)
    if note_kind == NOTE_KIND_APPOINTMENT:
        return get_appointment_memo(db, entity_id)
    return None


__all__ = [
    "apply_cancel_memo_prefix",
    "get_appointment_memo",
    "get_memo_by_kind",
    "get_patient_memo",
    "update_appointment_memo",
    "update_patient_memo",
]
