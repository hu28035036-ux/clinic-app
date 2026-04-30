"""업무 매뉴얼 Q&A — knowledge/manuals/ 기반 RAG + LLM (단계 5 + 세션 09 보강).

정책:
  - 환자 개인정보는 입력·검색·LLM 전달에 모두 사용하지 않는다.
  - 사용자 질문에 PII 패턴이 섞여 들어와도 마스킹 후 사용.
  - 매뉴얼 검색 결과가 0개 또는 점수가 LOW_SCORE_THRESHOLD 미만이면 LLM 호출 없이
    "매뉴얼에서 답을 찾지 못했습니다." 반환 (세션 09 보강).
  - 매뉴얼에 없는 내용을 추측하지 말 것 — system 프롬프트로 명시.
  - LLM 응답에 환각 PII (전화번호 등) / 의료 단정 / 실행 완료 표현이 섞이면
    blocked 처리 (세션 09 보강).

검색 카테고리: "manuals" 만 사용 (sms_guides 등 다른 카테고리는 직원이 직접 보는
매뉴얼이 아니라 LLM 톤 가이드용이므로 매뉴얼 Q&A 답변 근거에서 제외).
"""
from __future__ import annotations
import re
from typing import Optional

from . import pii
from . import provider as ai_provider
from ..rag.search import search as _rag_search


_NOT_FOUND_ANSWER = "매뉴얼에서 답을 찾지 못했습니다."
_NOT_FOUND_PROMPT = "매뉴얼에서 답을 찾지 못했습니다. 관리자에게 확인해주세요."
_OUT_OF_SCOPE_ANSWER = "이 질문은 등록된 업무매뉴얼 범위를 벗어납니다. 관리자에게 확인해주세요."
_BLOCKED_ANSWER = "답변을 생성했지만 검증 단계에서 차단되었습니다. 관리자에게 확인해주세요."

# 한국어 RAG score 분포가 보통 1~3 이라 임계치는 보수적으로 2 (score==1 = 모호한 매칭).
# 결과 0개는 기존 동작대로 즉시 차단.
LOW_SCORE_THRESHOLD = 2

_MANUAL_SYSTEM_PROMPT = (
    "당신은 한국 도수치료 클리닉 직원의 업무 매뉴얼 어시스턴트입니다.\n"
    "아래 '매뉴얼 발췌' 안에 있는 내용에만 근거해서 한국어로 간결하게 답하세요.\n"
    "매뉴얼 발췌에 없는 내용은 추측하거나 만들어내지 말고 "
    "'매뉴얼에서 답을 찾지 못했습니다.' 라고만 답하세요.\n"
    "출처 문서에 없는 기능명, 버튼명, API endpoint, 설정값을 만들지 마세요.\n"
    "의료 진단/치료효과/완치 같은 의료 판단을 하지 마세요.\n"
    "AI 가 직접 문자 발송하거나 DB 를 수정할 수 없다는 점을 사실대로 알리세요.\n"
    "이 시스템 외부 주제(주식/날씨/일반상식 등)는 "
    "'업무 매뉴얼 범위를 벗어납니다' 로만 답하세요.\n"
    "환자 이름·전화번호·생년월일·차트번호·환자 메모는 절대 만들어내지 마세요.\n"
    "답변은 단계가 있으면 번호 목록으로 정리하고, 마지막에 사용한 매뉴얼 파일명을 한 줄로 표시하세요."
)


# ── 응답 검증 패턴 (세션 09) ──
# 의료 단정 표현 (블랙리스트 — 화이트리스트가 아님: 일반 사용에서 거의 안 나오는 단어만)
_RE_MEDICAL_CLAIM = re.compile(
    r"(완치|반드시\s*치료|확실히\s*효과|보험\s*적용\s*확정|진단됩니다|치료가\s*필요합니다)"
)

# 실행 완료 오인 표현 — AI 가 직접 실행했다고 거짓 진술하면 위험
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


def _build_user_prompt(question: str, sources: list[dict]) -> str:
    """LLM 에 보낼 user 프롬프트 — 매뉴얼 발췌 + 질문."""
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


