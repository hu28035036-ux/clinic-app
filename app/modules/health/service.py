"""F-13 /api/health 통합 진단 service (post-19-P / 20-2 그룹 B).

# NOTE: 사용자 §4-B 결정값 — 6개 키 모두 (db_ok / migration_version /
# backup_age / disk_free / version / uptime). 19-2 facade 의 AI 상태 키와는
# 별개 — /api/health 는 *서버 전체* 진단.

# SAFETY: 외부 API 호출 ⊥ — 모든 진단은 로컬 (DB ping / 파일 시스템 / config).
# API key / PII 원문 노출 ⊥.
"""
from __future__ import annotations

import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import APP_VERSION, get_appdata_dir, get_backup_dir
from app.database import SCHEMA_VERSION, SessionLocal
from app.models.models import Patient

# 서버 startup 시점 기록 — uptime 계산용. main.py 에서 set_startup_time() 호출.
_STARTUP_TIME: Optional[float] = None


def set_startup_time(now: Optional[float] = None) -> None:
    """서버 startup 시점 기록 (uptime 기준)."""
    global _STARTUP_TIME
    _STARTUP_TIME = now if now is not None else time.time()


def _get_uptime_seconds() -> int:
    """startup 시점 이후 경과 초. set_startup_time 미호출 시 0."""
    if _STARTUP_TIME is None:
        return 0
    return int(time.time() - _STARTUP_TIME)


def _check_db_ok() -> bool:
    """DB 연결 + 단순 query 가능 여부."""
    try:
        db = SessionLocal()
        try:
            # 가장 가벼운 query — 환자 카운트 (테이블 존재 + 연결 확인)
            db.query(Patient).limit(1).first()
            return True
        finally:
            db.close()
    except Exception:
        return False


def _get_backup_age_seconds() -> Optional[int]:
    """가장 최근 백업 파일 mtime 기준 경과 초. 백업 0건이면 None."""
    try:
        backup_dir = get_backup_dir()
        if not backup_dir.exists():
            return None
        files = sorted(backup_dir.glob("clinic_*.db"), reverse=True)
        if not files:
            return None
        latest = files[0]
        mtime = latest.stat().st_mtime
        return int(time.time() - mtime)
    except Exception:
        return None


def _get_disk_free_bytes() -> Optional[int]:
    """AppData 폴더 디스크 여유 공간 (bytes). 측정 실패 시 None."""
    try:
        appdata = get_appdata_dir()
        usage = shutil.disk_usage(str(appdata))
        return int(usage.free)
    except Exception:
        return None


def collect_health_snapshot() -> dict:
    """/api/health 응답 dict — 사용자 §4-B 권장 6개 키.

    반환 키:
      - ``db_ok``: bool — DB 연결 가능.
      - ``migration_version``: int — schema_migrations 기준 마이그레이션 번호.
      - ``backup_age``: int | None — 가장 최근 백업 후 경과 초.
      - ``disk_free``: int | None — AppData 디스크 여유 bytes.
      - ``version``: str — APP_VERSION.
      - ``uptime``: int — 서버 startup 후 경과 초.

    # SAFETY: API key / PII 원문 미포함. 외부 API 호출 ⊥.
    """
    return {
        "db_ok": _check_db_ok(),
        "migration_version": SCHEMA_VERSION,
        "backup_age": _get_backup_age_seconds(),
        "disk_free": _get_disk_free_bytes(),
        "version": APP_VERSION,
        "uptime": _get_uptime_seconds(),
    }


# 응답 키 셋 (테스트 contract 잠금용)
HEALTH_SNAPSHOT_KEYS = frozenset({
    "db_ok",
    "migration_version",
    "backup_age",
    "disk_free",
    "version",
    "uptime",
})
