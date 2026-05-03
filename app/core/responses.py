"""core.responses — 공통 응답 envelope helper (신규).

19-P-2 §2-1 V2 트리의 ``app/core/responses.py`` — 신규 helper.

본 모듈은 modules 가 ``/api/ai/manual/ask`` (9키) / ``/api/ai/manual/search`` (3키) /
``/api/ai/health`` (admin 9키) / 비-AI alias 등 응답을 일관되게 만들 때 쓸 수 있는
helper 와 표준 키 상수를 제공한다.

# COMPAT: 19-P-1 §21 의 33+ 응답 키 셋 (DEC-C 절대 원칙) 100% 보존.
#         본 helper 는 *추가만* — 기존 응답 dict 빌드 위치를 *대체* 하지 않는다.

# NOTE: 본 모듈은 19-1 시점에 *기존 라우터가 참조하지 않는다*. 19-x 분리 시점에
#       modules 가 채택할 때 contract 테스트로 응답 dict 가 dict 단위 비교
#       (분리 전후) 동일함을 검증.

# RISK: ``ManualSearchResponse`` / ``ManualAskResponse`` / ``HealthResponse`` 의
#       키 / 타입은 main.html 7331줄 + 인라인 JS 의존 — 절대 변경 ⊥.
"""
from typing import Any, Final


# ─── /api/ai/manual/search 응답 키 (3키 — manual_qa.py:155-169) ───────────────

MANUAL_SEARCH_KEYS: Final[tuple[str, ...]] = ("sources", "masked_question", "top_score")


# ─── /api/ai/manual/ask 응답 키 (9키 — manual_qa.py:270-280) ──────────────────

MANUAL_ASK_KEYS: Final[tuple[str, ...]] = (
    "answer",
    "sources",
    "confidence",
    "not_found",
    "blocked",
    "blocked_reason",
    "guard_hits",
    "top_score",
    "masked_question",
)


# ─── sources[] 항목 키 (3키) ──────────────────────────────────────────────────

SOURCE_ITEM_KEYS: Final[tuple[str, ...]] = ("title", "path", "snippet")


# ─── /api/ai/health admin 9키 (routers/ai.py:138~166) ────────────────────────

HEALTH_ADMIN_KEYS: Final[tuple[str, ...]] = (
    "enabled",
    "provider",
    "model",
    "api_key_set",
    "sdk_installed",
    "sdk_errors",
    "knowledge_doc_count",
    "ready",
    "version",
)


# ─── /api/ai/health/public 4키 (인증 불필요) ────────────────────────────────────

HEALTH_PUBLIC_KEYS: Final[tuple[str, ...]] = (
    "ai_enabled",
    "ai_ready",
    "version",
    "node_id",
)


# ─── confidence 값 enumeration (manual_ask 응답 ``confidence`` 필드) ───────────

CONFIDENCE_HIGH: Final[str] = "high"
CONFIDENCE_LOW: Final[str] = "low"
CONFIDENCE_UNKNOWN: Final[str] = "unknown"

CONFIDENCE_VALUES: Final[tuple[str, ...]] = (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_UNKNOWN,
)


# ─── helper: dict 응답이 33+ 키 셋 위반 여부 검증 (테스트 / 검증용) ────────────

def assert_keys(response: dict[str, Any], expected: tuple[str, ...]) -> None:
    """response dict 가 expected 키를 모두 포함하는지 단언.

    NOTE: 19-x 분리 직전 contract 테스트에서 사용. 추가 키는 허용 (DEC-C
    "추가만 허용") — 제거 / rename / 타입 변경만 ⊥.
    """
    missing = [k for k in expected if k not in response]
    if missing:
        raise AssertionError(f"응답에 누락된 키: {missing}")


__all__ = [
    "MANUAL_SEARCH_KEYS",
    "MANUAL_ASK_KEYS",
    "SOURCE_ITEM_KEYS",
    "HEALTH_ADMIN_KEYS",
    "HEALTH_PUBLIC_KEYS",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_LOW",
    "CONFIDENCE_UNKNOWN",
    "CONFIDENCE_VALUES",
    "assert_keys",
]
