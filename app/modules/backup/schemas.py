"""백업 / 복구 API 응답 키 contract 상수 (19-12 신규).

frozenset 으로 응답 key 셋 보존. contract 테스트가 인라인 응답 dict 와 본 상수의
key 셋 비교 → 임의 변경 검출.

# COMPAT: 본 frozenset 상수의 *원소 변경 ⊥* — 관리자탭 백업 섹션 / 복구 버튼 /
#         자동 업데이트 직전 백업 안내 UI 의존. contract 테스트가 회귀 검출.

# SAFETY: 응답에 *운영 DB 절대경로 부재 보장* (관리자탭이 읽는 ``path`` 는 백업
#         파일 경로). 환자 PII / API key / sync_secret 평문 부재.

# RISK: 응답 row 의 ``size`` (bytes) / ``mtime`` (ISO) 타입 변경 ⊥ — UI 정렬 /
#       표시 의존.
"""
from __future__ import annotations


# ──────────────── /api/backup/list (행 단위 응답) ────────────────

# GET /api/backup/list 응답 dict row key 4개.
BACKUP_LIST_ROW_KEYS: frozenset[str] = frozenset({
    "name",
    "path",
    "size",
    "mtime",
})


# ──────────────── /api/backup/now (성공 / 실패) ────────────────

# POST /api/backup/now 성공 응답 (``make_backup`` ok=True 분기) — `ok`/`name`/`size`.
BACKUP_NOW_OK_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "name",
    "size",
})

# POST /api/backup/now 실패 응답 (``make_backup`` ok=False 분기) — `ok`/`error`.
BACKUP_NOW_ERROR_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "error",
})


# ──────────────── /api/backup/restore-{latest,by-name} ────────────────

# POST /api/backup/restore-latest / restore-by-name 성공 응답.
BACKUP_RESTORE_OK_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "restored_from",
    "msg",
})

# POST /api/backup/restore-latest / restore-by-name 실패 응답.
BACKUP_RESTORE_ERROR_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "error",
})


# ──────────────── /api/backup/dir ────────────────

# GET /api/backup/dir 응답.
BACKUP_DIR_RESPONSE_KEYS: frozenset[str] = frozenset({
    "path",
})


# ──────────────── /api/restore (legacy 업로드 복구) ────────────────

# POST /api/restore 성공 응답 — ``ok``/``msg``.
RESTORE_OK_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "msg",
})


# ──────────────── 자동 업데이트 직전 백업 메타 (about/apply-update.backup) ────────────────

# ``apply-update`` 응답의 ``backup`` 필드 — 성공.
APPLY_UPDATE_BACKUP_OK_KEYS: frozenset[str] = frozenset({
    "ok",
    "path",
    "filename",
    "size_mb",
})

# ``apply-update`` 응답의 ``backup`` 필드 — 실패.
APPLY_UPDATE_BACKUP_ERROR_KEYS: frozenset[str] = frozenset({
    "ok",
    "error",
})


# ──────────────── 백업 파일 prefix/suffix 정책 상수 (단일 원천) ────────────────

# COMPAT: ``app/services/backup.py:BACKUP_PREFIX`` / ``BACKUP_SUFFIX`` 와
#         byte-equivalent. 본 19-12 가 *변경 ⊥*.
BACKUP_PREFIX: str = "clinic_"
BACKUP_SUFFIX: str = ".db"

# 안전망 백업 prefix (``restore`` 직전 / ``restore_latest`` 직전 / ``restore_by_name``
# 직전 / ``apply-update`` 직전 자동 생성).
SAFETY_BACKUP_BEFORE_RESTORE_PREFIX: str = "clinic_before_restore_"
SAFETY_BACKUP_BEFORE_UPDATE_PREFIX: str = "clinic_before_update_v"

# 자동 백업 interval 최소 (분) 정책.
AUTO_BACKUP_INTERVAL_MIN_FLOOR: int = 5
"""``SystemSetting.auto_backup_interval_min`` 최소값 정책.

NOTE: ``app/routers/api.py:system_settings_set`` 의 ``max(5, v)`` 와 byte-equivalent.
본 19-12 가 *변경 ⊥* — 너무 짧으면 디스크 / I/O 부담.
"""

AUTO_BACKUP_KEEP_COUNT_DEFAULT: int = 30
"""``SystemSetting.auto_backup_keep_count`` 기본값 정책.

NOTE: ``app/services/backup.py:_enforce_keep_limit`` 의 ``ss.auto_backup_keep_count
or 30`` 와 byte-equivalent.
"""

AUTO_BACKUP_INTERVAL_MIN_DEFAULT: int = 60
"""``SystemSetting.auto_backup_interval_min`` 기본값 정책.

NOTE: ``app/services/backup.py:_timer_loop`` 의 ``ss.auto_backup_interval_min or 60``
와 byte-equivalent.
"""


# ──────────────── 모든 백업 응답 contract 셋 (cross-check 용) ────────────────

BACKUP_ALL_CONTRACT_SETS: dict[str, frozenset[str]] = {
    "backup_list_row": BACKUP_LIST_ROW_KEYS,
    "backup_now_ok": BACKUP_NOW_OK_RESPONSE_KEYS,
    "backup_now_error": BACKUP_NOW_ERROR_RESPONSE_KEYS,
    "backup_restore_ok": BACKUP_RESTORE_OK_RESPONSE_KEYS,
    "backup_restore_error": BACKUP_RESTORE_ERROR_RESPONSE_KEYS,
    "backup_dir": BACKUP_DIR_RESPONSE_KEYS,
    "restore_ok": RESTORE_OK_RESPONSE_KEYS,
    "apply_update_backup_ok": APPLY_UPDATE_BACKUP_OK_KEYS,
    "apply_update_backup_error": APPLY_UPDATE_BACKUP_ERROR_KEYS,
}
