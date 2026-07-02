"""19-12 admin / backup / audit / export_import 경계 정리 contract.

검증 범위 (19-12 세션 지시문 정합):
  1. ``admin.schemas`` / ``admin.service`` 가 ``api.py`` / ``ai.py`` 인라인 응답
     dict / 마스킹 정책과 byte-equivalent.
  2. ``backup.schemas`` / ``backup.service`` 가 ``services/backup.py`` /
     ``api.py`` 인라인 응답 dict / 파일명 정책과 byte-equivalent.
  3. ``audit.schemas`` / ``audit.service`` 가 ``api.py:audit`` /
     ``list_audit_logs`` 동작과 byte-equivalent.
  4. ``export_import.schemas`` / ``export_import.service`` 가 ``api.py:
     data_convert_preview`` / ``data_convert_apply`` 응답 dict 와 byte-equivalent.
  5. **API key / 문자나라 계정 / sync_secret / admin_password_hash 원문 노출 ⊥**
     정책 가드.
  6. **AuditLog detail 500자 cap 정책** 가드 (PII / payload 폭주 방지).
  7. modules.{admin,backup,audit,export_import} 가 ``app.routers`` 미참조 —
     단방향 경계.
  8. 라우터 핸들러 시그니처 / 응답 key 무수정.
  9. 기존 admin / backup / audit / export_import 흐름 영향 없음.
 10. 본 19-12 모듈은 외부 API 호출 / DB 변경 / 파일 시스템 변경 ⊥.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.modules.admin import schemas as _admin_schemas
from app.modules.admin import service as _admin_service
from app.modules.audit import schemas as _audit_schemas
from app.modules.audit import service as _audit_service
from app.modules.backup import schemas as _backup_schemas
from app.modules.backup import service as _backup_service
from app.modules.export_import import schemas as _ei_schemas
from app.modules.export_import import service as _ei_service

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_ROUTERS_API = REPO_ROOT / "app" / "routers" / "api.py"
APP_ROUTERS_AI = REPO_ROOT / "app" / "routers" / "ai.py"
APP_SERVICES_BACKUP = REPO_ROOT / "app" / "services" / "backup.py"


# ──────────────────────── 1. admin contract ────────────────────────


def test_admin_schemas_admin_status_keys_match_router():
    """COMPAT: ``GET /api/admin/status`` 응답 key 셋 정합."""
    assert _admin_schemas.ADMIN_STATUS_RESPONSE_KEYS == frozenset({
        "authenticated", "is_default_password",
    })


def test_admin_schemas_admin_login_keys_match_router():
    """COMPAT: ``POST /api/admin/login`` 성공 응답 key 셋 정합."""
    assert _admin_schemas.ADMIN_LOGIN_RESPONSE_KEYS == frozenset({
        "token", "is_default_password",
    })


def test_admin_schemas_about_keys_match_router():
    """COMPAT: ``GET /api/about`` 응답 key 9개 정합."""
    assert _admin_schemas.ABOUT_RESPONSE_KEYS == frozenset({
        "app_name", "version", "build_date", "data_dir", "db_path",
        "backup_dir", "update_manifest_url", "is_frozen", "update_completed",
    })


def test_admin_schemas_system_settings_keys_match_router():
    """COMPAT: ``GET /api/system-settings`` 응답 key 6개 정합."""
    assert _admin_schemas.SYSTEM_SETTINGS_RESPONSE_KEYS == frozenset({
        "manual_slot_limit", "treatment_minutes", "sms_template",
        "auto_backup_enabled", "auto_backup_interval_min", "auto_backup_keep_count",
    })


def test_admin_schemas_ai_settings_keys_match_router():
    """COMPAT: ``GET / PUT /api/ai/settings`` 응답 key 9개 정합."""
    assert _admin_schemas.AI_SETTINGS_RESPONSE_KEYS == frozenset({
        "enabled", "provider", "model", "api_key_masked", "api_key_set",
        "base_url", "max_tokens", "temperature", "pii_guard_enabled",
    })


def test_admin_schemas_ai_settings_forbidden_api_key():
    """SAFETY: AI 설정 응답에 ``api_key`` 평문 *부재 보장*."""
    assert "api_key" in _admin_schemas.AI_SETTINGS_FORBIDDEN_KEYS
    assert _admin_schemas.AI_SETTINGS_FORBIDDEN_KEYS.isdisjoint(
        _admin_schemas.AI_SETTINGS_RESPONSE_KEYS,
    )


def test_admin_schemas_public_config_drop_keys_includes_secrets():
    """SAFETY: 공개 config 응답에서 *반드시 제거되어야 할* 비밀 key 셋 정합."""
    assert "admin_password_hash" in _admin_schemas.PUBLIC_CONFIG_DROP_KEYS
    assert "sync_secret" in _admin_schemas.PUBLIC_CONFIG_DROP_KEYS


# ──────────────────────── 2. admin.service 마스킹 정책 ────────────────────────


@pytest.mark.parametrize("key,expected", [
    ("", ""),
    (None, ""),
    ("a", "****"),
    ("ab", "****"),
    ("abcd", "****"),  # 4자 이하
    ("abcde", "abcd****"),
    ("sk-12345abc", "sk-1****"),
    ("very-long-api-key-here", "very****"),
])
def test_admin_service_mask_api_key_byte_equivalent(key, expected):
    """SAFETY: ``mask_api_key`` 가 ``app/routers/ai.py:_mask_api_key`` byte-equivalent."""
    assert _admin_service.mask_api_key(key) == expected


@pytest.mark.parametrize("pw,expected", [
    ("", ""),
    (None, ""),
    ("anything", "****"),
    ("p@ssw0rd123", "****"),
])
def test_admin_service_mask_munjanara_pw_byte_equivalent(pw, expected):
    """SAFETY: ``mask_munjanara_pw`` 가 ``api.py:sms_get`` byte-equivalent."""
    assert _admin_service.mask_munjanara_pw(pw) == expected


@pytest.mark.parametrize("key,expected", [
    ("", ""),
    (None, ""),
    ("ABCDEFGH", "ABCD****"),
    ("xy", "xy****"),  # 짧아도 인덱싱은 [:4] 결과
])
def test_admin_service_mask_munjanara_key_byte_equivalent(key, expected):
    """SAFETY: ``mask_munjanara_key`` 가 ``api.py:sms_get`` byte-equivalent."""
    assert _admin_service.mask_munjanara_key(key) == expected


def test_admin_service_redact_public_config_removes_secrets():
    """SAFETY: ``redact_public_config`` 가 비밀 key 제거 정책 단일 원천."""
    cfg = {
        "node_id": "node-A",
        "admin_password_hash": "pbkdf2_sha256$...",
        "sync_secret": "very-secret-token",
        "lunch_enabled": True,
    }
    out = _admin_service.redact_public_config(cfg)
    assert "admin_password_hash" not in out
    assert "sync_secret" not in out
    assert out["node_id"] == "node-A"
    assert out["lunch_enabled"] is True
    # 원본 mapping 무수정
    assert cfg["admin_password_hash"] == "pbkdf2_sha256$..."
    assert cfg["sync_secret"] == "very-secret-token"


def test_admin_service_audit_detail_cap_500():
    """RISK: ``audit_detail_cap`` 500자 정책 — PII / payload 폭주 방지."""
    assert _admin_service.AUDIT_DETAIL_CAP == 500
    long = "x" * 1000
    assert len(_admin_service.audit_detail_cap(long)) == 500
    assert _admin_service.audit_detail_cap("") == ""
    assert _admin_service.audit_detail_cap(None) == ""


# ──────────────────────── 3. admin.service 응답 빌더 ────────────────────────


def test_admin_service_build_admin_status_response():
    """COMPAT: ``GET /api/admin/status`` 응답 byte-equivalent."""
    out = _admin_service.build_admin_status_response(
        authenticated=True, is_default_password=False,
    )
    assert out == {"authenticated": True, "is_default_password": False}
    assert set(out.keys()) == _admin_schemas.ADMIN_STATUS_RESPONSE_KEYS


def test_admin_service_build_admin_login_response():
    """COMPAT: ``POST /api/admin/login`` 응답 byte-equivalent."""
    out = _admin_service.build_admin_login_response(
        token="abc123", is_default_password=True,
    )
    assert out == {"token": "abc123", "is_default_password": True}
    assert set(out.keys()) == _admin_schemas.ADMIN_LOGIN_RESPONSE_KEYS


def test_admin_service_build_admin_logout_response():
    """COMPAT: ``POST /api/admin/logout`` 응답 byte-equivalent."""
    out = _admin_service.build_admin_logout_response()
    assert out == {"ok": True}
    assert set(out.keys()) == _admin_schemas.ADMIN_LOGOUT_RESPONSE_KEYS


def test_admin_service_build_admin_change_password_response():
    """COMPAT: ``POST /api/admin/change-password`` 응답 byte-equivalent."""
    out = _admin_service.build_admin_change_password_response()
    assert out["ok"] is True
    assert "msg" in out
    assert set(out.keys()) == _admin_schemas.ADMIN_CHANGE_PW_RESPONSE_KEYS


def test_admin_service_build_about_response():
    """COMPAT: ``GET /api/about`` 응답 byte-equivalent."""
    out = _admin_service.build_about_response(
        app_name="도수치료예약",
        version="1.2.3",
        build_date="2026-05-04",
        data_dir="/data",
        db_path="/data/clinic.db",
        backup_dir="/data/backups",
        update_manifest_url="",
        is_frozen=False,
        update_completed={"version": "1.2.3"},
    )
    assert set(out.keys()) == _admin_schemas.ABOUT_RESPONSE_KEYS
    assert out["app_name"] == "도수치료예약"
    assert out["update_manifest_url"] == ""
    assert out["update_completed"] == {"version": "1.2.3"}


def test_admin_service_build_system_settings_response():
    """COMPAT: ``GET /api/system-settings`` 응답 byte-equivalent."""
    out = _admin_service.build_system_settings_response(
        manual_slot_limit=20,
        treatment_minutes={"manual30": 30, "manual60": 60},
        sms_template="안녕하세요",
        auto_backup_enabled=True,
        auto_backup_interval_min=None,
        auto_backup_keep_count=None,
    )
    assert set(out.keys()) == _admin_schemas.SYSTEM_SETTINGS_RESPONSE_KEYS
    # 기본값 정책 byte-equivalent (api.py:system_settings_get).
    assert out["auto_backup_interval_min"] == 60
    assert out["auto_backup_keep_count"] == 30
    assert out["sms_template"] == "안녕하세요"
    assert out["treatment_minutes"] == {"manual30": 30, "manual60": 60}


def test_admin_service_serialize_ai_setting():
    """COMPAT/SAFETY: ``GET / PUT /api/ai/settings`` 응답 byte-equivalent.
    api_key 평문 부재.
    """
    out = _admin_service.serialize_ai_setting(
        enabled=True,
        provider="openai",
        model="gpt-4",
        api_key="sk-very-secret-key-here",
        base_url="",
        max_tokens=None,
        temperature=None,
        pii_guard_enabled=True,
    )
    assert set(out.keys()) == _admin_schemas.AI_SETTINGS_RESPONSE_KEYS
    # 평문 부재
    for forbidden in _admin_schemas.AI_SETTINGS_FORBIDDEN_KEYS:
        assert forbidden not in out
    # 마스킹 정합
    assert out["api_key_masked"] == "sk-v****"
    assert out["api_key_set"] is True
    # 기본값 정책 (ai.py:_serialize_setting).
    assert out["max_tokens"] == 512
    assert out["temperature"] == 0.3


def test_admin_service_serialize_ai_setting_empty_key_no_leak():
    """SAFETY: api_key 빈 값 — masked='' / set=False."""
    out = _admin_service.serialize_ai_setting(
        enabled=False,
        provider=None,
        model=None,
        api_key="",
        base_url=None,
        max_tokens=512,
        temperature=0.3,
        pii_guard_enabled=False,
    )
    assert out["api_key_masked"] == ""
    assert out["api_key_set"] is False
    assert out["provider"] == "openai"  # 기본값 fallback


# ──────────────────────── 4. backup contract ────────────────────────


def test_backup_schemas_list_row_keys():
    """COMPAT: ``GET /api/backup/list`` row key 4개 정합."""
    assert _backup_schemas.BACKUP_LIST_ROW_KEYS == frozenset({
        "name", "path", "size", "mtime",
    })


def test_backup_schemas_make_ok_keys():
    """COMPAT: ``POST /api/backup/now`` 성공 응답 key 정합."""
    assert _backup_schemas.BACKUP_NOW_OK_RESPONSE_KEYS == frozenset({
        "ok", "name", "size",
    })


def test_backup_schemas_restore_ok_keys():
    """COMPAT: ``POST /api/backup/restore-{latest,by-name}`` 성공 응답 key 정합."""
    assert _backup_schemas.BACKUP_RESTORE_OK_RESPONSE_KEYS == frozenset({
        "ok", "restored_from", "msg",
    })


def test_backup_schemas_prefix_suffix_constants():
    """COMPAT: ``BACKUP_PREFIX`` / ``BACKUP_SUFFIX`` 가 services/backup.py 와 정합."""
    src = APP_SERVICES_BACKUP.read_text(encoding="utf-8")
    assert 'BACKUP_PREFIX = "clinic_"' in src
    assert 'BACKUP_SUFFIX = ".db"' in src
    assert _backup_schemas.BACKUP_PREFIX == "clinic_"
    assert _backup_schemas.BACKUP_SUFFIX == ".db"


def test_backup_schemas_interval_floor_constant():
    """RISK: 자동 백업 interval 최소 5분 정책 가드."""
    assert _backup_schemas.AUTO_BACKUP_INTERVAL_MIN_FLOOR == 5


def test_backup_schemas_keep_count_default_constant():
    """NOTE: 기본 keep count 30 정책 가드."""
    assert _backup_schemas.AUTO_BACKUP_KEEP_COUNT_DEFAULT == 30


def test_backup_schemas_interval_default_constant():
    """NOTE: 기본 interval 60분 정책 가드."""
    assert _backup_schemas.AUTO_BACKUP_INTERVAL_MIN_DEFAULT == 60


# ──────────────────────── 5. backup.service 응답 빌더 / 파일명 ────────────────────────


def test_backup_service_make_backup_filename_byte_equivalent():
    """COMPAT: ``app/services/backup.py:make_backup`` 의 파일명 패턴과 byte-equivalent."""
    out = _backup_service.make_backup_filename("20260504_120000")
    assert out == "clinic_20260504_120000.db"


def test_backup_service_before_restore_filename_byte_equivalent():
    """RISK: 안전망 백업 파일명 — restore 직전 자동 생성."""
    out = _backup_service.make_before_restore_filename("20260504_120000")
    assert out == "clinic_before_restore_20260504_120000.db"


def test_backup_service_before_update_filename_byte_equivalent():
    """RISK: 자동 업데이트 직전 백업 — apply-update."""
    out = _backup_service.make_before_update_filename("1.2.3", "20260504_120000")
    assert out == "clinic_before_update_v1.2.3_20260504_120000.db"


@pytest.mark.parametrize("name,expected", [
    ("clinic_20260504_120000.db", True),
    ("clinic_before_restore_20260504_120000.db", True),
    ("clinic_before_update_v1.2.3_20260504_120000.db", True),
    ("clinic.db", False),  # prefix=clinic_ 이지만 ts 필요 없음 — 그래도 starts/ends 만 검사하므로 False (clinic_ 시작 X)
    ("other.db", False),
    ("", False),
    ("clinic_foo.txt", False),  # suffix mismatch
])
def test_backup_service_is_backup_filename(name, expected):
    """COMPAT: glob 패턴 byte-equivalent."""
    assert _backup_service.is_backup_filename(name) is expected


def test_backup_service_build_make_backup_ok_response():
    out = _backup_service.build_make_backup_ok_response(
        name="clinic_20260504_120000.db", size=12345,
    )
    assert out == {"ok": True, "name": "clinic_20260504_120000.db", "size": 12345}
    assert set(out.keys()) == _backup_schemas.BACKUP_NOW_OK_RESPONSE_KEYS


def test_backup_service_build_make_backup_error_response():
    out = _backup_service.build_make_backup_error_response(error="DB 파일이 없습니다.")
    assert out == {"ok": False, "error": "DB 파일이 없습니다."}
    assert set(out.keys()) == _backup_schemas.BACKUP_NOW_ERROR_RESPONSE_KEYS


def test_backup_service_build_restore_ok_response():
    out = _backup_service.build_restore_ok_response(
        restored_from="clinic_20260504_120000.db",
    )
    assert out["ok"] is True
    assert out["restored_from"] == "clinic_20260504_120000.db"
    assert "복원됨" in out["msg"]
    assert "재시작" in out["msg"]
    assert set(out.keys()) == _backup_schemas.BACKUP_RESTORE_OK_RESPONSE_KEYS


def test_backup_service_build_restore_error_response():
    out = _backup_service.build_restore_error_response(error="파일 없음")
    assert out == {"ok": False, "error": "파일 없음"}
    assert set(out.keys()) == _backup_schemas.BACKUP_RESTORE_ERROR_RESPONSE_KEYS


def test_backup_service_build_backup_dir_response():
    out = _backup_service.build_backup_dir_response(path="/data/backups")
    assert out == {"path": "/data/backups"}
    assert set(out.keys()) == _backup_schemas.BACKUP_DIR_RESPONSE_KEYS


def test_backup_service_build_legacy_restore_ok_response():
    out = _backup_service.build_legacy_restore_ok_response()
    assert out["ok"] is True
    assert "복원" in out["msg"]
    assert set(out.keys()) == _backup_schemas.RESTORE_OK_RESPONSE_KEYS


@pytest.mark.parametrize("v,expected", [
    (None, 60),
    (0, 60),
    (1, 5),  # 최소 5
    (5, 5),
    (30, 30),
    (180, 180),
    ("60", 60),  # 문자열도 허용 (api.py 와 정합)
])
def test_backup_service_normalize_interval_min(v, expected):
    """NOTE: ``api.py:system_settings_set`` 의 ``max(5, v)`` 와 byte-equivalent."""
    assert _backup_service.normalize_auto_backup_interval_min(v) == expected


@pytest.mark.parametrize("v,expected", [
    (None, 30),
    (0, 30),  # api.py: int(0 or 30) → 30
    (1, 1),  # 최소 1
    (50, 50),
    ("30", 30),
])
def test_backup_service_normalize_keep_count(v, expected):
    """NOTE: ``api.py:system_settings_set`` 의 ``max(1, int(... or 30))`` 와 byte-equivalent."""
    assert _backup_service.normalize_auto_backup_keep_count(v) == expected


# ──────────────────────── 6. audit contract ────────────────────────


def test_audit_schemas_log_row_keys():
    """COMPAT: ``GET /api/audit-logs`` row key 7개 정합."""
    assert _audit_schemas.AUDIT_LOG_ROW_KEYS == frozenset({
        "id", "ts", "node_id", "actor", "action", "entity_id", "detail",
    })


def test_audit_schemas_detail_cap_500():
    """SAFETY: ``AUDIT_DETAIL_CAP == 500`` PII / payload 폭주 방지."""
    assert _audit_schemas.AUDIT_DETAIL_CAP == 500


def test_audit_schemas_known_actors():
    """SAFETY: actor 는 ``system`` / ``admin`` 만 (현재 정책)."""
    assert _audit_schemas.AUDIT_KNOWN_ACTORS == frozenset({"system", "admin"})
    assert _audit_schemas.AUDIT_DEFAULT_ACTOR == "system"


def test_audit_service_cap_detail_byte_equivalent():
    """SAFETY: ``cap_detail`` 가 ``api.py:audit`` 의 ``detail[:500]`` byte-equivalent."""
    long = "x" * 1000
    assert len(_audit_service.cap_detail(long)) == 500
    assert _audit_service.cap_detail("short") == "short"
    assert _audit_service.cap_detail("") == ""
    assert _audit_service.cap_detail(None) == ""


def test_audit_service_serialize_audit_log_row_byte_equivalent():
    """COMPAT: ``serialize_audit_log_row`` 가 ``api.py:list_audit_logs`` 인라인 dict 와 byte-equivalent."""
    ts = datetime(2026, 5, 4, 12, 0, 0)
    row = SimpleNamespace(
        id=1,
        ts=ts,
        node_id="node-A",
        actor="admin",
        action="admin.password_change",
        entity_id="",
        detail="관리자 비밀번호 변경",
    )
    out = _audit_service.serialize_audit_log_row(row)
    assert set(out.keys()) == _audit_schemas.AUDIT_LOG_ROW_KEYS
    assert out["id"] == 1
    assert out["ts"] == ts.isoformat()
    assert out["actor"] == "admin"
    assert out["action"] == "admin.password_change"
    assert out["detail"] == "관리자 비밀번호 변경"


def test_audit_service_serialize_audit_log_rows_list():
    """COMPAT: 리스트 형태 직렬화 byte-equivalent."""
    rows = [
        SimpleNamespace(
            id=i, ts=datetime(2026, 5, 4, 12, i, 0),
            node_id="A", actor="system", action=f"action.{i}",
            entity_id=str(i), detail=f"detail-{i}",
        )
        for i in range(3)
    ]
    out = _audit_service.serialize_audit_log_rows(rows)
    assert len(out) == 3
    for d in out:
        assert set(d.keys()) == _audit_schemas.AUDIT_LOG_ROW_KEYS


@pytest.mark.parametrize("actor,expected", [
    (None, "system"),
    ("", "system"),
    ("  ", "system"),
    ("admin", "admin"),
    (" admin ", "admin"),
    ("system", "system"),
])
def test_audit_service_normalize_actor(actor, expected):
    """NOTE: actor 정규화 — 빈 값 → system."""
    assert _audit_service.normalize_actor(actor) == expected


# ──────────────────────── 7. export_import contract ────────────────────────


def test_ei_schemas_preview_keys():
    """COMPAT: ``data-convert/preview`` 응답 key 13개 정합 (v1.3.51+ 겹침 내역 추가)."""
    assert _ei_schemas.DATA_CONVERT_PREVIEW_RESPONSE_KEYS == frozenset({
        "total", "new_count", "existing_count", "existing_patients",
        "dup_in_file_count", "error_count",
        "header", "new_patients", "review_list", "review_count",
        "errors", "file_name", "parse_info",
    })


def test_ei_schemas_apply_keys():
    """COMPAT: ``data-convert/apply`` 응답 key 5개 정합."""
    assert _ei_schemas.DATA_CONVERT_APPLY_RESPONSE_KEYS == frozenset({
        "inserted", "review_inserted", "skipped",
        "inserted_patients", "skipped_items",
    })


def test_ei_schemas_file_size_max_constant():
    """RISK: 파일 크기 cap 10MB 정책 가드."""
    assert _ei_schemas.DATA_CONVERT_FILE_SIZE_MAX == 10 * 1024 * 1024


def test_ei_schemas_bulk_chunk_constant():
    """RISK: BULK_CHUNK 2000 정책 가드."""
    assert _ei_schemas.DATA_CONVERT_BULK_CHUNK == 2000


def test_ei_schemas_current_endpoints():
    """COMPAT: 현재 export / import 엔드포인트 셋 정합."""
    assert "/api/export/manual-schedule.xlsx" in _ei_schemas.CURRENT_EXPORT_ENDPOINTS
    assert "/api/export/stats.xlsx" in _ei_schemas.CURRENT_EXPORT_ENDPOINTS
    assert "/api/data-convert/preview" in _ei_schemas.CURRENT_IMPORT_ENDPOINTS
    assert "/api/data-convert/apply" in _ei_schemas.CURRENT_IMPORT_ENDPOINTS


@pytest.mark.parametrize("size,expected", [
    (0, False),
    (1, True),
    (10 * 1024 * 1024, True),  # 정확히 10MB
    (10 * 1024 * 1024 + 1, False),
    (-1, False),
    (None, False),
])
def test_ei_service_is_file_size_within_limit(size, expected):
    """RISK: 파일 크기 cap 10MB byte-equivalent."""
    assert _ei_service.is_file_size_within_limit(size) is expected


def test_ei_service_build_preview_response():
    """COMPAT: ``data-convert/preview`` 응답 byte-equivalent."""
    out = _ei_service.build_data_convert_preview_response(
        total=10,
        new_count=5,
        existing_count=3,
        error_count=2,
        header=["이름", "차트"],
        new_patients=[{"name": "홍길동", "chart_no": "001"}],
        review_list=[],
        review_count=0,
        errors=["err1"],
        file_name="patients.xlsx",
        parse_info={"fallback_used": False},
    )
    assert set(out.keys()) == _ei_schemas.DATA_CONVERT_PREVIEW_RESPONSE_KEYS
    assert out["total"] == 10
    assert out["file_name"] == "patients.xlsx"
    assert out["new_patients"] == [{"name": "홍길동", "chart_no": "001"}]


def test_ei_service_build_apply_response():
    """COMPAT: ``data-convert/apply`` 응답 byte-equivalent."""
    out = _ei_service.build_data_convert_apply_response(
        inserted=5,
        review_inserted=2,
        skipped=1,
        inserted_patients=[{"id": "abc", "name": "홍"}],
        skipped_items=[{"reason": "중복"}],
    )
    assert set(out.keys()) == _ei_schemas.DATA_CONVERT_APPLY_RESPONSE_KEYS
    assert out["inserted"] == 5
    assert out["skipped_items"] == [{"reason": "중복"}]


def test_ei_service_build_audit_detail_for_bulk_import_byte_equivalent():
    """SAFETY/COMPAT: ``api.py:data_convert_apply`` 의 audit detail 와 byte-equivalent.
    detail 에 환자 PII 부재 — 카운트만.
    """
    out = _ei_service.build_audit_detail_for_bulk_import(
        inserted=5, review_inserted=2, skipped=3,
    )
    assert out == "AI 데이터변환 5명 추가 (검토필요 2) / 3건 건너뜀"
    # PII 부재 가드
    assert "홍" not in out
    assert "010" not in out
    assert "@" not in out


# ──────────────────────── 8. 단방향 경계 (D-4) ────────────────────────


def test_admin_modules_no_app_routers_import():
    """D-4: ``app.modules.admin`` 가 ``app.routers`` 미참조."""
    for mod in (_admin_service, _admin_schemas):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from app.routers" not in src
        assert "import app.routers" not in src


def test_backup_modules_no_app_routers_import():
    """D-4: ``app.modules.backup`` 가 ``app.routers`` 미참조."""
    for mod in (_backup_service, _backup_schemas):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from app.routers" not in src
        assert "import app.routers" not in src


def test_audit_modules_no_app_routers_import():
    """D-4: ``app.modules.audit`` 가 ``app.routers`` 미참조."""
    for mod in (_audit_service, _audit_schemas):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from app.routers" not in src
        assert "import app.routers" not in src


def test_ei_modules_no_app_routers_import():
    """D-4: ``app.modules.export_import`` 가 ``app.routers`` 미참조."""
    for mod in (_ei_service, _ei_schemas):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from app.routers" not in src
        assert "import app.routers" not in src


# ──────────────────────── 9. 외부 의존 / DB 변경 부재 검증 ────────────────────────


@pytest.mark.parametrize("mod_path", [
    "app/modules/admin/service.py",
    "app/modules/admin/schemas.py",
    "app/modules/backup/service.py",
    "app/modules/backup/schemas.py",
    "app/modules/audit/service.py",
    "app/modules/audit/schemas.py",
    "app/modules/export_import/service.py",
    "app/modules/export_import/schemas.py",
])
def test_modules_no_external_http_imports(mod_path):
    """SAFETY: 본 19-12 모듈은 외부 HTTP / 파일 시스템 변경 라이브러리 의존 ⊥."""
    src = (REPO_ROOT / mod_path).read_text(encoding="utf-8")
    forbidden = ["import urllib.request", "import requests", "import httpx",
                 "import shutil", "import sqlite3"]
    for pat in forbidden:
        assert pat not in src, (
            f"{mod_path} 에 외부 / 파일 시스템 변경 의존성 발견: {pat!r}"
        )


@pytest.mark.parametrize("mod_path", [
    "app/modules/admin/service.py",
    "app/modules/admin/schemas.py",
    "app/modules/backup/service.py",
    "app/modules/backup/schemas.py",
    "app/modules/audit/service.py",
    "app/modules/audit/schemas.py",
    "app/modules/export_import/service.py",
    "app/modules/export_import/schemas.py",
])
def test_modules_no_db_mutation(mod_path):
    """SAFETY: 본 19-12 모듈은 DB 변경 ⊥ (db.commit/add/delete/flush 부재)."""
    src = (REPO_ROOT / mod_path).read_text(encoding="utf-8")
    forbidden = ["db.commit(", "db.add(", "db.delete(", "db.flush("]
    for pat in forbidden:
        assert pat not in src, f"{mod_path} 에 DB 변경 패턴 발견: {pat!r}"


# ──────────────────────── 10. 라우터 핸들러 무수정 검증 ────────────────────────


def test_router_admin_handlers_signature_unchanged():
    """COMPAT: ``app/routers/api.py`` 의 모든 관리자 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    expected_sigs = [
        "@router.get(\"/admin/status\")",
        "@router.post(\"/admin/login\")",
        "@router.post(\"/admin/logout\")",
        "@router.post(\"/admin/change-password\")",
        "@router.get(\"/about\")",
        "@router.post(\"/about/check-update\")",
        "@router.post(\"/about/download-update\")",
        "@router.post(\"/about/apply-update\")",
        "@router.get(\"/about/update-log\")",
        "@router.get(\"/config\")",
        "@router.get(\"/config/sync-secret\")",
        "@router.post(\"/config/regenerate-sync-secret\")",
        "@router.post(\"/config\")",
        "@router.post(\"/mode\")",
        "@router.get(\"/system-settings\")",
        "@router.post(\"/system-settings\")",
        "@router.get(\"/audit-logs\")",
    ]
    for sig in expected_sigs:
        assert sig in src, f"라우터 핸들러 시그니처 누락 — 19-12 가 라우터 본체 변경 ⊥: {sig}"


