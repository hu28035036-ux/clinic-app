"""F-7 privacy / retention 정책 (post-19-P / 20-1 그룹 A).

# NOTE: 사용자 §4-A 결정 (권장값):
#   - 환자: 비활성 18개월 (마지막 예약 기준) 후 PII 마스킹.
#   - AI 로그: 6개월 후 row 삭제.
# 두 정책 모두 schema 변경 ⊥ — 기존 ``Patient`` / ``AiUsageLog`` 컬럼만 활용.

# SAFETY: 본 헬퍼는 명시적 호출만 — 자동 트리거 ⊥ (admin endpoint / cron /
# 백업 시점 별도 결정). 운영 DB 안전 — 호출 전 백업 권장.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import AiUsageLog, Appointment, Patient

# 사용자 §4-A 결정 (권장값) — CLAUDE.md / 20-P-1 §4-A 정합
PATIENT_INACTIVE_MASK_MONTHS = 18
AI_LOG_RETENTION_MONTHS = 6

_MASK_NAME = "***"
_MASK_PHONE = "***-****-****"
_MASK_BIRTH = "****-**-**"
_MASK_CHART = ""


def _months_ago(months: int, *, now: Optional[datetime] = None) -> datetime:
    """N개월 전 시점 (단순 30일 곱 — 보존 정책 정확도 충분)."""
    base = now or datetime.utcnow()
    return base - timedelta(days=months * 30)


def mask_inactive_patients(
    db: Session,
    *,
    months: int = PATIENT_INACTIVE_MASK_MONTHS,
    now: Optional[datetime] = None,
    dry_run: bool = False,
) -> dict:
    """환자 비활성 N개월 후 PII 마스킹.

    기준: ``patients.id`` 가 ``appointments.patient_id`` 로 연결된 가장 최근
    ``Appointment.start_at`` 가 N개월 이전이거나, 예약 자체가 0건인 경우.

    마스킹 컬럼: ``name`` / ``phone`` / ``birth_date`` / ``chart_no`` / ``memo``.
    ``id`` / ``gender`` / ``created_at`` / ``updated_at`` 는 유지 (통계 기준 보존).

    인자:
      - ``months``: 비활성 임계 개월 (기본 18).
      - ``now``: 현재 시점 (테스트용 주입).
      - ``dry_run``: True 면 마스킹 대상만 반환 (DB 변경 ⊥).

    반환: ``{"candidates": int, "masked": int, "dry_run": bool}``
    """
    cutoff = _months_ago(months, now=now)
    candidates = []
    for patient in db.query(Patient).all():
        last_appt = (
            db.query(Appointment)
            .filter(Appointment.patient_id == patient.id)
            .order_by(Appointment.start_at.desc())
            .first()
        )
        # 마지막 예약 < cutoff → 비활성. 예약 0건이면 created_at 기준.
        if last_appt is None:
            if patient.created_at and patient.created_at < cutoff:
                candidates.append(patient)
        elif last_appt.start_at < cutoff:
            candidates.append(patient)

    masked = 0
    if not dry_run:
        for patient in candidates:
            # 이미 마스킹된 row 는 건너뛰기 (idempotent)
            if patient.name == _MASK_NAME:
                continue
            patient.name = _MASK_NAME
            patient.phone = _MASK_PHONE
            patient.birth_date = _MASK_BIRTH
            patient.chart_no = _MASK_CHART
            patient.memo = ""
            masked += 1
        if masked:
            db.commit()

    return {
        "candidates": len(candidates),
        "masked": masked,
        "dry_run": dry_run,
    }


def delete_old_ai_logs(
    db: Session,
    *,
    months: int = AI_LOG_RETENTION_MONTHS,
    now: Optional[datetime] = None,
    dry_run: bool = False,
) -> dict:
    """AI 로그 N개월 후 row 삭제.

    기준: ``AiUsageLog.ts < cutoff``.

    인자:
      - ``months``: 보존 개월 (기본 6).
      - ``now``: 현재 시점 (테스트용 주입).
      - ``dry_run``: True 면 후보 카운트만 (DB 변경 ⊥).

    반환: ``{"candidates": int, "deleted": int, "dry_run": bool}``
    """
    cutoff = _months_ago(months, now=now)
    q = db.query(AiUsageLog).filter(AiUsageLog.ts < cutoff)
    candidates = q.count()

    deleted = 0
    if not dry_run and candidates:
        deleted = q.delete(synchronize_session=False)
        db.commit()

    return {
        "candidates": candidates,
        "deleted": deleted,
        "dry_run": dry_run,
    }