def _format_sources(results: list[dict]) -> list[dict]:
    """라우터 응답용 출처 리스트 — UI 표시에 필요한 필드만."""
    out = []
    for r in results:
        out.append({
            "title": r.get("title") or r.get("name") or r.get("path", ""),
            "path": r.get("path", ""),
            "snippet": r.get("snippet", ""),
        })
    return out


def validate_answer(text: str, *, has_sources: bool) -> dict:
    """LLM 응답 후 검증 — 위험 표현 / PII / 출처 없는 단정 탐지.

    반환:
      {
        "blocked": bool,
        "reason": str,    # 차단/경고 사유 (영문 short)
        "cleaned": str,   # PII 마스킹 + 차단 시 안내문구로 대체된 답변
        "guard_hits": int, # 적중 카운트 (PII + 위험 표현)
      }
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

    # 4) 출처 없는데 단정 표현 (확신·반드시·무조건)
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


def manual_search(question: str) -> dict:
    """LLM 호출 없는 RAG 검색 (디버깅·사전검색용).

    응답:
      {"sources": [...], "masked_question": str, "top_score": int}
    """
    scan = pii.scan(question or "")
    cleaned = scan.cleaned
    results = _rag_search(cleaned, category="manuals", limit=5)
    top_score = int(results[0].get("score", 0)) if results else 0
    return {
        "sources": _format_sources(results),
        "masked_question": cleaned,
        "top_score": top_score,
    }


def ask_manual_question(
    db,
    question: str,
    *,
    provider_override: Optional[ai_provider.AiProvider] = None,
) -> dict:
    """업무 매뉴얼 Q&A 진입점.

    인자:
      db                : SQLAlchemy 세션 — 환자 DB 접근 금지 정책상 의도적으로 미사용.
                          라우터 시그니처/향후 확장 위해 유지.
      question          : 직원 질문 (자유 한국어)
      provider_override : 라우터에서 초기화한 provider 인스턴스. 테스트에서 FakeProvider 주입.

    반환:
      {
        "answer": str,
        "sources": [{"title", "path", "snippet"}, ...],
        "confidence": "high"|"low"|"unknown",
        "not_found": bool,
        "blocked": bool,            # 세션 09: 응답 검증에서 차단됐는지
        "blocked_reason": str,      # 세션 09: 차단/경고 사유 (영문 short)
        "guard_hits": int,          # 세션 09: PII + 위험표현 적중 합계
        "top_score": int,           # 세션 09: 최상위 RAG 점수 (관찰용)
        "masked_question": str
      }
    """
    _ = db  # 의도적으로 사용하지 않음 (환자 DB 접근 금지)

    # 1) 입력 PII 마스킹
    scan = pii.scan(question or "")
    cleaned = scan.cleaned
    pii_hits = sum(len(v) for v in scan.found.values()) if scan.found else 0

    # 2) RAG 검색 — manuals 카테고리만
    results = _rag_search(cleaned, category="manuals", limit=5)
    top_score = int(results[0].get("score", 0)) if results else 0

    # 3) 결과 없음 → LLM 호출 없이 즉시 unknown 반환
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

    # 4) 점수 낮음 → LLM 호출 생략 (세션 09 신규)
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

    # 6) 프롬프트 구성 + LLM 호출
    user_prompt = _build_user_prompt(cleaned, results)
    ai_result = provider_override.generate(user_prompt, system=_MANUAL_SYSTEM_PROMPT)
    answer_text = (ai_result.text or "").strip()

    # 7) 응답 검증 (PII 마스킹 + 위험 표현 + 실행 오인)
    validation = validate_answer(answer_text, has_sources=bool(results))
    answer_text = validation["cleaned"]
    blocked = validation["blocked"]
    blocked_reason = validation["reason"]
    guard_hits = pii_hits + validation["guard_hits"]

    # 8) confidence — 최상위 score 기준
    confidence = _confidence_for(top_score)

    # 9) LLM 이 매뉴얼에 없는 질문이라고 답하면 not_found=True 로 일관 처리
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