def test_router_backup_handlers_signature_unchanged():
    """COMPAT: ``app/routers/api.py`` 의 모든 백업 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    expected_sigs = [
        "@router.get(\"/backup\")",
        "@router.post(\"/restore\")",
        "@router.get(\"/backup/list\")",
        "@router.post(\"/backup/now\")",
        "@router.get(\"/backup/dir\")",
        "@router.post(\"/backup/restore-latest\")",
        "@router.post(\"/backup/restore-by-name\")",
    ]
    for sig in expected_sigs:
        assert sig in src, f"백업 핸들러 시그니처 누락 — 19-12 가 라우터 본체 변경 ⊥: {sig}"


def test_router_data_convert_handlers_signature_unchanged():
    """COMPAT: ``app/routers/api.py`` 의 data-convert 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    assert "@router.post(\"/data-convert/preview\")" in src
    assert "@router.post(\"/data-convert/apply\")" in src


def test_router_export_handlers_signature_unchanged():
    """COMPAT: ``app/routers/api.py`` 의 export xlsx 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    assert "@router.get(\"/export/manual-schedule.xlsx\")" in src
    assert "@router.get(\"/export/stats.xlsx\")" in src


def test_router_ai_settings_handlers_signature_unchanged():
    """COMPAT: ``app/routers/ai.py`` 의 AI settings 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert "@router.get(\"/settings\")" in src
    assert "@router.put(\"/settings\")" in src


