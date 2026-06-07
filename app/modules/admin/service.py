"""관리자 / about / config / system-settings 응답 dict 빌더 + 정책 helper (19-12 신규).

19-11 stats.service / 19-10 sms.service 와 동일 패턴 — *byte-equivalent helper*.
라우터 본체 무수정. 라우터 채택은 19-13+ 시점에 점진적.

# COMPAT: 본 모듈의 모든 ``build_*`` / ``redact_*`` / ``mask_*`` 함수는
#         ``app/routers/api.py`` / ``app/routers/ai.py`` 의 인라인 동작과
#         *byte-equivalent*. 응답 key / 타입 / 마스킹 결과 보존.

# SAFETY: ``redact_public_config`` 는 ``admin_password_hash`` / ``sync_secret``
#         *원문 제거 정책* 의 단일 원천. ``schemas.PUBLIC_CONFIG_DROP_KEYS`` 와
#         정합. 실수 / 우회 방지 contract 는 19-12 테스트가 검증.

# SAFETY: ``mask_api_key`` 는 ``app/routers/ai.py:_mask_api_key`` 와 byte-equivalent
#         — 앞 4자 + ``****``, 4자 이하면 ``****``, 빈 값이면 ``""``. 본 19-12 가
#         이 정책 변경 ⊥.

# SAFETY: ``mask_munjanara_pw`` / ``mask_munjanara_key`` 는 ``app/routers/api.py:
#         sms_get`` 의 인라인 마스킹과 byte-equivalent — ``****`` / 앞 4자 + ``****``.

# RISK: ``audit_detail_cap`` (500자) 정책은 ``app/routers/api.py:audit`` 와
#       byte-equivalent. 본 19-12 가 길이 *변경 ⊥* — PII 원문 노출 / 로그 폭주
#       회귀 방지.

# NOTE: 본 모듈은 *읽기 / 응답 dict 조립 / 마스킹* 만 — DB 변경 ⊥.
#       SystemSetting / AiSetting / SmsSetting 갱신은 라우터 본체가 보유.
"""
from __future__ import annotations

from typing import Any, Mapping

from .schemas import PUBLIC_CONFIG_DROP_KEYS


# ──────────────── 비밀 값 제거 / 마스킹 ────────────────

def redact_public_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """공개 config 응답용 — 비밀 key 제거.

    SAFETY: ``admin_password_hash`` / ``sync_secret`` *원문 노출 금지* 정책 단일 원천.
    ``app/routers/api.py:get_config`` 의 ``cfg.pop(...)`` 와 byte-equivalent.

    응답 dict 는 *복사본* — 원본 mapping 무수정.
    """
    out: dict[str, Any] = dict(cfg)
    for key in PUBLIC_CONFIG_DROP_KEYS:
        out.pop(key, None)
    return out


def mask_api_key(key: str | None) -> str:
    """AI api_key 마스킹 — ``app/routers/ai.py:_mask_api_key`` byte-equivalent.

    - ``""`` / ``None`` → ``""``
    - 길이 ≤ 4 → ``"****"``
    - 그 외 → ``key[:4] + "****"``

    SAFETY: 본 정책은 AI 설정 응답에 사용 — *원문 노출 ⊥*.
    """
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return key[:4] + "****"


def mask_munjanara_pw(pw: str | None) -> str:
    """문자나라 비밀번호 마스킹 — ``app/routers/api.py:sms_get`` byte-equivalent.

    - 값이 있으면 ``"****"`` (등록 여부만 알림)
    - 없으면 ``""``

    SAFETY: 비밀번호 *원문 노출 ⊥*.
    """
    return "****" if pw else ""


def mask_munjanara_key(key: str | None) -> str:
    """문자나라 API key 마스킹 — ``app/routers/api.py:sms_get`` byte-equivalent.

    - 값이 있으면 ``key[:4] + "****"``
    - 없으면 ``""``

    SAFETY: API key *원문 노출 ⊥* — 앞 4자 + ``****`` 만.
    """
    return key[:4] + "****" if key else ""


# ──────────────── audit detail 길이 정책 ────────────────

AUDIT_DETAIL_CAP: int = 500
"""AuditLog detail 컬럼 길이 cap (정책 단일 원천).

RISK: ``app/routers/api.py:audit`` 의 ``detail[:500]`` 와 byte-equivalent.
PII 원문 / 페이로드 폭주 방지 정책. *변경 ⊥*.
"""


def audit_detail_cap(detail: str | None) -> str:
    """audit detail 길이 cap helper (500자) — ``app/routers/api.py:audit`` byte-equivalent.

    RISK: 본 cap 은 ``app/modules/audit/`` 와도 정합 — 단일 원천.
    """
    if detail is None:
        return ""
    return str(detail)[:AUDIT_DETAIL_CAP]


