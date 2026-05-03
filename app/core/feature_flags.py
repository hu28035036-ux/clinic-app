"""core.feature_flags — AI / RAG / Vector / Hybrid 기능 플래그 통합 진입점 (신규).

19-P-2 §2-1 V2 트리의 ``app/core/feature_flags.py`` — 신규 helper.

본 모듈은 ``ai_mode`` (local_only / local_first / ai_assist) 와 환경변수
(``AI_RAG_ENABLED`` / ``AI_VECTOR_ENABLED`` / ``AI_HYBRID_ENABLED``) 를 *하나의 진입점* 에서
조회할 수 있게 한다. 19-1 시점에는 *기존 ``AiSetting`` / ``app.services.ai.health`` 가
참조하지 않는다* — 신규 modules 가 점진적으로 채택할 수 있는 facade.

# COMPAT: 본 모듈은 ``AiSetting.enabled`` / ``ai_mode`` / 환경변수의 *기존 의미를
#         변경하지 않는다*. 단순히 *조회 진입점* 만 통합 — 실제 값은 DB / env 에서
#         그대로 읽음.

# SAFETY: ``local_only`` 모드에서는 외부 LLM/Embedding 호출 0 (DEC-N 절대 원칙).
#         본 helper 는 *값 조회* 만 — 외부 호출 차단 자체는 ``app.services.ai.provider``
#         + ``tests/conftest.py:_block_sdk_modules`` 가 담당.

# NOTE: 환경변수 vs DB (AiSetting) 단일 진실원천 결정 (T-8 19-P-2) 은 19-2 settings
#       세션에서 확정. 본 19-1 helper 는 *환경변수 우선 + DB fallback* 패턴 (기존
#       ``health.py`` / ``manual_qa.py`` 의 ``ai_mode`` 도출 정합).

# RISK: ``ai_mode`` 도출 결과는 사용자 운영 환경에 직접 영향 — 잘못 도출하면 외부
#       API 호출 발생 또는 AI 비활성화. 19-x 분리 시점에 contract 테스트로 확인.
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
]
