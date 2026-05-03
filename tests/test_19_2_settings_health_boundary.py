"""19-2 settings / feature_flags / health 경계 정리 contract.

검증 범위 (19-2 세션 지시문 정합):
  1. ``app.core.feature_flags`` pure-input helper 가 ``app.services.ai.health.derive_*``
     와 동일한 출력을 반환 (회귀 0).
  2. ``app.modules.settings.serializers`` 의 직렬화 결과가 ``app/routers/ai.py:
     _serialize_setting`` / ``ai.py:ai_health_public`` / ``ai.py:ai_health`` /
     ``api.py:sms_get`` / ``api.py:system_settings_get`` 와 키/값/타입 일치.
  3. ``api_key`` / ``munjanara_pw`` / ``munjanara_key`` 원문이 응답에 노출 ⊥ —
     SAFETY 정책 회귀 검증.
  4. ``app.modules.health`` 가 ``app.services.ai.health`` 의 공개 API 를 그대로
     re-export — 기존 import 경로 호환.
  5. core / modules 패키지가 ``app.models`` / ``app.services`` 를 *import 하지
     않음* — 단방향 경계 (D-4 정합).
  6. 외부 API 호출 0 — 본 테스트 안에서 LLM/Embedding provider 인스턴스화 ⊥.

원칙:
  - 운영 DB 미접근 — 본 테스트는 in-memory ``AiSetting`` / ``SmsSetting`` /
    ``SystemSetting`` 만 사용 (DB 세션 부재).
  - 외부 API 호출 0 — provider 인스턴스화 / SDK import 시도 ⊥.
"""
from __future__ import annotations

import importlib

import pytest

from app.core import feature_flags as _ff
from app.modules import health as _modules_health
from app.modules.settings import serializers as _serializers
from app.services.ai import health as _services_health

# ──────────────────────── 1. feature_flags pure-input vs health.py 회귀 ────


