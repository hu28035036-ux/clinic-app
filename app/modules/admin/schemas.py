"""관리자 / about / config / system-settings 응답 키 contract 상수 (19-12 신규).

19-11 stats.schemas / 19-10 sms.schemas 와 동일 패턴 — frozenset 상수 노출.
contract 테스트가 본 모듈의 상수와 라우터 응답 key 셋 비교 → 임의 변경 검출.

# COMPAT: 본 frozenset 상수의 *원소 변경 ⊥* (key 추가/제거/이름 변경) —
#         관리자탭 / 자동 업데이트 UI / SMS 템플릿 / AI 설정 모달이 모두 의존.
#         contract 테스트가 회귀 검출.

# SAFETY: 공개 config 응답 key 셋에는 ``admin_password_hash`` / ``sync_secret``
#         *부재 보장* — ``PUBLIC_CONFIG_DROP_KEYS`` 가 정책 단일 원천.

# SAFETY: AI / SMS 설정 응답 key 셋에는 ``api_key`` / ``munjanara_pw`` 평문
#         *부재 보장* — ``api_key_set`` / ``api_key_masked`` / ``****``
#         마스킹 키만 노출.
"""
from __future__ import annotations


# ──────────────── /api/admin/* (4 endpoints) ────────────────

# GET /api/admin/status
ADMIN_STATUS_RESPONSE_KEYS: frozenset[str] = frozenset({
    "authenticated",
    "is_default_password",
})

# POST /api/admin/login (성공 응답)
ADMIN_LOGIN_RESPONSE_KEYS: frozenset[str] = frozenset({
    "token",
    "is_default_password",
})

# POST /api/admin/logout
ADMIN_LOGOUT_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
})

# POST /api/admin/change-password
ADMIN_CHANGE_PW_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "msg",
})


# ──────────────── /api/about/* (5 endpoints) ────────────────

# GET /api/about
ABOUT_RESPONSE_KEYS: frozenset[str] = frozenset({
    "app_name",
    "version",
    "build_date",
    "data_dir",
    "db_path",
    "backup_dir",
    "update_manifest_url",
    "is_frozen",
})

# POST /api/about/check-update — 분기 별 응답 key (configured / 미설정)
ABOUT_CHECK_UPDATE_BASE_KEYS: frozenset[str] = frozenset({
    "current_version",
    "checked_at",
})

# POST /api/about/download-update (성공 응답)
ABOUT_DOWNLOAD_UPDATE_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "path",
    "size_mb",
    "sha256",
    "sha256_expected",
    "sha256_matched",
})

# POST /api/about/apply-update (성공 응답)
ABOUT_APPLY_UPDATE_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "message",
    "backup",
    "updater_log_path",
})

# GET /api/about/update-log (exists=True 응답)
ABOUT_UPDATE_LOG_KEYS: frozenset[str] = frozenset({
    "path",
    "exists",
    "lines",
    "total_lines",
    "mtime",
    "size_bytes",
})


# ──────────────── /api/config (4 endpoints) ────────────────

# GET /api/config 응답에서 *반드시 제거되어야 할* 비밀 key 셋.
# SAFETY: 정책 단일 원천 — ``app/routers/api.py:get_config`` 의 ``cfg.pop(...)`` 와
#         byte-equivalent.
PUBLIC_CONFIG_DROP_KEYS: frozenset[str] = frozenset({
    "admin_password_hash",
    "sync_secret",
})

# GET /api/config/sync-secret (관리자 전용 — secret 원문 노출. 본 응답 key 만 contract.)
CONFIG_SYNC_SECRET_RESPONSE_KEYS: frozenset[str] = frozenset({
    "sync_secret",
})

# POST /api/config/regenerate-sync-secret
CONFIG_REGEN_SYNC_SECRET_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
    "sync_secret",
})


# ──────────────── /api/system-settings ────────────────

# GET /api/system-settings (응답 key 6개 — UI / 백업 / SMS 템플릿 의존)
SYSTEM_SETTINGS_RESPONSE_KEYS: frozenset[str] = frozenset({
    "manual_slot_limit",
    "treatment_minutes",
    "sms_template",
    "auto_backup_enabled",
    "auto_backup_interval_min",
    "auto_backup_keep_count",
})

# POST /api/system-settings
SYSTEM_SETTINGS_UPDATE_RESPONSE_KEYS: frozenset[str] = frozenset({
    "ok",
})


# ──────────────── /api/ai/settings (9 keys, AI 모듈 단일 원천) ────────────────

# GET / PUT /api/ai/settings — ``app/routers/ai.py:_serialize_setting`` 와 byte-equivalent.
# SAFETY: ``api_key`` 평문 부재 + ``api_key_set`` (등록 여부) + ``api_key_masked``
#         (앞 4자 + ``****``) 만 노출. 본 contract 가 정책 가드.
AI_SETTINGS_RESPONSE_KEYS: frozenset[str] = frozenset({
    "enabled",
    "provider",
    "model",
    "api_key_masked",
    "api_key_set",
    "base_url",
    "max_tokens",
    "temperature",
    "pii_guard_enabled",
})

# AI 설정 응답에 *부재 보장* 되어야 할 평문 key 셋 (regression 가드).
AI_SETTINGS_FORBIDDEN_KEYS: frozenset[str] = frozenset({
    "api_key",
})


# ──────────────── 모든 관리자 응답 key contract 셋 (cross-check 용) ────────────────

ADMIN_ALL_CONTRACT_SETS: dict[str, frozenset[str]] = {
    "admin_status": ADMIN_STATUS_RESPONSE_KEYS,
    "admin_login": ADMIN_LOGIN_RESPONSE_KEYS,
    "admin_logout": ADMIN_LOGOUT_RESPONSE_KEYS,
    "admin_change_password": ADMIN_CHANGE_PW_RESPONSE_KEYS,
    "about": ABOUT_RESPONSE_KEYS,
    "about_check_update_base": ABOUT_CHECK_UPDATE_BASE_KEYS,
    "about_download_update": ABOUT_DOWNLOAD_UPDATE_RESPONSE_KEYS,
    "about_apply_update": ABOUT_APPLY_UPDATE_RESPONSE_KEYS,
    "about_update_log": ABOUT_UPDATE_LOG_KEYS,
    "config_sync_secret": CONFIG_SYNC_SECRET_RESPONSE_KEYS,
    "config_regen_sync_secret": CONFIG_REGEN_SYNC_SECRET_RESPONSE_KEYS,
    "system_settings": SYSTEM_SETTINGS_RESPONSE_KEYS,
    "system_settings_update": SYSTEM_SETTINGS_UPDATE_RESPONSE_KEYS,
    "ai_settings": AI_SETTINGS_RESPONSE_KEYS,
}
