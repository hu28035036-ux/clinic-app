"""세션 09 검증 — manual_qa 할루시네이션 방어.

검증:
  ① 결과 없음 → LLM 미호출, not_found, blocked_reason="no rag hit"
  ② 낮은 score (< 2) → LLM 미호출, blocked_reason="low rag confidence"
  ③ 의료 단정 ("진단됩니다") → blocked
  ④ 실행 완료 ("문자 발송했습니다") → blocked
  ⑤ 응답 PII 환각 (전화번호) → 마스킹 + guard_hits 증가
  ⑥ validate_answer 단위 검증

실행:
    venv/Scripts/python.exe -m pytest tests/test_ai_hallucination.py -v
"""
from __future__ import annotations

from app.services.ai import manual_qa as ai_manual_qa
from app.services.ai import provider as ai_provider
from app.services.rag.search import reset_cache as _rag_reset_cache


class FakeProvider(ai_provider.AiProvider):
    name = "fake"

    def __init__(self, return_text=""):
        super().__init__(model="fake-1", api_key="fake-key")
        self.return_text = return_text
        self.calls = []

    def is_ready(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "") -> ai_provider.AiResult:
        self.calls.append({"prompt": prompt, "system": system})
        return ai_provider.AiResult(text=self.return_text)


# ─────────── ① 결과 0 ───────────

def test_no_rag_hit_skips_llm():
    _rag_reset_cache()
    fake = FakeProvider(return_text="이 응답은 호출되면 안 됨")
    res = ai_manual_qa.ask_manual_question(
        None, "오늘 주식 시황 알려줘 짜장면 짬뽕 메뉴 추천", provider_override=fake,
    )
    assert res["not_found"] is True
    assert res["blocked_reason"] == "no rag hit"
    assert len(fake.calls) == 0
    assert res["confidence"] == "unknown"


# ─────────── ② 낮은 score (< 2) ───────────

def test_low_score_skips_llm():
    _rag_reset_cache()
    fake = FakeProvider(return_text="이 응답은 호출되면 안 됨")
    # 한국어 질문 score=1 짜리 — "문자나라 -999 오류는 뭐야?" 측정 결과 score=1
    res = ai_manual_qa.ask_manual_question(
        None, "문자나라 -999 오류는 뭐야?", provider_override=fake,
    )
    assert res["not_found"] is True
    assert res["blocked_reason"] == "low rag confidence"
    assert len(fake.calls) == 0
    assert res["top_score"] < 2


# ─────────── ③ 의료 단정 차단 ───────────

def test_medical_claim_blocked():
    _rag_reset_cache()
    fake = FakeProvider(return_text="이 환자는 도수치료로 완치됩니다.")
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    # LLM 은 호출되지만 응답 검증에서 차단
    assert len(fake.calls) == 1
    assert res["blocked"] is True
    assert res["blocked_reason"] == "unsafe medical advice"
    assert "완치" not in res["answer"]
    assert "차단" in res["answer"]


# ─────────── ④ 실행 완료 표현 차단 ───────────

def test_execution_claim_blocked():
    _rag_reset_cache()
    fake = FakeProvider(return_text="문자를 발송했습니다. 추가 안내 끝.")
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert len(fake.calls) == 1
    assert res["blocked"] is True
    assert res["blocked_reason"] == "execution claim blocked"
    assert "발송했" not in res["answer"]


# ─────────── ⑤ 응답 PII 환각 ───────────

def test_response_pii_masked_and_counted():
    _rag_reset_cache()
    fake = FakeProvider(
        return_text="예약문자 작성 안내. 문의 010-1234-5678 로 연락하세요."
    )
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert "010-1234-5678" not in res["answer"]
    assert "[PHONE]" in res["answer"]
    assert res["guard_hits"] >= 1
    # 단정 표현/의료 단정 없으므로 blocked 는 아님
    assert res["blocked"] is False


# ─────────── ⑥ validate_answer 단위 ───────────

def test_validate_answer_unit():
    v = ai_manual_qa.validate_answer("이 환자는 완치됩니다.", has_sources=True)
    assert v["blocked"] and v["reason"] == "unsafe medical advice"

    v = ai_manual_qa.validate_answer("문자를 발송했습니다.", has_sources=True)
    assert v["blocked"] and v["reason"] == "execution claim blocked"

    v = ai_manual_qa.validate_answer("정상 답변입니다.", has_sources=True)
    assert not v["blocked"]

    v = ai_manual_qa.validate_answer(
        "반드시 이렇게 해야 합니다.", has_sources=False,
    )
    assert v["blocked"] and v["reason"] == "unsupported claim"

    v = ai_manual_qa.validate_answer(
        "전화 010-1234-5678 로 연락하세요.", has_sources=True,
    )
    # PII 마스킹 + guard_hits 증가, 차단은 아님 (단정/실행 표현 없음)
    assert "[PHONE]" in v["cleaned"]
    assert v["guard_hits"] >= 1


# ─────────── ⑦ 결과 0 → manual_search 도 안전 ───────────

def test_manual_search_no_results():
    _rag_reset_cache()
    # 영문 무의미 토큰만 — 한글 매뉴얼의 어떤 토큰과도 매칭되지 않음
    res = ai_manual_qa.manual_search("qwertyabc asdfzxcv lmnopqr")
    assert res["sources"] == []
    assert res["top_score"] == 0
