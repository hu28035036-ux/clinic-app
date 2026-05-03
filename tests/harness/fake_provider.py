"""FakeProvider helper — 18-0 RAG/Safety 하네스.

기존 ``tests/conftest.py:112`` ``FakeProvider`` 를 재사용하기 위한 얇은
helper 모듈. 새 구현을 추가하지 않고, 호출 카운트/마지막 prompt/system 을
가독성 있게 꺼내기 위한 함수만 제공한다.

표준 컨벤션 (``docs/ai_rag_test_plan.md`` §0-0):
  - provider call count = ``len(provider.calls)``
  - 향후 ``call_count`` property 가 추가되더라도 ``len(.calls)`` 와 동일 값.
"""
from __future__ import annotations

from typing import Any

from tests.conftest import FakeProvider, make_fake_provider


def call_count(provider: FakeProvider) -> int:
    """provider call count — 표준 측정. ``len(provider.calls)``."""
    return len(provider.calls)


def last_prompt(provider: FakeProvider) -> str:
    """가장 최근 ``generate()`` 에 전달된 prompt. 호출 0이면 빈 문자열."""
    return provider.calls[-1]["prompt"] if provider.calls else ""


def last_system(provider: FakeProvider) -> str:
    """가장 최근 ``generate()`` 에 전달된 system 프롬프트. 호출 0이면 빈 문자열."""
    return provider.calls[-1]["system"] if provider.calls else ""


def assert_no_external_call(provider: FakeProvider, msg: str = "") -> None:
    """provider call count == 0 단언."""
    n = call_count(provider)
    assert n == 0, msg or f"expected len(provider.calls) == 0, got {n}"


def assert_provider_received_no_pii(provider: FakeProvider, *patterns: str) -> None:
    """모든 호출의 prompt + system 합본에 PII 패턴이 없는지 단언.

    ``patterns`` 는 원본 PII 문자열들 (예: ``"010-1234-5678"``).
    """
    for c in provider.calls:
        joined = (c.get("prompt") or "") + " " + (c.get("system") or "")
        for p in patterns:
            assert p not in joined, (
                f"FakeProvider received PII '{p}' in prompt/system: "
                f"{joined[:200]!r}"
            )


__all__: list[Any] = [
    "FakeProvider",
    "make_fake_provider",
    "call_count",
    "last_prompt",
    "last_system",
    "assert_no_external_call",
    "assert_provider_received_no_pii",
]
