"""Safety Harness — 18-0 최소 안전 검증.

PII 보호, 할루시네이션 차단, 출처 없는 단정 차단.

상세 설계: ``docs/harnesses/safety_harness_plan.md``.
이번 세션 범위:
  - 입력 PII (전화/생년월일/RRN) → masked_question 마스킹 + provider prompt 미도달
  - LLM 응답 PII → answer 마스킹
  - LLM 응답 위험 단정 → blocked=true
  - 매뉴얼에 없는 기능 질문 → not_found 또는 blocked
"""
from __future__ import annotations

from app.services.ai import manual_qa as ai_manual_qa
from app.services.rag.search import reset_cache as _rag_reset_cache
from tests.harness.contract import assert_manual_ask_contract
from tests.harness.fake_provider import (
    FakeProvider,
    assert_no_external_call,
    assert_provider_received_no_pii,
)
from tests.harness.safety_harness import (
    DANGEROUS_RESPONSES,
    PII_PHONE_TEXTS,
    UNKNOWN_FEATURE_QUESTIONS,
    assert_no_pii_in_text,
    assert_pii_marker_present,
)


def test_safety_phone_pii_masked_in_question_and_not_in_prompt():
    """입력 전화번호 → ``masked_question`` 에 ``[PHONE]`` + provider prompt 미도달."""
    _rag_reset_cache()
    fake = FakeProvider()
    raw_question = "010-1234-5678 환자가 예약문자 작성을 어떻게 해야 하나요?"
    res = ai_manual_qa.ask_manual_question(
        None, raw_question, provider_override=fake,
    )
    assert_manual_ask_contract(res)
    masked = res["masked_question"]
    for p in PII_PHONE_TEXTS:
        assert p not in masked, masked
    assert_pii_marker_present(masked)
    assert_provider_received_no_pii(fake, *PII_PHONE_TEXTS)


def test_safety_phone_pii_in_llm_response_masked_in_answer():
    """LLM 응답에 환각 PII → ``answer`` 사후 마스킹."""
    _rag_reset_cache()
    fake = FakeProvider(
        return_text="예약문자는 예약 문자 탭에서 작성합니다. 문의 010-1234-5678 로 연락하세요."
    )
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성 방법", provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert res["not_found"] is False
    assert_no_pii_in_text(res["answer"], *PII_PHONE_TEXTS)
    assert_pii_marker_present(res["answer"])


def test_safety_dangerous_medical_claim_blocked():
    """LLM 응답에 의료 단정 표현 → blocked=true + 안내 문구로 대체."""
    _rag_reset_cache()
    fake = FakeProvider(return_text=DANGEROUS_RESPONSES[0])  # "이 환자는 확실히 효과가 있습니다."
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert res["blocked"] is True, res
    assert res["blocked_reason"], "blocked_reason must be non-empty when blocked"
    # 차단 시 안내 문구
    assert "검증 단계에서 차단" in res["answer"] or "관리자에게 확인" in res["answer"]


def test_safety_execution_claim_blocked():
    """LLM 응답이 실행 완료 오인 → blocked=true."""
    _rag_reset_cache()
    fake = FakeProvider(return_text=DANGEROUS_RESPONSES[1])  # "예약문자를 발송했습니다."
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert res["blocked"] is True, res


def test_safety_unknown_feature_question_safe_response():
    """매뉴얼에 없는 기능 질문 → not_found 또는 blocked. LLM 단정 응답 금지."""
    _rag_reset_cache()
    fake = FakeProvider(return_text="자동 보험청구 기능은 설정 → 자동화 메뉴에 있습니다.")
    res = ai_manual_qa.ask_manual_question(
        None, UNKNOWN_FEATURE_QUESTIONS[0], provider_override=fake,
    )
    assert_manual_ask_contract(res)
    # 매뉴얼에 없는 기능이면 not_found 가 우선이며, LLM 호출이 일어나지 않아야 한다.
    # (LOW_SCORE_THRESHOLD 미달 또는 sources 0건)
    assert res["not_found"] is True or res["blocked"] is True
    if res["not_found"] is True and not res["sources"]:
        assert_no_external_call(fake)


def test_safety_birth_pii_masked():
    """입력 생년월일 → masked_question 마스킹."""
    _rag_reset_cache()
    fake = FakeProvider()
    raw = "1980-01-01 환자 백업 어떻게 하나요?"
    res = ai_manual_qa.ask_manual_question(
        None, raw, provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert "1980-01-01" not in res["masked_question"]
    assert_pii_marker_present(res["masked_question"])