# ──────────────── 응답 dict 빌더 ────────────────

def build_admin_status_response(authenticated: bool, is_default_password: bool) -> dict[str, Any]:
    """``GET /api/admin/status`` 응답 dict — byte-equivalent."""
    return {
        "authenticated": bool(authenticated),
        "is_default_password": bool(is_default_password),
    }


def build_admin_login_response(token: str, is_default_password: bool) -> dict[str, Any]:
    """``POST /api/admin/login`` 성공 응답 dict — byte-equivalent."""
    return {
        "token": token,
        "is_default_password": bool(is_default_password),
    }


def build_admin_logout_response() -> dict[str, Any]:
    """``POST /api/admin/logout`` 응답 dict — byte-equivalent."""
    return {"ok": True}


def build_admin_change_password_response() -> dict[str, Any]:
    """``POST /api/admin/change-password`` 성공 응답 dict — byte-equivalent."""
    return {
        "ok": True,
        "msg": "비밀번호가 변경되었습니다. 다시 로그인하세요.",
    }


def build_about_response(
    *,
    app_name: str,
    version: str,
    build_date: str,
    data_dir: str,
    db_path: str,
    backup_dir: str,
    update_manifest_url: str,
    is_frozen: bool,
    update_completed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """``GET /api/about`` 응답 dict — byte-equivalent.

    NOTE: ``app/routers/api.py:about`` 은 ``app_name="도수치료예약"`` 하드코딩.
    본 helper 는 caller 가 명시적 주입.
    """
    return {
        "app_name": app_name,
        "version": version,
        "build_date": build_date,
        "data_dir": data_dir,
        "db_path": db_path,
        "backup_dir": backup_dir,
        "update_manifest_url": update_manifest_url or "",
        "is_frozen": bool(is_frozen),
        "update_completed": dict(update_completed) if update_completed else None,
    }


def build_system_settings_response(
    *,
    manual_slot_limit: int | None,
    treatment_minutes: Mapping[str, int],
    sms_template: str | None,
    auto_backup_enabled: bool,
    auto_backup_interval_min: int | None,
    auto_backup_keep_count: int | None,
) -> dict[str, Any]:
    """``GET /api/system-settings`` 응답 dict — byte-equivalent.

    NOTE: ``app/routers/api.py:system_settings_get`` 의 인라인 dict 와 byte-equivalent.
    fallback 정책: ``auto_backup_interval_min or 60`` / ``auto_backup_keep_count or 30``.
    """
    return {
        "manual_slot_limit": manual_slot_limit,
        "treatment_minutes": dict(treatment_minutes),
        "sms_template": sms_template or "",
        "auto_backup_enabled": bool(auto_backup_enabled),
        "auto_backup_interval_min": (auto_backup_interval_min or 60),
        "auto_backup_keep_count": (auto_backup_keep_count or 30),
    }


def serialize_ai_setting(
    *,
    enabled: bool,
    provider: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    max_tokens: int | None,
    temperature: float | None,
    pii_guard_enabled: bool,
) -> dict[str, Any]:
    """``GET / PUT /api/ai/settings`` 응답 dict — ``app/routers/ai.py:_serialize_setting``
    byte-equivalent.

    SAFETY: ``api_key`` 평문 부재 — ``api_key_masked`` (앞 4자 + ``****``) +
            ``api_key_set`` (등록 여부) 만 노출.
    """
    return {
        "enabled": bool(enabled),
        "provider": provider or "openai",
        "model": model or "",
        "api_key_masked": mask_api_key(api_key or ""),
        "api_key_set": bool(api_key),
        "base_url": base_url or "",
        "max_tokens": int(max_tokens or 512),
        "temperature": float(temperature or 0.3),
        "pii_guard_enabled": bool(pii_guard_enabled),
    }


# ──────────────── about 업데이트 흐름 (후속 검토) ────────────────

# RISK: ``check-update`` / ``download-update`` / ``apply-update`` 응답 dict 빌더는
#       *후속 검토* — 분기가 많고 (configured/up_to_date/available/error) PyInstaller
#       프로그램 폴더 교체 + ``updater.bat`` 실행 + ``engine.dispose()`` 부수효과
#       동반. 19-12 가 helper 추가 ⊥.
#
# TODO(후속 검토): 19-13+ 에서 ``build_about_check_update_*`` 분기 helper 분리 검토.
#                  본 19-12 는 schemas.py 의 응답 key contract 만 기록.