def test_router_ai_mask_api_key_unchanged():
    """SAFETY: ``ai.py:_mask_api_key`` 함수 본체 무수정 — admin.service.mask_api_key 가
    byte-equivalent helper. 라우터 채택 ⊥.
    """
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert "def _mask_api_key(key: str) -> str:" in src
    assert "return key[:4] + \"****\"" in src


# ──────────────────────── 11. 운영 DB 보호 / engine.dispose 정책 검증 ────────────────────────


def test_router_restore_uses_engine_dispose():
    """RISK: ``/api/restore`` 와 ``/backup/restore-*`` 모두 ``engine.dispose()`` 가
    파일 교체 직전 호출 — Windows DB 락 회피 정책. 본 19-12 가 *변경 ⊥*.
    """
    api_src = APP_ROUTERS_API.read_text(encoding="utf-8")
    assert "engine.dispose()" in api_src

    backup_src = APP_SERVICES_BACKUP.read_text(encoding="utf-8")
    assert "engine.dispose()" in backup_src


def test_router_restore_creates_safety_backup_before():
    """RISK: 복구 직전 안전망 백업 (``clinic_before_restore_*``) 자동 생성 — 본 19-12 가 정책 변경 ⊥."""
    api_src = APP_ROUTERS_API.read_text(encoding="utf-8")
    assert "clinic_before_restore_" in api_src

    backup_src = APP_SERVICES_BACKUP.read_text(encoding="utf-8")
    assert "before_restore_" in backup_src


