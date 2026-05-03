"""core.feature_flags — AI / RAG / Vector / Hybrid 기능 플래그 통합 진입점 (신규).

19-P-2 §2-1 V2 트리의 ``app/core/feature_flags.py`` — 신규 helper.

본 모듈은 ``ai_mode`` (local_only / local_first / ai_assist) 와 환경변수
(``AI_RAG_ENABLED`` / ``AI_VECTOR_ENABLED`` / ``AI_HYBRID_ENABLED``) 를 *하나의 진입점* 에서
조회할 수 있게 한다. 19-2 시점에는 *기존 ``AiSetting`` / ``app.services.ai.health`` 가
참조하지 않는다* — 신규 modules 가 점진적으로 채택할 수 있는 facade.

19-2 보강:
  - ``derive_ai_mode_from_inputs`` / ``derive_vector_status_from_inputs`` /
    ``derive_external_api_status_from_inputs`` — DB/ORM 의존이 없는 *pure-input*
    helper. 입력으로 ``AiSetting`` 인스턴스 대신 primitives 만 받음.
  - 기존 ``app.services.ai.health.derive_*`` 함수와 동일한 결과를 반환 (분리 후
    회귀 0 보장). 19-2 시점에는 *둘 다 공존* — health.py 는 ORM 친화 인자, core
    는 primitives 인자. modules/health 는 core helper 를 facade 로 wrap.

# COMPAT: 본 모듈은 ``AiSetting.enabled`` / ``ai_mode`` / 환경변수의 *기존 의미를
#         변경하지 않는다*. 단순히 *조회 진입점* 만 통합 — 실제 값은 DB / env 에서
#         그대로 읽음. health.py 의 응답 키 (``ai_mode`` / ``search_mode`` /
#         ``vector_status`` / ``external_api``) 무변경.

# SAFETY: ``local_only`` 모드에서는 외부 LLM/Embedding 호출 0 (DEC-N 절대 원칙).
#         본 helper 는 *값 조회* 만 — 외부 호출 차단 자체는 ``app.services.ai.provider``
#         + ``tests/conftest.py:_block_sdk_modules`` 가 담당. ``api_key`` /
#         ``model`` 원문은 helper 결과에 포함 ⊥ — boolean / enum 만 반환.

# NOTE: 환경변수 vs DB (AiSetting) 단일 진실원천 결정 (T-8 19-P-2) 은 본 19-2
#       시점에 *분류만* 확정 — DB ``AiSetting.enabled`` 가 1차 진실원천이며 환경
#       변수는 *조회 helper 단위* 의 보조 (선택 기능 토글). 통합 시점은
#       post-19-P 에서 결정.

# RISK: ``ai_mode`` 도출 결과는 사용자 운영 환경에 직접 영향 — 잘못 도출하면 외부
#       API 호출 발생 또는 AI 비활성화. 본 19-2 contract 테스트가 health.py 와의
#       동등성을 검증.
"""
from __future__ import annotations

import os
from typing import Final, Literal


# ─── ai_mode 값 enumeration (DEC-N + 19-P-2 §3-10 정합) ───────────────────────

AiMode = Literal["local_only", "local_first", "ai_assist"]

AI_MODE_LOCAL_ONLY: Final[str] = "local_only"
AI_MODE_LOCAL_FIRST: Final[str] = "local_first"
AI_MODE_AI_ASSIST: Final[str] = "ai_assist"

AI_MODE_VALUES: Final[tuple[str, ...]] = (
    AI_MODE_LOCAL_ONLY,
    AI_MODE_LOCAL_FIRST,
    AI_MODE_AI_ASSIST,
)


# ─── 환경변수 키 (기존 정합) ──────────────────────────────────────────────────

ENV_AI_MODE: Final[str] = "AI_MODE"
ENV_AI_RAG_ENABLED: Final[str] = "AI_RAG_ENABLED"
ENV_AI_VECTOR_ENABLED: Final[str] = "AI_VECTOR_ENABLED"
ENV_AI_HYBRID_ENABLED: Final[str] = "AI_HYBRID_ENABLED"


