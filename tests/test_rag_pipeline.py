"""RAG Harness — 18-0 최소 RAG 파이프라인 검증.

매뉴얼 RAG 검색·답변 흐름과 LLM 호출 게이트.

상세 설계: ``docs/harnesses/rag_harness_plan.md``.
이번 세션 범위:
  - 매뉴얼에 있는 질문 → sources≥1 + 회귀 모드 1회 LLM 호출
  - 매뉴얼에 없는 질문 → not_found=true + LLM 호출 0
  - manual_search 단독 (LLM 미사용)
  - 응답 9개 키 계약 단언
"""
from __future__ import annotations

from app.services.ai import manual_qa as ai_manual_qa
from app.services.rag.search import reset_cache as _rag_reset_cache
from tests.harness.contract import (
    assert_manual_ask_contract,
    assert_manual_search_contract,
)
from tests.harness.fake_provider import (
    FakeProvider,
    assert_no_external_call,
    call_count,
)


def test_rag_known_question_yields_sources_and_one_llm_call():
    """매뉴얼 매칭 질문 → sources≥1 + LLM 1회 (회귀 모드 A)."""
    _rag_reset_cache()
    fake = FakeProvider(
        return_text="예약문자는 예약 문자 탭에서 작성합니다.\n참고: sms_compose.md"
    )
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert res["not_found"] is False, res
    assert len(res["sources"]) >= 1
    assert call_count(fake) == 1, f"expected 1 LLM call, got {call_count(fake)}"


def test_rag_unknown_question_no_llm_call():
    """매뉴얼에 없는 질문 → not_found=true + LLM 호출 0 (모든 모드 공통)."""
    _rag_reset_cache()
    fake = FakeProvider(return_text="이 응답은 호출되지 않아야 함")
    res = ai_manual_qa.ask_manual_question(
        None, "오늘 점심 메뉴 추천해줘 짜장면 짬뽕", provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert res["not_found"] is True
    assert res["sources"] == []
    assert res["confidence"] == "unknown"
    assert "매뉴얼에서 답을 찾지 못했습니다." in res["answer"]
    assert_no_external_call(fake)


def test_rag_no_provider_returns_not_found():
    """provider=None → LLM 호출 없이 안전하게 not_found=true."""
    _rag_reset_cache()
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=None,
    )
    assert_manual_ask_contract(res)
    assert res["not_found"] is True


def test_manual_search_only_returns_sources_no_llm():
    """manual_search 는 keyword RAG 만 — LLM 미사용. 응답 3개 키 계약."""
    _rag_reset_cache()
    res = ai_manual_qa.manual_search("백업은 어디서 해?")
    assert_manual_search_contract(res)
    assert len(res["sources"]) >= 1
    assert "backup" in (res["sources"][0].get("path") or "")


def test_manual_search_unknown_returns_empty_sources():
    """매칭 없는 질문 → 200 + sources=[] + top_score=0."""
    _rag_reset_cache()
    res = ai_manual_qa.manual_search("주식 추천해줘 종목 시세")
    assert_manual_search_contract(res)
    assert res["sources"] == []
    assert res["top_score"] == 0
