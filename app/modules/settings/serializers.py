"""modules.settings.serializers — 설정 직렬화 helper (19-2 신규).

본 모듈은 ``AiSetting`` / ``SmsSetting`` / ``SystemSetting`` 직렬화 정책의
*단일 진실원천 후보* 다. 19-2 시점에는 *기존 라우터가 본 모듈을 import 하지
않는다* — 19-12 / 19-13 분리 세션이 점진적으로 채택.

19-2 본 세션 범위:
  - 직렬화 helper 만 정의 — *기존 응답 dict 와 byte-equivalent* 를 보장.
  - DB / ORM import ⊥ — 본 모듈은 ``AiSetting.api_key`` 같은 attribute 를
    *primitives 로 받거나*, ORM 인스턴스를 받더라도 *내부 attribute 만 read*.
  - 신규 저장소 / 신규 router 추가 ⊥.

# COMPAT: 본 helper 는 ``app/routers/ai.py:_serialize_setting`` (라인 79~90) 의
#         결과와 *키 / 값 / 타입* 100% 일치. ``app/routers/api.py:sms_get`` (라인
#         2927~2939) 의 결과와도 일치. 응답 dict 추가 키 ⊥ (DEC-C 정합).

# SAFETY: ``api_key`` / ``munjanara_pw`` / ``munjanara_key`` *원문* 은 어떤 반환
#         값에도 포함 ⊥. 마스킹 (``mask_api_key`` / ``mask_password``) 또는
#         ``api_key_set`` / ``has_password`` boolean 만 노출.
"""
from __future__ import annotations

from typing import Any


# ─── API key / 비밀번호 마스킹 helper (단일 진실원천 후보) ────────────────────


def mask_api_key(key: str | None) -> str:
    """API key 평문 노출 금지 — 앞 4자 + ``****``.

    SAFETY: ``app/routers/ai.py:_mask_api_key`` 와 byte-equivalent. 4자 미만이면
    ``****`` 만 반환 (앞 글자도 노출 ⊥).
    """
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return key[:4] + "****"


def mask_password(value: str | None) -> str:
    """비밀번호 마스킹 — 값이 있으면 ``****``, 없으면 빈 문자열.

    SAFETY: ``app/routers/api.py:sms_get`` 의 ``munjanara_pw`` 마스킹 패턴과 동일
    (``"****" if obj.munjanara_pw else ""``). 원문 길이도 노출 ⊥.
    """
    return "****" if value else ""


# ─── AiSetting 직렬화 (api.py:_serialize_setting 와 동등) ─────────────────────


def serialize_ai_setting(obj: Any) -> dict:
    """``AiSetting`` ORM 인스턴스 → 9키 응답 dict.

    COMPAT: ``app/routers/ai.py:_serialize_setting`` (라인 79~90) 와 *키 / 값 /
    타입* 100% 일치. 9키: ``enabled / provider / model / api_key_masked /
    api_key_set / base_url / max_tokens / temperature / pii_guard_enabled``.

    SAFETY: ``api_key`` 원문 미노출 — ``api_key_masked`` (앞 4자 + ****) +
    ``api_key_set`` boolean.
    """
    return {
        "enabled": bool(obj.enabled),
        "provider": obj.provider or "openai",
        "model": obj.model or "",
        "api_key_masked": mask_api_key(obj.api_key or ""),
        "api_key_set": bool(obj.api_key),
        "base_url": obj.base_url or "",
        "max_tokens": int(obj.max_tokens or 512),
        "temperature": float(obj.temperature or 0.3),
        "pii_guard_enabled": bool(obj.pii_guard_enabled),
    }


# ─── AiSetting → admin /api/ai/health 9키 (ai.py:138~166 와 동등) ─────────────


def serialize_ai_health_admin(
    obj: Any,
    *,
    sdk_installed: dict[str, bool],
    sdk_errors: dict[str, str],
    knowledge_doc_count: int,
    ready: bool,
    version: str,
) -> dict:
    """admin ``/api/ai/health`` 응답 9키 조립 — ai.py 라우터의 dict 빌더와 동등.

    COMPAT: 9키 — ``enabled / provider / model / api_key_set / sdk_installed /
    sdk_errors / knowledge_doc_count / ready / version``. ``model`` 평문 노출은
    기존 동작 — admin 전용이므로 정합 (public 4키 와 별도 분리 — `serialize_ai_health_public`).

    SAFETY: ``api_key`` 원문 ⊥. ``sdk_errors`` 는 caller 가 미리 sdk import 실패
    사유를 200자 cap 후 전달.
    """
    return {
        "enabled": bool(obj.enabled),
        "provider": obj.provider or "openai",
        "model": obj.model or "",
        "api_key_set": bool(obj.api_key),
        "sdk_installed": dict(sdk_installed or {}),
        "sdk_errors": dict(sdk_errors or {}),
        "knowledge_doc_count": int(knowledge_doc_count or 0),
        "ready": bool(ready),
        "version": str(version),
    }


