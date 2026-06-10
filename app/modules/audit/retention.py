"""F-8 audit_log 보존 / 자동 정리 정책 (post-19-P / 20-1 그룹 A).

# NOTE: 사용자 §4-A 결정 (권장값) — audit_log 5년 후 row 삭제.
# 19-12 audit 모듈 (service.py / schemas.py — PII 무저장 / 500자 cap) 보존.
# 본 retention 은 schema 변경 ⊥ — 정책 / 헬퍼만 신설.

# NOTE: 자동 트리거 — ``app/services/sync.py:run_daily_maintenance`` 가 일일
# 주기로 호출 (sync worker 루프, SyncOp prune 와 동일 주기). 명시적 단독 호출도 가능.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import AuditLog

# 사용자 §4-A 결정 (권장값) — CLAUDE.md / 20-P-1 §4-A 정합
AUDIT_LOG_RETENTION_YEARS = 5


def _years_ago(years: int, *, now: Optional[datetime] = None) -> datetime:
    """N년 전 시점 (단순 365일 곱 — 보존 정책 정확도 충분)."""
    base = now or datetime.utcnow()
    return base - timedelta(days=years * 365)


def delete_old_audit_logs(
    db: Session,
    *,
    years: int = AUDIT_LOG_RETENTION_YEARS,
    now: Optional[datetime] = None,
    dry_run: bool = False,
) -> dict:
    """audit_log N년 후 row 삭제.

    기준: ``AuditLog.ts < cutoff``.

    인자:
      - ``years``: 보존 년 (기본 5).
      - ``now``: 현재 시점 (테스트용 주입).
      - ``dry_run``: True 면 후보 카운트만 (DB 변경 ⊥).

    반환: ``{"candidates": int, "deleted": int, "dry_run": bool}``
    """
    cutoff = _years_ago(years, now=now)
    q = db.query(AuditLog).filter(AuditLog.ts < cutoff)
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
