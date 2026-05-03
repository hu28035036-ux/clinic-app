"""18-1 Safety Harness — 신규 골격 도입 후 안전 정책 회귀 0.

PII 마스킹 / 위험 단정 차단 / 출처 없는 단정 차단 / API key 미노출이
v1.3.3과 동일하게 동작하는지 + 신규 ``rag.safety`` stub 인터페이스 검증.

상세: ``docs/harnesses/safety_harness_plan.md``.
"""
from __future__ import annotations

from app.services.ai import manual_qa as ai_manual_qa
from app.services.ai.rag import safety as rag_safety
from app.services.ai.rag import schemas as rag_schemas
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
    assert_no_api_key_in_text,
    assert_no_pii_in_text,
    assert_pii_marker_present,
)

# ────────── 1. PII 마스킹 회귀 0 ──────────


def test_safety_phone_pii_in_question_still_masked():
    """전화번호 입력 → ``masked_question`` 마스킹 + provider prompt 미도달."""
    _rag_reset_cache()
    fake = FakeProvider()
    raw = "010-1234-5678 환자가 예약문자 작성을 어떻게 해야 하나요?"
    res = ai_manual_qa.ask_manual_question(None, raw, provider_override=fake)
    assert_manual_ask_contract(res)
    masked = res["masked_question"]
    for p in PII_PHONE_TEXTS:
        assert p not in masked
    assert_pii_marker_present(masked)
    assert_provider_received_no_pii(fake, *PII_PHONE_TEXTS)


def test_safety_phone_pii_in_llm_response_still_masked():
    """LLM 환각 응답에 전화번호 → ``answer`` 사후 마스킹 (회귀 0)."""
    _rag_reset_cache()
    fake = FakeProvider(
        return_text="예약문자는 예약 문자 탭에서 작성합니다. 문의 010-1234-5678 로 연락하세요."
    )
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성 방법", provider_override=fake,
    )
    assert_no_pii_in_text(res["answer"], *PII_PHONE_TEXTS)
    assert_pii_marker_present(res["answer"])


def test_safety_birth_pii_in_question_still_masked():
    """생년월일 입력 → ``masked_question`` 마스킹."""
    _rag_reset_cache()
    fake = FakeProvider()
    res = ai_manual_qa.ask_manual_question(
        None, "1980-01-01 환자 백업 어떻게 하나요?", provider_override=fake,
    )
    assert "1980-01-01" not in res["masked_question"]
    assert_pii_marker_present(res["masked_question"])


# ────────── 2. 위험 단정 차단 회귀 0 ──────────


def test_safety_medical_claim_still_blocked():
    """LLM 의료 단정 응답 → ``blocked=true`` (회귀 0)."""
    _rag_reset_cache()
    fake = FakeProvider(return_text=DANGEROUS_RESPONSES[0])  # "확실히 효과"
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert res["blocked"] is True
    assert res["blocked_reason"]


def test_safety_execution_claim_still_blocked():
    """LLM 실행 완료 오인 응답 → ``blocked=true`` (회귀 0)."""
    _rag_reset_cache()
    fake = FakeProvider(return_text=DANGEROUS_RESPONSES[1])
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert res["blocked"] is True


# ────────── 3. 없는 기능 질문 안전 응답 회귀 0 ──────────


def test_safety_unknown_feature_safe_response():
    """매뉴얼에 없는 기능 질문 → ``not_found=true`` 또는 ``blocked=true``."""
    _rag_reset_cache()
    fake = FakeProvider(return_text="자동 보험청구 기능은 설정 → 자동화 메뉴에 있습니다.")
    res = ai_manual_qa.ask_manual_question(
        None, UNKNOWN_FEATURE_QUESTIONS[0], provider_override=fake,
    )
    assert res["not_found"] is True or res["blocked"] is True
    if res["not_found"] is True and not res["sources"]:
        assert_no_external_call(fake)


# ────────── 4. API key 미노출 회귀 0 ──────────


def test_safety_no_api_key_in_503_response(client, ai_disabled_setting):
    """503 응답 본문에 어떤 API key 값도 부재."""
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    assert resp.status_code == 503
    assert_no_api_key_in_text(resp.text, "test-fake-key", "sk-")


# ────────── 5. 신규 rag.safety stub 검증 (18-1 신규) ──────────


def test_safety_check_query_invalid_query_for_empty():
    """빈 질문 → ``rag.safety.check_query`` 가 ``invalid_query`` 발급."""
    d = rag_safety.check_query("")
    assert d.allowed is False
    assert d.reason_code == rag_schemas.REASON_INVALID_QUERY


def test_safety_check_query_normal_passes():
    """정상 질문은 18-1 stub 에서 그대로 통과 (실제 PII 차단은 manual_qa 처리)."""
    d = rag_safety.check_query("예약문자 작성")
    assert d.allowed is True
    assert d.reason_code == ""


def test_safety_decision_dataclass_fields():
    """``SafetyDecision`` 의 필수 필드 보존."""
    d = rag_safety.SafetyDecision(allowed=True)
    assert hasattr(d, "allowed")
    assert hasattr(d, "reason_code")
    assert hasattr(d, "masked_question")
    assert hasattr(d, "pii_hits")


def test_safety_pii_reason_code_constant():
    """``REASON_PII_DETECTED`` 가 ``pii_detected`` 문자열로 정의."""
    assert rag_schemas.REASON_PII_DETECTED == "pii_detected"


def test_safety_unsupported_question_is_single_standard():
    """``unsupported_question`` 단일 표준 — 다른 별칭(``unsupported_claim``) 부재."""
    assert rag_schemas.REASON_UNSUPPORTED_QUESTION == "unsupported_question"
    assert "unsupported_claim" not in rag_schemas.ALL_REASON_CODES