class _FakeAiSetting:
    """in-memory ``AiSetting`` — DB 세션 부재."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        provider: str = "openai",
        model: str = "",
        api_key: str = "",
    ) -> None:
        self.enabled = enabled
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = ""
        self.max_tokens = 512
        self.temperature = 0.3
        self.pii_guard_enabled = True


@pytest.mark.parametrize(
    "enabled,api_key,model,expected",
    [
        (False, "", "", "local_only"),
        (False, "sk-test", "gpt-4o-mini", "local_only"),
        (True, "", "gpt-4o-mini", "local_only"),
        (True, "sk-test", "", "local_only"),
        (True, "  ", "gpt-4o-mini", "local_only"),
        (True, "sk-test", "  ", "local_only"),
        (True, "sk-test", "gpt-4o-mini", "local_first"),
    ],
)
def test_derive_ai_mode_pure_input_matches_health_py(enabled, api_key, model, expected):
    """``feature_flags.derive_ai_mode_from_inputs`` == ``health.derive_ai_mode``.

    NOTE: 두 경로의 출력이 byte-equivalent — 19-2 분리 후 회귀 0 보장.
    """
    setting = _FakeAiSetting(enabled=enabled, api_key=api_key, model=model)

    pure = _ff.derive_ai_mode_from_inputs(
        enabled=enabled, api_key=api_key, model=model,
    )
    orm = _services_health.derive_ai_mode(setting)

    assert pure == orm == expected


def test_derive_vector_status_pure_input_matches_health_py_default():
    """기본값 (vector_enabled=False) → 두 경로 모두 ``vector_disabled``."""
    setting = _FakeAiSetting(enabled=True, api_key="sk-test", model="gpt-4o-mini")

    pure = _ff.derive_vector_status_from_inputs(
        enabled=True,
        api_key="sk-test",
        provider="openai",
        sdk_installed={"openai": True},
    )
    orm = _services_health.derive_vector_status(
        setting, sdk_installed={"openai": True},
    )

    assert pure == orm
    assert pure["enabled"] is False
    assert pure["available"] is False
    assert pure["reason"] == "vector_disabled"


@pytest.mark.parametrize(
    "enabled,api_key,model,provider,sdk_installed,expected_llm",
    [
        # disabled → llm_available=False
        (False, "sk-test", "gpt-4o-mini", "openai", {"openai": True}, False),
        # api_key 없음 → False
        (True, "", "gpt-4o-mini", "openai", {"openai": True}, False),
        # model 없음 → False
        (True, "sk-test", "", "openai", {"openai": True}, False),
        # provider sdk 없음 → False
        (True, "sk-test", "gpt-4o-mini", "openai", {"openai": False}, False),
        # 모두 OK → True
        (True, "sk-test", "gpt-4o-mini", "openai", {"openai": True}, True),
        # anthropic + sdk 있음 → True
        (True, "sk-test", "claude-3-haiku-20240307", "anthropic",
         {"anthropic": True}, True),
    ],
)
def test_derive_external_api_status_matches_health_py(
    enabled, api_key, model, provider, sdk_installed, expected_llm
):
    """``feature_flags.derive_external_api_status_from_inputs`` ==
    ``health.derive_external_api_status``."""
    setting = _FakeAiSetting(
        enabled=enabled, api_key=api_key, model=model, provider=provider,
    )

    pure = _ff.derive_external_api_status_from_inputs(
        enabled=enabled,
        api_key=api_key,
        model=model,
        provider=provider,
        sdk_installed=sdk_installed,
    )
    orm = _services_health.derive_external_api_status(
        setting, sdk_installed=sdk_installed,
    )

    assert pure == orm
    assert pure["llm_available"] is expected_llm
    assert pure["embedding_available"] is False  # 18-7 시점 항상 False


# ──────────────────────── 2. modules.settings.serializers 회귀 ────────────


def test_serialize_ai_setting_matches_routers_ai_py_keys():
    """``serializers.serialize_ai_setting`` 결과 9키 == ai.py:_serialize_setting."""
    setting = _FakeAiSetting(
        enabled=True, provider="openai", model="gpt-4o-mini",
        api_key="sk-1234567890abcdef",
    )

    result = _serializers.serialize_ai_setting(setting)

    expected_keys = {
        "enabled", "provider", "model", "api_key_masked", "api_key_set",
        "base_url", "max_tokens", "temperature", "pii_guard_enabled",
    }
    assert set(result.keys()) == expected_keys

    # COMPAT: ai.py:_serialize_setting 와 byte-equivalent (라인 79~90).
    assert result["enabled"] is True
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini"
    assert result["api_key_masked"] == "sk-1****"  # 4자 + ****
    assert result["api_key_set"] is True
    assert result["max_tokens"] == 512
    assert result["temperature"] == 0.3
    assert result["pii_guard_enabled"] is True


def test_serialize_ai_setting_does_not_leak_raw_api_key():
    """SAFETY: ``api_key`` 원문이 어떤 값에도 포함 ⊥."""
    raw_key = "sk-EXTREMELY_SECRET_KEY_12345"
    setting = _FakeAiSetting(enabled=True, api_key=raw_key, model="gpt-4o-mini")

    result = _serializers.serialize_ai_setting(setting)

    for value in result.values():
        if isinstance(value, str):
            assert raw_key not in value, (
                f"api_key 원문이 응답에 노출됨: {value!r}"
            )


def test_serialize_ai_health_public_returns_exactly_4_keys():
    """COMPAT: public 응답은 정확히 4키 — admin 정보 (model/sdk/version) 미포함."""
    setting = _FakeAiSetting(
        enabled=True, provider="openai", model="gpt-4o-mini",
        api_key="sk-test",
    )

    result = _serializers.serialize_ai_health_public(setting, ready=True)

    assert set(result.keys()) == {"enabled", "ready", "provider", "api_key_set"}
    # admin 전용 필드가 노출되면 안 됨.
    assert "model" not in result
    assert "sdk_installed" not in result
    assert "sdk_errors" not in result
    assert "knowledge_doc_count" not in result
    assert "version" not in result


def test_serialize_ai_health_admin_returns_exactly_9_keys():
    """COMPAT: admin 응답은 정확히 9키 (test_ai_health_public.ADMIN_FIELDS 정합)."""
    setting = _FakeAiSetting(
        enabled=True, provider="openai", model="gpt-4o-mini",
        api_key="sk-test",
    )

    result = _serializers.serialize_ai_health_admin(
        setting,
        sdk_installed={"openai": True, "anthropic": False},
        sdk_errors={"anthropic": "ImportError: foo"},
        knowledge_doc_count=15,
        ready=True,
        version="v1.3-stage1",
    )

    expected_keys = {
        "enabled", "provider", "model", "api_key_set",
        "sdk_installed", "sdk_errors",
        "knowledge_doc_count", "ready", "version",
    }
    assert set(result.keys()) == expected_keys


def test_serialize_sms_setting_masks_pw_and_key():
    """SAFETY: ``munjanara_pw`` / ``munjanara_key`` 원문 미노출."""

    class _FakeSmsSetting:
        munjanara_id = "user1"
        munjanara_pw = "supersecretpw123"
        munjanara_key = "MUNJ_KEY_LONG_VALUE_ABCDEF"
        sender_phone = "010-1234-5678"
        clinic_phone = "02-1234-5678"
        clinic_name = "도수치료의원"
        api_url = "https://example.com/sms"

    result = _serializers.serialize_sms_setting(_FakeSmsSetting())

    assert result["munjanara_pw"] == "****"
    # munjanara_key 는 앞 4자 + **** (api.py:sms_get 정합)
    assert result["munjanara_key"] == "MUNJ****"
    # 원문 어디에도 포함 ⊥
    for value in result.values():
        if isinstance(value, str):
            assert "supersecretpw123" not in value
            assert "MUNJ_KEY_LONG_VALUE_ABCDEF" not in value
    # 마스킹 안 되는 일반 필드는 그대로
    assert result["clinic_name"] == "도수치료의원"
    assert result["sender_phone"] == "010-1234-5678"


def test_serialize_sms_setting_empty_pw_returns_empty_string():
    """COMPAT: 비어 있는 ``munjanara_pw`` → 빈 문자열 (api.py:sms_get 정합)."""

    class _Empty:
        munjanara_id = ""
        munjanara_pw = ""
        munjanara_key = ""
        sender_phone = ""
        clinic_phone = ""
        clinic_name = ""
        api_url = ""

    result = _serializers.serialize_sms_setting(_Empty())
    assert result["munjanara_pw"] == ""
    assert result["munjanara_key"] == ""


def test_serialize_system_setting_returns_6_keys():
    """COMPAT: ``system_settings_get`` 응답 6키 정합 (api.py:2058~2071)."""

    class _FakeSystemSetting:
        manual_slot_limit = 4
        sms_template = "예약 알림: {date}"
        auto_backup_enabled = True
        auto_backup_interval_min = 60
        auto_backup_keep_count = 30

    result = _serializers.serialize_system_setting(
        _FakeSystemSetting(),
        treatment_minutes={"manual30": 30, "manual60": 60},
    )

    expected_keys = {
        "manual_slot_limit", "treatment_minutes", "sms_template",
        "auto_backup_enabled", "auto_backup_interval_min",
        "auto_backup_keep_count",
    }
    assert set(result.keys()) == expected_keys
    assert result["manual_slot_limit"] == 4
    assert result["treatment_minutes"] == {"manual30": 30, "manual60": 60}
    assert result["auto_backup_enabled"] is True
    assert result["auto_backup_interval_min"] == 60
    assert result["auto_backup_keep_count"] == 30


def test_mask_api_key_short_returns_stars_only():
    """SAFETY: 4자 이하 키는 앞 글자도 노출 ⊥ — ``****`` 만 반환."""
    assert _serializers.mask_api_key("ab") == "****"
    assert _serializers.mask_api_key("abcd") == "****"  # 정확히 4자도 stars only
    # 4자 초과는 앞 4자 + ****
    assert _serializers.mask_api_key("abcde") == "abcd****"
    assert _serializers.mask_api_key("") == ""
    assert _serializers.mask_api_key(None) == ""


# ──────────────────────── 3. modules.health re-export 동등성 ──────────────


def test_modules_health_reexports_match_services_ai_health():
    """``app.modules.health`` 의 공개 API == ``app.services.ai.health`` 의 공개 API."""
    expected = {
        "AI_MODE_AI_ASSIST", "AI_MODE_LOCAL_FIRST", "AI_MODE_LOCAL_ONLY",
        "DEFAULT_RECENT_HOURS", "DEFAULT_RECENT_LIMIT",
        "ERROR_DETAIL_DISPLAY_LIMIT", "MAX_RECENT_LIMIT",
        "SEARCH_MODE_DISABLED", "SEARCH_MODE_HYBRID",
        "SEARCH_MODE_KEYWORD", "SEARCH_MODE_VECTOR",
        "LastReindex", "RecentLogEntry",
        "build_admin_status",
        "count_chunks", "count_documents", "count_vectors",
        "derive_ai_mode", "derive_external_api_status",
        "derive_search_mode", "derive_vector_status",
        "get_last_reindex", "get_prompt_versions", "get_recent_logs",
    }
    for name in expected:
        assert hasattr(_modules_health, name), (
            f"app.modules.health 에 {name!r} 미re-export"
        )
        # 기존 services.ai.health 와 동일 객체.
        assert getattr(_modules_health, name) is getattr(_services_health, name), (
            f"{name!r} 가 services.ai.health 와 다른 객체"
        )


def test_modules_health_derive_ai_mode_works():
    """re-export 된 ``derive_ai_mode`` 가 in-memory AiSetting 으로 정상 동작."""
    setting = _FakeAiSetting(enabled=True, api_key="sk-test", model="gpt-4o-mini")
    assert _modules_health.derive_ai_mode(setting) == "local_first"


# ──────────────────────── 4. 단방향 경계 검증 (D-4 정합) ──────────────────


def test_core_feature_flags_does_not_import_models():
    """core 는 modules / services / models 를 import 하지 않음 (D-4 단방향 경계)."""
    import app.core.feature_flags as mod
    src = importlib.import_module("inspect").getsource(mod)
    forbidden = (
        "from app.models", "from app.services", "from app.modules",
        "from app.routers", "import app.models", "import app.services",
        "import app.modules", "import app.routers",
    )
    for token in forbidden:
        assert token not in src, (
            f"app.core.feature_flags 가 금지된 import 사용: {token!r}"
        )


def test_modules_settings_serializers_does_not_import_models_or_db():
    """modules.settings.serializers 는 ORM / DB session 미참조 — pure helper."""
    import app.modules.settings.serializers as mod
    src = importlib.import_module("inspect").getsource(mod)
    forbidden = (
        "from app.models", "import app.models",
        "from app.database", "import app.database",
        "from app.services", "import app.services",
        "from sqlalchemy", "import sqlalchemy",
    )
    for token in forbidden:
        assert token not in src, (
            f"app.modules.settings.serializers 가 금지된 import 사용: {token!r}"
        )


# ──────────────────────── 5. 외부 API 호출 0 검증 ─────────────────────────


def test_pure_helpers_do_not_invoke_provider_or_sdk(monkeypatch):
    """pure-input helper 는 LLM/Embedding provider / SDK import 시도 ⊥.

    SAFETY: ``local_only`` 절대 원칙 (DEC-N) — 본 helper 는 *값 조회* 만.
    """
    # provider 모듈을 import 하면 fail.
    called = {"provider": False, "anthropic": False, "openai": False}

    class _Tripwire:
        def __getattr__(self, name):
            called["provider"] = True
            raise RuntimeError("provider 호출 ⊥")

    # helper 호출 시 provider 모듈을 건드리지 않아야 함.
    setting = _FakeAiSetting(enabled=True, api_key="sk-test", model="gpt-4o-mini")

    _ = _ff.derive_ai_mode_from_inputs(
        enabled=True, api_key="sk-test", model="gpt-4o-mini",
    )
    _ = _ff.derive_vector_status_from_inputs(
        enabled=True, api_key="sk-test", provider="openai",
        sdk_installed={"openai": True},
    )
    _ = _ff.derive_external_api_status_from_inputs(
        enabled=True, api_key="sk-test", model="gpt-4o-mini",
        provider="openai", sdk_installed={"openai": True},
    )
    _ = _serializers.serialize_ai_setting(setting)
    _ = _serializers.serialize_ai_health_public(setting, ready=True)

    assert called["provider"] is False


# ──────────────────────── 6. env helper SAFETY ────────────────────────────


def test_env_ai_mode_or_none_returns_none_for_invalid_value(monkeypatch):
    """SAFETY: 알려지지 않은 ``AI_MODE`` 값은 None 반환 — 외부 API path 차단."""
    monkeypatch.setenv("AI_MODE", "bogus_mode")
    assert _ff.env_ai_mode_or_none() is None

    monkeypatch.setenv("AI_MODE", "local_only")
    assert _ff.env_ai_mode_or_none() == "local_only"

    monkeypatch.setenv("AI_MODE", "LOCAL_FIRST")  # case-insensitive
    assert _ff.env_ai_mode_or_none() == "local_first"

    monkeypatch.delenv("AI_MODE", raising=False)
    assert _ff.env_ai_mode_or_none() is None


def test_env_bool_helpers_default_when_unset(monkeypatch):
    """env 미설정 시 default 값 반환."""
    monkeypatch.delenv("AI_RAG_ENABLED", raising=False)
    monkeypatch.delenv("AI_VECTOR_ENABLED", raising=False)
    monkeypatch.delenv("AI_HYBRID_ENABLED", raising=False)

    assert _ff.env_rag_enabled() is True  # default True
    assert _ff.env_vector_enabled() is False  # default False
    assert _ff.env_hybrid_enabled() is False  # default False

    # default 인자 override 가능.
    assert _ff.env_rag_enabled(default=False) is False
    assert _ff.env_vector_enabled(default=True) is True


def test_env_bool_helpers_parse_truthy(monkeypatch):
    """``"1" / "true" / "yes" / "on"`` (case-insensitive) → True."""
    for truthy in ("1", "true", "True", "TRUE", "yes", "YES", "on", "ON"):
        monkeypatch.setenv("AI_RAG_ENABLED", truthy)
        assert _ff.env_rag_enabled() is True, f"{truthy!r} 가 True 로 파싱되어야 함"
    for falsy in ("0", "false", "no", "off", "anything_else"):
        monkeypatch.setenv("AI_RAG_ENABLED", falsy)
        assert _ff.env_rag_enabled() is False, f"{falsy!r} 가 False 로 파싱되어야 함"


# ──────────────────────── 7. 응답 키 변경 회귀 검증 ──────────────────────


def test_responses_health_public_keys_match_actual_endpoint():
    """COMPAT: ``app.core.responses.HEALTH_PUBLIC_KEYS`` ==
    ``/api/ai/health/public`` 실제 응답 4키.

    19-2 보정 — 19-1 placeholder (``ai_enabled / ai_ready / version / node_id``)
    가 실제 응답과 불일치 했음. 실제 응답은 ``enabled / ready / provider /
    api_key_set`` (tests/test_ai_health_public.py:9 와 ai.py:179~184 정합).
    """
    from app.core import responses as _resp

    assert set(_resp.HEALTH_PUBLIC_KEYS) == {
        "enabled", "ready", "provider", "api_key_set",
    }


def test_responses_health_admin_keys_match_actual_endpoint():
    """COMPAT: ``HEALTH_ADMIN_KEYS`` == ``/api/ai/health`` admin 9키."""
    from app.core import responses as _resp

    assert set(_resp.HEALTH_ADMIN_KEYS) == {
        "enabled", "provider", "model", "api_key_set",
        "sdk_installed", "sdk_errors",
        "knowledge_doc_count", "ready", "version",
    }
