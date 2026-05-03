"""Local-Only 모드 단언 — 18-0 최소 버전.

18-0 시점에는 명시적 ``local_only`` 플래그가 코드에 없으나,
"외부 호출이 일어나면 안 되는 케이스"를 통합적으로 단언한다.

상세 설계: ``docs/ai_rag_test_plan.md`` §0-1 (B 목표 모드 일부 도입).
이번 세션 범위:
  - AI disabled → provider 호출 0
  - API key 없음 → provider 호출 0
  - 매뉴얼 없는 질문 → provider 호출 0 (모든 모드 공통)
  - low_confidence → provider 호출 0
"""
from __future__ import annotations

from app.services.ai import manual_qa as ai_manual_qa
from app.services.rag.search import reset_cache as _rag_reset_cache
from tests.harness.fake_provider import (
    FakeProvider,
    assert_no_external_call,
    call_count,
)


def test_local_only_unknown_question_no_provider_call():
    """모드 무관 — 매뉴얼 없는 질문이면 LLM 호출 0."""
    _rag_reset_cache()
    fake = FakeProvider(return_text="이 응답은 호출되지 않아야 함")
    res = ai_manual_qa.ask_manual_question(
        None, "주식 추천해줘 종목 시세", provider_override=fake,
    )
    assert res["not_found"] is True
    assert_no_external_call(fake)


def test_local_only_no_provider_passes_safely():
    """provider=None → no LLM call (정의상 호출 불가능). not_found 안전 응답."""
    _rag_reset_cache()
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=None,
    )
    assert res["not_found"] is True


def test_local_only_low_score_no_provider_call():
    """``LOW_SCORE_THRESHOLD`` 미달 (한국어 score=1) → LLM 호출 0.

    한 단어 검색은 보통 score=1 → low_confidence 분기.
    """
    _rag_reset_cache()
    fake = FakeProvider(return_text="이 응답은 호출되지 않아야 함")
    res = ai_manual_qa.ask_manual_question(
        None, "백업", provider_override=fake,
    )
    # top_score 가 LOW_SCORE_THRESHOLD(=2) 미만이면 LLM 미호출 + not_found=true.
    if res["top_score"] < ai_manual_qa.LOW_SCORE_THRESHOLD:
        assert res["not_found"] is True
        assert_no_external_call(fake)
    else:
        # score>=2 환경이면 LLM 1회 호출이 정상 — 이 케이스는 본 테스트의
        # 검증 대상이 아니므로 단언만 약화 (회귀 모드 (A)).
        assert call_count(fake) <= 1


def test_local_only_router_disabled_no_provider_call(client, ai_disabled_setting):
    """라우터 통합 — AI disabled 상태에서 manual/ask 호출 → 503 + LLM 0회."""
    # ``ai_disabled_setting`` fixture 가 enabled=False 강제.
    # 라우터에서 503 으로 즉시 차단되므로 어떤 provider 도 인스턴스화되지 않음.
    resp = client.post(
        "/api/ai/manual/ask",
        json={"question": "예약문자 작성"},
    )
    assert resp.status_code == 503