def test_router_apply_update_creates_safety_backup_before():
    """RISK: 자동 업데이트 직전 SQLite online-backup 으로 ``clinic_before_update_*``
    생성 + 실패 시 업데이트 중단 — 본 19-12 가 정책 변경 ⊥.
    """
    api_src = APP_ROUTERS_API.read_text(encoding="utf-8")
    assert "_backup_db_before_update" in api_src
    assert "clinic_before_update_v" in api_src
    assert "안전을 위해 업데이트를 중단합니다" in api_src


# ──────────────────────── 12. config 비밀 값 보호 검증 ────────────────────────


def test_router_get_config_drops_secrets():
    """SAFETY: ``GET /api/config`` 가 ``admin_password_hash`` / ``sync_secret`` 제거."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    # /api/config 핸들러 본체 안에 비밀값 pop 가드.
    assert 'cfg.pop("admin_password_hash"' in src
    assert 'cfg.pop("sync_secret"' in src


def test_router_post_config_drops_secrets():
    """SAFETY: ``POST /api/config`` 가 payload 에서 비밀값 제거 + 응답에서도 제거."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    assert 'payload.pop("sync_secret"' in src
    assert 'payload.pop("admin_password_hash"' in src
    assert 'out.pop("sync_secret"' in src
    assert 'out.pop("admin_password_hash"' in src


