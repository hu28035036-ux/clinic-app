"""RAG 하네스 (18-0 최소 버전).

매뉴얼 RAG 검색·답변 흐름 검증 helper.

이번 세션 범위:
  - knowledge fixture: 현행 ``knowledge/manuals/*.md`` 그대로 사용 (이미 동봉됨).
  - LLM 호출 게이트 검증 helper.
  - ``expect_no_external_call(provider, embedding_provider=None)``.

상세 설계: ``docs/harnesses/rag_harness_plan.md``.
"""
from __future__ import annotations

from typing import Any, Optional

from .fake_provider import FakeProvider, call_count

# 매뉴얼 keyword search 가 score>=2 로 매칭하는, 18-0 시점에 안정적으로 동작
# 한다고 검증된 질문들 (현행 ``knowledge/manuals/*.md`` 기준).
KNOWN_QUESTIONS = (
    "예약문자 작성",        # → sms_compose.md
    "백업은 어디서 해?",    # → backup.md
)

# 어떤 매뉴얼도 매칭되지 않아 ``not_found=true`` 가 나와야 하는 질문들.
UNKNOWN_QUESTIONS = (
    "오늘 점심 메뉴 추천해줘 짜장면 짬뽕",
    "주식 추천해줘",
)


def expect_no_external_call(
    provider: FakeProvider,
    embedding_provider: Optional[Any] = None,
) -> None:
    """provider / embedding_provider 모두 호출 0 단언.

    18-0~18-4 범위에서는 embedding_provider 가 호출되면 자체로 위반.
    18-5 이후에도 ``local_only`` / 사전 차단 케이스에서 동일 단언이 유효.
    """
    n = call_count(provider)
    assert n == 0, f"expected len(provider.calls) == 0, got {n}"
    if embedding_provider is not None:
        en = len(getattr(embedding_provider, "calls", []) or [])
        assert en == 0, f"expected len(embedding_provider.calls) == 0, got {en}"


__all__: list[Any] = [
    "KNOWN_QUESTIONS",
    "UNKNOWN_QUESTIONS",
    "expect_no_external_call",
]