# ─── AiSetting → public /api/ai/health/public 4키 (ai.py:167~184) ─────────────


def serialize_ai_health_public(obj: Any, *, ready: bool) -> dict:
    """public ``/api/ai/health/public`` 응답 4키 — 인증 불필요.

    COMPAT: 정확히 4키 — ``enabled / ready / provider / api_key_set``. 의도적으로
    admin 전용 정보 (``model`` / ``sdk_installed`` / ``sdk_errors`` /
    ``knowledge_doc_count`` / ``version``) 미포함.

    SAFETY: ``api_key`` 원문 ⊥ (boolean 만). ``model`` 노출 ⊥ (admin 전용).
    """
    return {
        "enabled": bool(obj.enabled),
        "ready": bool(ready),
        "provider": obj.provider or "openai",
        "api_key_set": bool(obj.api_key),
    }


# ─── SmsSetting 직렬화 (api.py:sms_get 와 동등) ───────────────────────────────


def serialize_sms_setting(obj: Any) -> dict:
    """``SmsSetting`` ORM 인스턴스 → 7키 응답 dict.

    COMPAT: ``app/routers/api.py:sms_get`` (라인 2927~2939) 와 동등. 7키:
    ``munjanara_id / munjanara_pw / munjanara_key / sender_phone / clinic_phone /
    clinic_name / api_url``.

    SAFETY: ``munjanara_pw`` 는 ``****`` (있으면) / 빈 문자열 (없으면) 만 노출.
    ``munjanara_key`` 는 앞 4자 + ``****`` (있으면) / 빈 문자열 (없으면) 만 노출.
    원문 ⊥.
    """
    munjanara_key_raw = getattr(obj, "munjanara_key", "") or ""
    return {
        "munjanara_id": getattr(obj, "munjanara_id", "") or "",
        "munjanara_pw": mask_password(getattr(obj, "munjanara_pw", "")),
        "munjanara_key": (
            munjanara_key_raw[:4] + "****" if munjanara_key_raw else ""
        ),
        "sender_phone": getattr(obj, "sender_phone", "") or "",
        "clinic_phone": getattr(obj, "clinic_phone", "") or "",
        "clinic_name": getattr(obj, "clinic_name", "") or "",
        "api_url": getattr(obj, "api_url", "") or "",
    }


# ─── SystemSetting 직렬화 (api.py:system_settings_get 와 동등) ────────────────


def serialize_system_setting(
    obj: Any,
    *,
    treatment_minutes: dict[str, int] | None = None,
) -> dict:
    """``SystemSetting`` ORM 인스턴스 → 6키 응답 dict.

    COMPAT: ``app/routers/api.py:system_settings_get`` (라인 2058~2071) 와 동등.
    6키: ``manual_slot_limit / treatment_minutes / sms_template /
    auto_backup_enabled / auto_backup_interval_min / auto_backup_keep_count``.

    NOTE: ``treatment_minutes`` 는 caller 가 ``Treatment.default_minutes`` 를 미리
    조회해 dict 로 전달. 본 helper 는 *DB 조회 ⊥* — 순수 직렬화만.
    ``manual_slot_limit`` (도수 시간당 동시 허용 수) / ``auto_backup_*`` (자동
    백업 정책) 정책 정합 보존.
    """
    return {
        "manual_slot_limit": obj.manual_slot_limit,
        "treatment_minutes": dict(treatment_minutes or {}),
        "sms_template": obj.sms_template or "",
        "auto_backup_enabled": bool(obj.auto_backup_enabled),
        "auto_backup_interval_min": obj.auto_backup_interval_min or 60,
        "auto_backup_keep_count": obj.auto_backup_keep_count or 30,
    }


__all__ = [
    "mask_api_key",
    "mask_password",
    "serialize_ai_setting",
    "serialize_ai_health_admin",
    "serialize_ai_health_public",
    "serialize_sms_setting",
    "serialize_system_setting",
]