# ─── 환경변수 boolean 파싱 helper ────────────────────────────────────────────

_TRUE_VALUES: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})


def _env_bool(key: str, default: bool = False) -> bool:
    """환경변수 boolean 파싱. ``"1"`` / ``"true"`` / ``"yes"`` / ``"on"`` (case-insensitive) → True.

    NOTE: 기존 ``app.services.ai.health`` 의 환경변수 파싱 패턴 정합.
    """
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


# ─── 환경변수 우선 조회 helper (DB fallback 은 19-2 settings 분리 시점에 통합) ─

def env_ai_mode_or_none() -> str | None:
    """환경변수 ``AI_MODE`` 가 설정되어 있으면 값 반환 (검증 후), 아니면 None.

    NOTE: ``AiMode`` 값 (local_only / local_first / ai_assist) 외에는 None 반환.
    DB ``AiSetting`` fallback 은 호출자가 처리 (19-2 settings 분리 시점에 통합).
    """
    raw = os.environ.get(ENV_AI_MODE)
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in AI_MODE_VALUES:
        return val
    return None


def env_rag_enabled(default: bool = True) -> bool:
    """``AI_RAG_ENABLED`` 환경변수 조회. 미설정 시 default (True).

    NOTE: 18-1 RAG 구조 도입 후 기본 활성. ``AI_RAG_ENABLED=0`` 으로 비활성화 가능.
    """
    return _env_bool(ENV_AI_RAG_ENABLED, default=default)


def env_vector_enabled(default: bool = False) -> bool:
    """``AI_VECTOR_ENABLED`` 환경변수 조회. 미설정 시 default (False).

    NOTE: 18-5 Vector 구조 도입 후 *선택 기능*. embedding provider 가 필요하므로
    기본 비활성. ``AI_VECTOR_ENABLED=1`` 로 활성화.
    """
    return _env_bool(ENV_AI_VECTOR_ENABLED, default=default)


def env_hybrid_enabled(default: bool = False) -> bool:
    """``AI_HYBRID_ENABLED`` 환경변수 조회. 미설정 시 default (False).

    NOTE: 18-6 Hybrid 구조 도입 후 *선택 기능*. vector + keyword 결합. 기본 비활성.
    """
    return _env_bool(ENV_AI_HYBRID_ENABLED, default=default)


# ─── 19-2 pure-input helper (ORM 의존 0) ──────────────────────────────────────
#
# NOTE: 아래 helper 는 ``app.services.ai.health.derive_*`` 와 *동일한 결과* 를 내야
# 한다 — 19-2 contract 테스트 (`test_feature_flags_helpers.py`) 가 두 경로의 출력을
# 비교 검증. 변경 시 health.py 도 같이 변경 (단일 진실원천 책임은 분리 후 본
# 모듈로 이동 예정 — TODO(post-19-P)).


def derive_ai_mode_from_inputs(
    *,
    enabled: bool,
    api_key: str | None,
    model: str | None,
) -> str:
    """``AiSetting`` 의 primitives 로부터 effective AI 모드 파생.

    health.py:derive_ai_mode 와 동일한 룰 (18-7):
      - enabled=False                   → "local_only"
      - enabled + api_key 미설정         → "local_only"
      - enabled + model 미설정           → "local_only"
      - 그 외                           → "local_first"

    SAFETY: ``api_key`` / ``model`` 원문은 결과에 포함 ⊥ — boolean 판정 후 enum 반환.
    """
    if not bool(enabled):
        return AI_MODE_LOCAL_ONLY
    if not (api_key or "").strip():
        return AI_MODE_LOCAL_ONLY
    if not (model or "").strip():
        return AI_MODE_LOCAL_ONLY
    return AI_MODE_LOCAL_FIRST


