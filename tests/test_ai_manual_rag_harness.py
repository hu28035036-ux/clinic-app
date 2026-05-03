"""18-1 RAG Harness — 신규 RAG 골격 검증 + 기존 동작 회귀 0.

신규 ``rag/`` 패키지의 schemas/safety/prompts 가 v1.3.3 응답 키 / 시스템 프롬프트
와 정합되는지, 그리고 기존 ``manual_qa.ask_manual_question`` 흐름이 그대로
동작하는지 검증.

상세: ``docs/harnesses/rag_harness_plan.md``.
"""
from __future__ import annotations

from app.services.ai import manual_qa as ai_manual_qa
from app.services.ai.rag import (
    pipeline as rag_pipeline,
)
from app.services.ai.rag import (
    prompts as rag_prompts,
)
from app.services.ai.rag import (
    retriever as rag_retriever,
)
from app.services.ai.rag import (
    safety as rag_safety,
)
from app.services.ai.rag import (
    schemas as rag_schemas,
)
from app.services.rag.search import reset_cache as _rag_reset_cache
from tests.harness.contract import assert_manual_ask_contract
from tests.harness.fake_provider import (
    FakeProvider,
    assert_no_external_call,
    call_count,
)

# ────────── 1. schemas — v1.3.3 응답 키 정합 ──────────


def test_schemas_source_keys_match_v1_3_3():
    """``Source`` 의 dataclass 필드가 v1.3.3 응답 ``sources[]`` 키와 1:1."""
    fields = rag_schemas.Source.__dataclass_fields__
    assert set(fields.keys()) >= {"title", "path", "snippet"}


def test_schemas_answer_required_9_keys_match_v1_3_3():
    """``Answer`` 의 필수 9개 필드가 v1.3.3 manual/ask 응답 키와 1:1."""
    fields = rag_schemas.Answer.__dataclass_fields__
    required_9 = {
        "answer", "sources", "confidence", "not_found",
        "blocked", "blocked_reason", "guard_hits",
        "top_score", "masked_question",
    }
    assert required_9.issubset(set(fields.keys()))


def test_schemas_optional_4_keys_present():
    """``Answer`` 에 신규 optional 4개 필드 정의 — 18-3 이후 채워질 자리.

    ``embedding_called`` 는 18-5 vector/embedding 도입 시점에 다시 추가될 예정.
    """
    fields = rag_schemas.Answer.__dataclass_fields__
    optional_4 = {
        "reason_code", "llm_called",
        "ai_mode", "prompt_version",
    }
    assert optional_4.issubset(set(fields.keys()))


def test_schemas_reason_codes_29_defined():
    """``ALL_REASON_CODES`` 가 29개 unique (18-5 vector 도입 후).

    구성 (``docs/ai_rag_error_codes.md`` §1~§4):
      §1 기본 RAG/Safety/Provider 11개 + §2 LLM skip 10개 +
      §4 Provider 별칭 2개 = 23개 (18-2 시점).
    18-5 시점에 §1-8 + §3 embedding skip 6개 추가:
      vector_disabled / embedding_skipped_local_only / _same_hash /
      _short_query / _disabled / _api_key_missing → 총 29개.
    """
    codes = rag_schemas.ALL_REASON_CODES
    assert len(codes) == 29, f"expected 29 reason codes, got {len(codes)}"
    assert len(set(codes)) == len(codes)
    # 18-5 신규 6개 모두 포함
    new_18_5 = {
        "vector_disabled",
        "embedding_skipped_local_only",
        "embedding_skipped_same_hash",
        "embedding_skipped_short_query",
        "embedding_skipped_disabled",
        "embedding_skipped_api_key_missing",
    }
    assert new_18_5.issubset(set(codes)), (
        f"18-5 신규 reason_code 누락: {new_18_5 - set(codes)}"
    )


def test_schemas_reason_code_unsupported_question_present():
    """단일 표준 ``unsupported_question`` 정의 — ``unsupported_claim`` 별칭 부재."""
    assert rag_schemas.REASON_UNSUPPORTED_QUESTION == "unsupported_question"
    # 별칭이 없는지 — 모든 reason_code 문자열 검사
    assert "unsupported_claim" not in rag_schemas.ALL_REASON_CODES


def test_schemas_ai_modes_defined():
    """3개 AI 모드 정의 (``local_only`` / ``local_first`` / ``ai_assist``)."""
    assert rag_schemas.AI_MODE_LOCAL_ONLY == "local_only"
    assert rag_schemas.AI_MODE_LOCAL_FIRST == "local_first"
    assert rag_schemas.AI_MODE_AI_ASSIST == "ai_assist"


