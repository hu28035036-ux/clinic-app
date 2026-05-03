"""RAG safety gate stub — 18-1.

PII 사전 차단 / invalid_query / unknown_feature 사전 분기.
실제 구현은 18-2 이후. 18-1 시점에는 인터페이스만.

기존 ``app.services.ai.pii`` 의 ``scan()`` 을 그대로 재사용한다.
새로운 PII 패턴/정책을 본 모듈에서 추가하지 않는다 (18-1 범위 외).
"""
from __future__ import annotations

from dataclasses import dataclass

from .schemas import (
    REASON_INVALID_QUERY,
    REASON_PII_DETECTED,
)


@dataclass
class SafetyDecision:
    """safety gate 결과.

    ``allowed`` 가 False 이면 후속 retriever/LLM 호출은 차단되어야 한다.
    """
    allowed: bool
    reason_code: str = ""
    masked_question: str = ""
    pii_hits: int = 0


def check_query(question: str) -> SafetyDecision:
    """질문 단계 사전 검사 stub — 18-2 에서 본격 구현.

    18-1 시점에는 입력만 받고 ``allowed=True`` + masked_question 만 채워서
    반환한다. 실제 PII 마스킹/invalid_query 차단은 ``manual_qa.ask_manual_question``
    의 현행 동작이 그대로 처리한다 (18-1 회귀 0 보장).
    """
    if not (question or "").strip():
        return SafetyDecision(
            allowed=False,
            reason_code=REASON_INVALID_QUERY,
            masked_question="",
        )
    # 18-1: 사전 PII 차단은 도입하지 않는다 (현행 manual_qa 가 처리).
    # 인터페이스 형태만 둔다 — 18-2 에서 ``pii.scan`` wrapper 로 대체.
    _ = REASON_PII_DETECTED  # 미사용 경고 회피 (18-2 에서 사용)
    return SafetyDecision(allowed=True, reason_code="", masked_question=question)


__all__ = ["SafetyDecision", "check_query"]
