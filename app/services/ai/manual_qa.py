"""업무 매뉴얼 Q&A — wrapper (18-2 분리 후).

18-2 분리:
  - 검색/답변 조립 본체는 ``app.services.ai.rag.pipeline`` 으로 이전.
  - 본 모듈은 v1.3.3 import 경로/시그니처/공개 상수/응답 9개 키를 100% 보존하는
    얇은 wrapper.

기존 사용처:
  - 라우터 ``app/routers/ai.py:38`` 의 ``from ..services.ai import manual_qa
    as ai_manual_qa`` 그대로 동작.
  - 테스트 (``tests/test_ai_manual_rag_*``) 의 ``ai_manual_qa.LOW_SCORE_THRESHOLD``
    / ``ai_manual_qa._MANUAL_SYSTEM_PROMPT`` 참조 그대로 동작.

정책 (분리 전후 동등):
  - 환자 개인정보는 입력·검색·LLM 전달 모두에 사용하지 않는다.
  - 사용자 질문에 PII 패턴이 섞여 들어와도 마스킹 후 사용.
  - 매뉴얼 검색 결과가 0개 또는 점수가 ``LOW_SCORE_THRESHOLD`` 미만이면 LLM
    호출 없이 ``"매뉴얼에서 답을 찾지 못했습니다."`` 반환.
  - LLM 응답에 환각 PII / 의료 단정 / 실행 완료 표현이 섞이면 blocked.

검색 카테고리: ``"manuals"`` 만 사용.
"""
from __future__ import annotations

from typing import Optional

from . import provider as ai_provider
from .rag import pipeline as _pipeline
from .rag.prompts import get_prompt as _get_prompt

# ── v1.3.3 공개 상수 (기존 import 호환) ──
LOW_SCORE_THRESHOLD = _pipeline.LOW_SCORE_THRESHOLD

# ``rag.prompts`` 가 v1 시스템 프롬프트의 단일 진실원천. 본 wrapper 는 같은
# 문자열을 재노출하여 ``ai_manual_qa._MANUAL_SYSTEM_PROMPT`` 참조 호환을 유지.
_MANUAL_SYSTEM_PROMPT = _get_prompt("manual_qa.system", "v1")


def manual_search(question: str) -> dict:
    """LLM 호출 없는 RAG 검색 — v1.3.3 응답 그대로.

    응답: ``{"sources": [...], "masked_question": str, "top_score": int}``.
    """
    return _pipeline.run_manual_search(question)


def ask_manual_question(
    db,
    question: str,
    *,
    provider_override: Optional[ai_provider.AiProvider] = None,
) -> dict:
    """업무 매뉴얼 Q&A 진입점 — v1.3.3 응답 9개 키 그대로.

    인자:
      db                : SQLAlchemy 세션 (의도적 미사용 — 환자 DB 접근 금지)
      question          : 직원 질문
      provider_override : 라우터/테스트에서 주입하는 provider 인스턴스
    """
    return _pipeline.run_manual_ask(
        db,
        question,
        provider_override=provider_override,
    )


def validate_answer(text: str, *, has_sources: bool) -> dict:
    """LLM 응답 검증 wrapper — 기존 import 호환 (PII 마스킹 + 위험 표현 차단)."""
    return _pipeline.validate_answer(text, has_sources=has_sources)


__all__ = [
    "ask_manual_question",
    "manual_search",
    "validate_answer",
    "LOW_SCORE_THRESHOLD",
    "_MANUAL_SYSTEM_PROMPT",
]
