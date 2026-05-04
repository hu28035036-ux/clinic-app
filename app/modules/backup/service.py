"""백업 / 복구 응답 dict 빌더 + 정책 helper (19-12 신규).

19-11 stats.service / 19-10 sms.service 와 동일 패턴 — *byte-equivalent helper*.
백업/복구 본체 (``shutil.copy2`` / ``engine.dispose()`` / ``Path.replace``) 는
``app/services/backup.py`` / ``app/routers/api.py`` 가 그대로 보유. 라우터 무수정.

# COMPAT: 본 모듈의 모든 ``build_*`` 응답 빌더는 ``app/services/backup.py`` /
#         ``app/routers/api.py`` 의 인라인 동작과 *byte-equivalent*.

# SAFETY: 본 모듈은 *백업 메타데이터 직렬화* + *정책 상수* 만 — 운영 DB 파일 직접
#         read/write ⊥. ``shutil`` / ``sqlite3`` / ``engine`` 의존 ⊥.

# RISK: ``build_restore_ok_response`` 의 ``msg`` 문자열 (``f"{filename} 으로
#       복원됨. 서버를 재시작하세요."``) 은 UI 가 그대로 표시 — 본 19-12 가
#       *변경 ⊥*.

# NOTE: 본 모듈은 *읽기 / 응답 dict 조립 / 파일명 빌더* 만 — DB 변경 ⊥, 파일 시스템
#       변경 ⊥, 외부 API 호출 ⊥.
"""
from __future__ import annotations

from typing import Any

from .schemas import (
    BACKUP_PREFIX,
    BACKUP_SUFFIX,
    SAFETY_BACKUP_BEFORE_RESTORE_PREFIX,
    SAFETY_BACKUP_BEFORE_UPDATE_PREFIX,
)


# ──────────────── 백업 파일명 정책 helper ────────────────

def is_backup_filename(name: str) -> bool:
    """파일명이 백업 명명 규칙을 따르는지.

    NOTE: ``app/services/backup.py:list_backups`` 의 glob ``f"{BACKUP_PREFIX}*
    {BACKUP_SUFFIX}"`` 와 byte-equivalent.
    """
    if not name:
        return False
    return name.startswith(BACKUP_PREFIX) and name.endswith(BACKUP_SUFFIX)


def make_backup_filename(timestamp: str) -> str:
    """일반 백업 파일명 — ``app/services/backup.py:make_backup`` byte-equivalent.

    형식: ``clinic_<YYYYMMDD_HHMMSS>.db``.
    """
    return f"{BACKUP_PREFIX}{timestamp}{BACKUP_SUFFIX}"


def make_before_restore_filename(timestamp: str) -> str:
    """안전망 백업 (복구 직전) 파일명 — byte-equivalent.

    형식: ``clinic_before_restore_<YYYYMMDD_HHMMSS>.db``.

    RISK: ``restore_latest`` / ``restore_by_name`` / ``/api/restore`` 직전 자동
    생성. 복구 후 되돌리기 가능. 본 19-12 가 *변경 ⊥*.
    """
    return f"{SAFETY_BACKUP_BEFORE_RESTORE_PREFIX}{timestamp}{BACKUP_SUFFIX}"


def make_before_update_filename(version: str, timestamp: str) -> str:
    """업데이트 직전 백업 파일명 — ``app/routers/api.py:_backup_db_before_update``
    byte-equivalent.

    형식: ``clinic_before_update_v<version>_<YYYYMMDD_HHMMSS>.db``.

    RISK: ``apply-update`` 직전 SQLite online-backup API 로 생성.
    """
    return f"{SAFETY_BACKUP_BEFORE_UPDATE_PREFIX}{version}_{timestamp}{BACKUP_SUFFIX}"


# ──────────────── 응답 dict 빌더 ────────────────

def build_backup_list_row(
    *,
    name: str,
    path: str,
    size: int,
    mtime_iso: str,
) -> dict[str, Any]:
    """``GET /api/backup/list`` 응답 row dict — ``app/services/backup.py:list_backups``
    byte-equivalent."""
    return {
        "name": name,
        "path": path,
        "size": int(size),
        "mtime": mtime_iso,
    }


def build_make_backup_ok_response(*, name: str, size: int) -> dict[str, Any]:
    """``POST /api/backup/now`` 성공 응답 dict — ``make_backup`` ok=True 분기."""
    return {
        "ok": True,
        "name": name,
        "size": int(size),
    }


def build_make_backup_error_response(*, error: str) -> dict[str, Any]:
    """``POST /api/backup/now`` 실패 응답 dict — ``make_backup`` ok=False 분기."""
    return {
        "ok": False,
        "error": error,
    }


def build_restore_ok_response(*, restored_from: str) -> dict[str, Any]:
    """``POST /api/backup/restore-{latest,by-name}`` 성공 응답 dict —
    ``restore_latest`` / ``restore_by_name`` byte-equivalent.

    RISK: ``msg`` 문자열은 UI 가 그대로 표시 — 본 19-12 가 *변경 ⊥*.
    """
    return {
        "ok": True,
        "restored_from": restored_from,
        "msg": f"{restored_from} 으로 복원됨. 서버를 재시작하세요.",
    }


def build_restore_error_response(*, error: str) -> dict[str, Any]:
    """``POST /api/backup/restore-{latest,by-name}`` 실패 응답 dict."""
    return {
        "ok": False,
        "error": error,
    }


def build_backup_dir_response(*, path: str) -> dict[str, Any]:
    """``GET /api/backup/dir`` 응답 dict — byte-equivalent."""
    return {"path": path}


def build_legacy_restore_ok_response() -> dict[str, Any]:
    """``POST /api/restore`` (업로드 복구) 성공 응답 dict — byte-equivalent.

    NOTE: 메시지 문자열은 ``app/routers/api.py:restore`` 와 정합.
    """
    return {
        "ok": True,
        "msg": "복원 완료. 프로그램을 재시작하세요.",
    }


# ──────────────── 자동 백업 정책 helper ────────────────

def normalize_auto_backup_interval_min(value: int | None) -> int:
    """``SystemSetting.auto_backup_interval_min`` 정책 정규화 — ``app/routers/api.py:
    system_settings_set`` 의 ``max(5, v)`` 와 byte-equivalent.

    NOTE: 최소 5분 강제. ``None`` 이면 기본값 60분.
    """
    from .schemas import (
        AUTO_BACKUP_INTERVAL_MIN_DEFAULT,
        AUTO_BACKUP_INTERVAL_MIN_FLOOR,
    )

    try:
        v = int(value or AUTO_BACKUP_INTERVAL_MIN_DEFAULT)
    except (TypeError, ValueError):
        v = AUTO_BACKUP_INTERVAL_MIN_DEFAULT
    return max(AUTO_BACKUP_INTERVAL_MIN_FLOOR, v)


def normalize_auto_backup_keep_count(value: int | None) -> int:
    """``SystemSetting.auto_backup_keep_count`` 정책 정규화 — ``app/routers/api.py:
    system_settings_set`` 의 ``max(1, int(... or 30))`` 와 byte-equivalent.

    NOTE: 최소 1 강제. ``None`` 이면 기본값 30.
    """
    from .schemas import AUTO_BACKUP_KEEP_COUNT_DEFAULT

    try:
        v = int(value or AUTO_BACKUP_KEEP_COUNT_DEFAULT)
    except (TypeError, ValueError):
        v = AUTO_BACKUP_KEEP_COUNT_DEFAULT
    return max(1, v)
