"""API 응답 계약 단언 — 18-0 RAG 하네스.

v1.3.3 ``/api/ai/manual/{search,ask}`` 응답 키를 후방호환으로 보호한다.

기존 키:
  manual/search → ``sources[]`` (각 항목 ``title`` / ``path`` / ``snippet``),
                  ``masked_question``, ``top_score``
  manual/ask    → ``answer``, ``sources[]``, ``confidence``, ``not_found``,
                  ``blocked``, ``blocked_reason``, ``guard_hits``,
                  ``top_score``, ``masked_question``  (총 9개)

신규 optional 키 (추가만 허용 — 응답에 없어도 단언 통과):
  ``reason_code``, ``llm_called``, ``ai_mode``, ``prompt_version``
(``embedding_called`` 는 18-5 chunk + vector 도입 시점에 다시 추가될 예정)
"""
from __future__ import annotations

from typing import Any

# v1.3.3 응답 키 — 제거/이름 변경/타입 변경 절대 금지.
MANUAL_SEARCH_REQUIRED = ("sources", "masked_question", "top_score")
MANUAL_ASK_REQUIRED = (
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
SOURCE_ITEM_REQUIRED = ("title", "path", "snippet")

# 18-3 이후 응답에 추가될 수 있는 신규 optional 키 (있어도 OK, 없어도 OK).
# ``embedding_called`` 는 18-5 chunk + vector 도입 시점에 다시 추가.
OPTIONAL_KEYS = (
    "reason_code",
    "llm_called",
    "ai_mode",
    "prompt_version",
)

CONFIDENCE_VALUES = ("high", "low", "unknown")


def assert_manual_search_contract(body: dict) -> None:
    """``/api/ai/manual/search`` 200 응답 계약."""
    for k in MANUAL_SEARCH_REQUIRED:
        assert k in body, f"manual/search missing key: {k!r} in {sorted(body)}"
    assert isinstance(body["sources"], list), \
        f"sources must be list, got {type(body['sources']).__name__}"
    assert isinstance(body["masked_question"], str), \
        f"masked_question must be str, got {type(body['masked_question']).__name__}"
    assert isinstance(body["top_score"], int), \
        f"top_score must be int, got {type(body['top_score']).__name__}"
    for s in body["sources"]:
        assert_source_item_contract(s)


def assert_manual_ask_contract(body: dict) -> None:
    """``/api/ai/manual/ask`` 200 응답 계약 (success / no_result / safety_block 공통)."""
    for k in MANUAL_ASK_REQUIRED:
        assert k in body, f"manual/ask missing key: {k!r} in {sorted(body)}"
    assert isinstance(body["answer"], str), \
        f"answer must be str, got {type(body['answer']).__name__}"
    assert isinstance(body["sources"], list), \
        f"sources must be list, got {type(body['sources']).__name__}"
    assert body["confidence"] in CONFIDENCE_VALUES, \
        f"confidence must be one of {CONFIDENCE_VALUES}, got {body['confidence']!r}"
    assert isinstance(body["not_found"], bool), \
        f"not_found must be bool, got {type(body['not_found']).__name__}"
    assert isinstance(body["blocked"], bool), \
        f"blocked must be bool, got {type(body['blocked']).__name__}"
    assert isinstance(body["blocked_reason"], str), \
        f"blocked_reason must be str, got {type(body['blocked_reason']).__name__}"
    assert isinstance(body["guard_hits"], int), \
        f"guard_hits must be int, got {type(body['guard_hits']).__name__}"
    assert isinstance(body["top_score"], int), \
        f"top_score must be int, got {type(body['top_score']).__name__}"
    assert isinstance(body["masked_question"], str), \
        f"masked_question must be str, got {type(body['masked_question']).__name__}"
    for s in body["sources"]:
        assert_source_item_contract(s)


def assert_source_item_contract(source: dict) -> None:
    """``sources[]`` 항목 계약 (title/path/snippet)."""
    for k in SOURCE_ITEM_REQUIRED:
        assert k in source, \
            f"source item missing key: {k!r} in {sorted(source)}"
        assert isinstance(source[k], str), \
            f"source[{k!r}] must be str, got {type(source[k]).__name__}"


def assert_no_unknown_required_keys(body: dict, required: tuple) -> None:
    """현재 응답에 누락된 required 키 검출. 본 모듈 내부 단언과 동일하지만
    개별 호출처에서 명시적으로 사용 가능."""
    missing = [k for k in required if k not in body]
    assert not missing, f"missing required keys: {missing}"


__all__: list[Any] = [
    "MANUAL_SEARCH_REQUIRED",
    "MANUAL_ASK_REQUIRED",
    "SOURCE_ITEM_REQUIRED",
    "OPTIONAL_KEYS",
    "CONFIDENCE_VALUES",
    "assert_manual_search_contract",
    "assert_manual_ask_contract",
    "assert_source_item_contract",
    "assert_no_unknown_required_keys",
]