def test_schemas_source_dataclass_instantiable():
    """``Source(title, path, snippet)`` 생성 가능 + 키로 dict 변환 가능."""
    s = rag_schemas.Source(title="t", path="p", snippet="sn")
    assert s.title == "t"
    assert s.path == "p"
    assert s.snippet == "sn"


def test_schemas_answer_dataclass_default_values():
    """``Answer`` 기본값 — confidence=unknown, not_found=False, blocked=False."""
    a = rag_schemas.Answer(answer="x")
    assert a.confidence == "unknown"
    assert a.not_found is False
    assert a.blocked is False
    assert a.guard_hits == 0
    assert a.top_score == 0
    # optional 은 기본 None
    assert a.reason_code is None
    assert a.llm_called is None


# ────────── 2. prompts — manual_qa 시스템 프롬프트 v1 고정 ──────────


def test_prompts_manual_qa_system_v1_present():
    """``PROMPTS["manual_qa.system"]["v1"]`` 가 존재 + 비어있지 않음."""
    text = rag_prompts.get_prompt("manual_qa.system", "v1")
    assert isinstance(text, str)
    assert len(text) > 0


def test_prompts_default_version_is_v1():
    """default 버전이 v1."""
    assert rag_prompts.DEFAULT_VERSIONS["manual_qa.system"] == "v1"
    # version 미지정 호출 → v1 반환
    assert rag_prompts.get_prompt("manual_qa.system") == \
        rag_prompts.PROMPTS["manual_qa.system"]["v1"]


def test_prompts_v1_matches_current_manual_qa_system():
    """v1 프롬프트가 현행 ``manual_qa._MANUAL_SYSTEM_PROMPT`` 와 1:1."""
    v1 = rag_prompts.get_prompt("manual_qa.system", "v1")
    assert v1 == ai_manual_qa._MANUAL_SYSTEM_PROMPT


def test_prompts_unknown_name_or_version_raises():
    """미지정 이름/버전 → ``KeyError``."""
    import pytest as _pt
    with _pt.raises(KeyError):
        rag_prompts.get_prompt("nonexistent.prompt")
    with _pt.raises(KeyError):
        rag_prompts.get_prompt("manual_qa.system", "v999")


# ────────── 3. safety — stub 인터페이스만 ──────────


def test_safety_check_query_empty_returns_invalid_query():
    """빈 질문 → ``allowed=False`` + ``reason_code="invalid_query"``."""
    d = rag_safety.check_query("   ")
    assert d.allowed is False
    assert d.reason_code == rag_schemas.REASON_INVALID_QUERY


def test_safety_check_query_normal_passes_in_18_1():
    """18-1 시점에는 정상 입력은 그대로 통과 (실제 PII 차단은 manual_qa 가 처리)."""
    d = rag_safety.check_query("백업은 어디서 해?")
    assert d.allowed is True
    assert d.reason_code == ""


# ────────── 4. pipeline / retriever — stub 미구현 검증 ──────────


def test_pipeline_run_manual_qa_not_implemented():
    """18-1 시점에는 pipeline stub — ``NotImplementedError`` raise."""
    import pytest as _pt
    with _pt.raises(NotImplementedError):
        rag_pipeline.run_manual_qa(None, "예약문자 작성")


def test_retriever_retrieve_not_implemented():
    """18-1 시점에는 retriever stub — ``NotImplementedError`` raise."""
    import pytest as _pt
    with _pt.raises(NotImplementedError):
        rag_retriever.retrieve("예약문자 작성")


# ────────── 5. 기존 manual_qa 동작 회귀 0 ──────────


def test_existing_manual_qa_known_question_unchanged():
    """기존 ``ask_manual_question`` 가 매뉴얼 매칭 질문에 대해 v1.3.3 동일 동작."""
    _rag_reset_cache()
    fake = FakeProvider(
        return_text="예약문자는 예약 문자 탭에서 작성합니다.\n참고: sms_compose.md"
    )
    res = ai_manual_qa.ask_manual_question(
        None, "예약문자 작성", provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert res["not_found"] is False
    assert len(res["sources"]) >= 1
    assert call_count(fake) == 1


def test_existing_manual_qa_unknown_question_unchanged():
    """기존 ``ask_manual_question`` 가 매뉴얼 미매칭 질문 → not_found+LLM 0."""
    _rag_reset_cache()
    fake = FakeProvider()
    res = ai_manual_qa.ask_manual_question(
        None, "주식 추천해줘 종목 시세", provider_override=fake,
    )
    assert_manual_ask_contract(res)
    assert res["not_found"] is True
    assert_no_external_call(fake)
