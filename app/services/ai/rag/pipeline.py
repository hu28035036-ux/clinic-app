"""RAG pipeline — 18-2 manual ask/search 진입점.

흐름 (``run_manual_ask``):
  1. PII mask (입력 question)
  2. keyword retrieve (manuals 카테고리)
  3. score gate
       - sources 0   → provider 호출 0, ``not_found=True``
       - top_score < ``LOW_SCORE_THRESHOLD`` → provider 호출 0, ``not_found=True``
       - provider 부재 → provider 호출 0, ``not_found=True``
  4. user_prompt 조립 + provider.generate (system v1)
  5. answer 검증 (PII / medical claim / execution claim / unsupported)
  6. confidence 계산 + ``not_found_in_text`` 판정
  7. v1.3.3 응답 9키 dict 반환

``run_manual_search`` 는 1+2 만. LLM 호출 없음.

18-1 stub 인 ``run_manual_qa`` 는 NotImplementedError 그대로 유지
(``test_pipeline_run_manual_qa_not_implemented`` 단언 충족). 18-2 의 매뉴얼
ask 정식 진입점은 ``run_manual_ask``.

의존 규칙 (18-1 ``rag/__init__.py`` 가이드):
  - ``app.services.ai.{provider, pii}`` 만 직접 import.
  - 기존 ``app.services.ai.manual_qa`` 는 import 하지 않는다 (역의존 회피).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from .. import pii
from .. import provider as ai_provider
from .prompts import get_prompt
from .retriever import keyword_retrieve
from .schemas import Answer  # noqa: F401  # 18-1 stub 시그니처 보존

# ── v1.3.3 정책 상수 (manual_qa.py:24-31 와 1:1) ──
_NOT_FOUND_ANSWER = "매뉴얼에서 답을 찾지 못했습니다."
_NOT_FOUND_PROMPT = "매뉴얼에서 답을 찾지 못했습니다. 관리자에게 확인해주세요."
_OUT_OF_SCOPE_ANSWER = "이 질문은 등록된 업무매뉴얼 범위를 벗어납니다. 관리자에게 확인해주세요."
_BLOCKED_ANSWER = "답변을 생성했지만 검증 단계에서 차단되었습니다. 관리자에게 확인해주세요."

LOW_SCORE_THRESHOLD = 2

_RE_MEDICAL_CLAIM = re.compile(
    r"(완치|반드시\s*치료|확실히\s*효과|보험\s*적용\s*확정|진단됩니다|치료가\s*필요합니다)"
)
_RE_EXECUTION_CLAIM = re.compile(
    r"(문자\s*[를을]?\s*발송했|예약\s*[을를]?\s*변경했|"
    r"설정\s*[을를]?\s*변경했|발송\s*완료\s*했|예약\s*확정\s*했|"
    r"DB\s*[를을]?\s*수정했|환자\s*정보\s*[를을]?\s*변경했)"
)


def _confidence_for(score: int) -> str:
    if score >= 5:
        return "high"
    if score >= 1:
        return "low"
    return "unknown"


def _format_sources(results: list[dict]) -> list[dict]:
    """라우터 응답용 출처 리스트 — UI 표시 필수 3개 키만."""
    out = []
    for r in results:
        out.append(
            {
                "title": r.get("title") or r.get("name") or r.get("path", ""),
                "path": r.get("path", ""),
                "snippet": r.get("snippet", ""),
            }
        )
    return out


def _build_user_prompt(question: str, sources: list[dict]) -> str:
    """LLM 에 보낼 user 프롬프트 — 매뉴얼 발췌 + 질문 (v1.3.3 동등)."""
    chunks = []
    for s in sources:
        title = s.get("title") or s.get("name") or s.get("path", "")
        path = s.get("path", "")
        snippet = s.get("snippet", "")
        chunks.append(f"[매뉴얼: {title} ({path})]\n{snippet}")
    excerpts = "\n\n".join(chunks) if chunks else "(매뉴얼 발췌 없음)"
    return (
        "다음은 업무 매뉴얼 발췌입니다:\n\n"
        f"{excerpts}\n\n"
        f"질문: {question}\n\n"
        "위 발췌에 근거해서 답하세요. 매뉴얼에 없는 내용이면 "
        "'매뉴얼에서 답을 찾지 못했습니다.' 라고만 답하세요."
    )


def validate_answer(text: str, *, has_sources: bool) -> dict:
    """LLM 응답 검증 — PII 마스킹 + 위험 표현 + 출처 없는 단정 차단.

    v1.3.3 ``manual_qa.validate_answer`` (manual_qa.py:100-152) 와 동작 1:1.

    반환:
      ``{"blocked": bool, "reason": str, "cleaned": str, "guard_hits": int}``
    """
    reason = ""
    blocked = False
    hits = 0
    cleaned = text or ""

    # 1) PII 마스킹
    try:
        scan = pii.scan(cleaned)
        if scan.has_blocking:
            cleaned = scan.cleaned
            hits += sum(len(v) for v in scan.found.values())
    except Exception:
        pass

    # 2) 의료 단정 표현
    if _RE_MEDICAL_CLAIM.search(cleaned):
        blocked = True
        reason = "unsafe medical advice"
        hits += 1

    # 3) 실행 완료 오인 표현
    if not blocked and _RE_EXECUTION_CLAIM.search(cleaned):
        blocked = True
        reason = "execution claim blocked"
        hits += 1

    # 4) 출처 없는데 단정 표현
    if not blocked and not has_sources:
        if re.search(r"(반드시|무조건|확실히|항상)", cleaned):
            blocked = True
            reason = "unsupported claim"
            hits += 1

    if blocked:
        cleaned = _BLOCKED_ANSWER

    return {
        "blocked": blocked,
        "reason": reason,
        "cleaned": cleaned,
        "guard_hits": hits,
    }


def _system_prompt() -> str:
    return get_prompt("manual_qa.system", "v1")


# ──────────────────────── 18-2 정식 진입점 ────────────────────────


def run_manual_search(question: str) -> dict:
    """``/api/ai/manual/search`` 진입점 — LLM 호출 없음.

    응답:
      ``{"sources": [...], "masked_question": str, "top_score": int}``.
    """
    scan = pii.scan(question or "")
    cleaned = scan.cleaned
    results = keyword_retrieve(cleaned, category="manuals", limit=5)
    top_score = int(results[0].get("score", 0)) if results else 0
    return {
        "sources": _format_sources(results),
        "masked_question": cleaned,
        "top_score": top_score,
    }


def run_manual_ask(
    db: Any,
    question: str,
    *,
    provider_override: Optional[ai_provider.AiProvider] = None,
) -> dict:
    """``/api/ai/manual/ask`` 진입점 — v1.3.3 응답 9키 동일.

    Local-first 게이트:
      - sources 0 / top_score < LOW_SCORE_THRESHOLD / provider 부재 → provider 호출 0
    """
    _ = db  # 환자 DB 접근 금지 정책 — 의도적으로 미사용

    # 1) 입력 PII 마스킹
    scan = pii.scan(question or "")
    cleaned = scan.cleaned
    pii_hits = sum(len(v) for v in scan.found.values()) if scan.found else 0

    # 2) keyword retrieve (manuals only)
    results = keyword_retrieve(cleaned, category="manuals", limit=5)
    top_score = int(results[0].get("score", 0)) if results else 0

    # 3) 결과 없음 → LLM 호출 없이 즉시 반환
    if not results:
        return {
            "answer": _NOT_FOUND_PROMPT,
            "sources": [],
            "confidence": "unknown",
            "not_found": True,
            "blocked": False,
            "blocked_reason": "no rag hit",
            "guard_hits": pii_hits,
            "top_score": 0,
            "masked_question": cleaned,
        }

    # 4) 점수 낮음 → LLM 호출 생략
    if top_score < LOW_SCORE_THRESHOLD:
        return {
            "answer": _NOT_FOUND_PROMPT,
            "sources": _format_sources(results),
            "confidence": "unknown",
            "not_found": True,
            "blocked": False,
            "blocked_reason": "low rag confidence",
            "guard_hits": pii_hits,
            "top_score": top_score,
            "masked_question": cleaned,
        }

    # 5) provider 없음 → LLM 호출 없이 안전 반환
    if provider_override is None:
        return {
            "answer": _NOT_FOUND_ANSWER,
            "sources": _format_sources(results),
            "confidence": "unknown",
            "not_found": True,
            "blocked": False,
            "blocked_reason": "no provider",
            "guard_hits": pii_hits,
            "top_score": top_score,
            "masked_question": cleaned,
        }

    # 6) 프롬프트 조립 + LLM 호출
    user_prompt = _build_user_prompt(cleaned, results)
    ai_result = provider_override.generate(user_prompt, system=_system_prompt())
    answer_text = (ai_result.text or "").strip()

    # 7) 응답 검증
    validation = validate_answer(answer_text, has_sources=bool(results))
    answer_text = validation["cleaned"]
    blocked = validation["blocked"]
    blocked_reason = validation["reason"]
    guard_hits = pii_hits + validation["guard_hits"]

    # 8) confidence
    confidence = _confidence_for(top_score)

    # 9) LLM 이 매뉴얼에 없는 질문이라고 답하면 not_found=True 로 통일
    not_found_in_text = _NOT_FOUND_ANSWER in answer_text and top_score < 5

    return {
        "answer": answer_text or _NOT_FOUND_ANSWER,
        "sources": _format_sources(results),
        "confidence": "unknown" if (blocked or not_found_in_text) else confidence,
        "not_found": bool(not_found_in_text),
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "guard_hits": guard_hits,
        "top_score": top_score,
        "masked_question": cleaned,
    }


# ──────────────────────── 18-1 stub 보존 (회귀 단언 충족) ────────────────────────


def run_manual_qa(
    db: Any,
    question: str,
    *,
    provider_override: Optional[Any] = None,
    embedding_provider: Optional[Any] = None,
    mode: Optional[str] = None,
) -> Answer:
    """18-1 stub — 18-5 chunk + hybrid 통합 시점에 정식 구현 예정.

    18-2 시점의 매뉴얼 ask 정식 진입점은 ``run_manual_ask`` 다.
    ``test_pipeline_run_manual_qa_not_implemented`` 단언 충족을 위해 본 함수는
    NotImplementedError 를 그대로 유지한다.
    """
    _ = (db, question, provider_override, embedding_provider, mode)
    raise NotImplementedError(
        "rag.pipeline.run_manual_qa 는 18-5 chunk + hybrid 통합 시점에 구현됩니다. "
        "현재 매뉴얼 ask 진입점은 run_manual_ask() 입니다."
    )


__all__ = [
    "run_manual_search",
    "run_manual_ask",
    "run_manual_qa",
    "validate_answer",
    "LOW_SCORE_THRESHOLD",
]