def derive_vector_status_from_inputs(
    *,
    enabled: bool,
    api_key: str | None,
    provider: str | None,
    sdk_installed: dict[str, bool] | None = None,
    vector_enabled: bool = False,
) -> dict:
    """vector 사용 가능 여부 + 사유 — pure-input.

    health.py:derive_vector_status 와 동등 (m014 미도입 → 항상 enabled=False).

    인자:
      enabled         : ``AiSetting.enabled`` (AI 자체 enabled 여부).
      api_key         : ``AiSetting.api_key`` 원문 — 빈 여부만 판정 (반환 ⊥).
      provider        : ``AiSetting.provider`` (openai / anthropic / local).
      sdk_installed   : provider→bool dict (이미 설치된 SDK).
      vector_enabled  : 운영 토글 — m014 도입 전 항상 False (기본값 False).

    반환 키 (3): ``enabled / available / reason``.
    """
    # NOTE: 본 helper 는 health.py:derive_vector_status 와 동일한 출력 — m014 미도입
    # 시점은 ``enabled`` (AiSetting.enabled) 와 무관하게 ``vector_enabled=False`` 분기에서
    # ``vector_disabled`` 반환. m014 path (``vector_enabled=True``) 에서는 api_key /
    # sdk / provider 만 검사. ``enabled`` 인자는 호출 측 시그니처 일관성을 위해 받지만
    # 본 단계에서는 사용하지 않음 — TODO(post-19-P): m014 도입 후 정책 명시.
    _ = enabled  # placeholder — m014 도입 후 정책 결정
    sdk_installed = sdk_installed or {}
    if not vector_enabled:
        return {
            "enabled": False,
            "available": False,
            "reason": "vector_disabled",
        }
    api_key_set = bool((api_key or "").strip())
    if not api_key_set:
        return {"enabled": True, "available": False, "reason": "api_key_missing"}
    provider_name = (provider or "").strip().lower()
    if provider_name in ("openai", "anthropic") and not sdk_installed.get(
        provider_name, False
    ):
        return {"enabled": True, "available": False, "reason": "sdk_missing"}
    return {"enabled": True, "available": True, "reason": ""}


def derive_external_api_status_from_inputs(
    *,
    enabled: bool,
    api_key: str | None,
    model: str | None,
    provider: str | None,
    sdk_installed: dict[str, bool] | None = None,
) -> dict:
    """외부 API 사용 가능 여부 — pure-input.

    health.py:derive_external_api_status 와 동등 (LLM / Embedding 분리).

    반환 키 (3):
      ``llm_available``        : enabled + api_key + model + provider sdk 모두 OK.
      ``embedding_available``  : 18-7 시점 항상 False (운영 미구현).
      ``sdk_installed``        : provider→bool dict (입력 그대로 dict 복사).

    SAFETY: ``api_key`` / ``model`` 원문은 결과에 포함 ⊥.
    """
    sdk_installed = sdk_installed or {}
    api_key_set = bool((api_key or "").strip())
    model_set = bool((model or "").strip())
    provider_name = (provider or "").strip().lower()
    provider_sdk_ok = bool(sdk_installed.get(provider_name, False))
    llm_available = bool(
        enabled and api_key_set and model_set and provider_sdk_ok
    )
    return {
        "llm_available": llm_available,
        "embedding_available": False,
        "sdk_installed": dict(sdk_installed),
    }


__all__ = [
    "AiMode",
    "AI_MODE_LOCAL_ONLY",
    "AI_MODE_LOCAL_FIRST",
    "AI_MODE_AI_ASSIST",
    "AI_MODE_VALUES",
    "ENV_AI_MODE",
    "ENV_AI_RAG_ENABLED",
    "ENV_AI_VECTOR_ENABLED",
    "ENV_AI_HYBRID_ENABLED",
    "env_ai_mode_or_none",
    "env_rag_enabled",
    "env_vector_enabled",
    "env_hybrid_enabled",
    "derive_ai_mode_from_inputs",
    "derive_vector_status_from_inputs",
    "derive_external_api_status_from_inputs",
]