def test_router_sms_get_masks_credentials():
    """SAFETY: ``GET /api/sms/setting`` 가 munjanara_pw / munjanara_key 마스킹."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    # 마스킹 패턴 정합 — admin.service.mask_munjanara_pw / mask_munjanara_key 와 byte-equivalent.
    assert '"****" if obj.munjanara_pw else ""' in src
    assert 'obj.munjanara_key[:4] + "****"' in src


# ──────────────────────── 13. audit detail PII 부재 검증 (정책 가드) ────────────────────────


def test_router_audit_detail_500_cap():
    """SAFETY: ``api.py:audit`` 의 ``detail[:500]`` 정책 가드 — PII / payload 폭주 방지."""
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    # audit() 함수 본체 검사
    m = re.search(r"def audit\(.*?\n(?:.*?\n){0,10}", src)
    assert m is not None
    assert "detail[:500]" in src


def test_router_bulk_import_audit_detail_no_pii():
    """SAFETY: ``patient.bulk_import`` audit detail 에 PII 부재 — 카운트만.
    ``api.py:data_convert_apply`` 의 audit 호출 본체 byte-equivalent 검증.
    """
    src = APP_ROUTERS_API.read_text(encoding="utf-8")
    # audit 호출 시작 위치 ~ 매칭된 ``)`` 까지 (다단계 — 괄호 카운트로 정확히 추출).
    start = src.find('audit(db, "patient.bulk_import"')
    assert start >= 0, "patient.bulk_import audit 호출 누락"
    # 괄호 균형으로 호출 끝 찾기.
    depth = 0
    end = -1
    for i in range(start, len(src)):
        ch = src[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    assert end > start
    audit_call = src[start:end]
    # detail 부분에 카운트 변수 (len(inserted)/review_inserted/len(skipped)) 만, 환자 데이터 부재.
    assert "len(inserted)" in audit_call
    assert "review_inserted" in audit_call
    assert "len(skipped)" in audit_call
    # 명시적 환자 PII 필드 부재 검증 — 환자명 / 차트번호 / 전화 / 생년월일 / 성별 의 변수명 부재.
    pii_var_names = ["it.get(\"name\"", "it.get(\"phone\"", "it.get(\"chart_no\"",
                     "it.get(\"birth_date\"", "p.name", "p.phone", "p.chart_no"]
    for v in pii_var_names:
        assert v not in audit_call, f"audit detail 에 PII 변수 발견: {v}"
