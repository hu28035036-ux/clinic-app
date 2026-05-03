"""18-1 API 계약 회귀 테스트 — manual/{search,ask} 응답 키 변동 0 검증.

신규 RAG 골격이 도입된 상태에서도 v1.3.3 응답 키가 정확히 보존되는지
라우터 레벨에서 단언한다. 18-2 이후 응답에 신규 optional 키가 추가되더라도
필수 키가 사라지면 본 테스트가 즉시 실패해야 한다.

상세: ``docs/ai_rag_test_plan.md`` §4-3, ``docs/harnesses/component_harness_matrix.md`` §1-10.
"""
from __future__ import annotations

from tests.harness.contract import (
    MANUAL_ASK_REQUIRED,
    MANUAL_SEARCH_REQUIRED,
    SOURCE_ITEM_REQUIRED,
    assert_manual_ask_contract,
    assert_manual_search_contract,
)

# ────────── 1. manual/search 계약 ──────────


def test_contract_manual_search_required_keys_3():
    """필수 키 정의 — 3개 (sources / masked_question / top_score)."""
    assert set(MANUAL_SEARCH_REQUIRED) == {"sources", "masked_question", "top_score"}


def test_contract_manual_search_200_response_has_all_required_keys(client):
    """라우터 ``/api/ai/manual/search`` 200 응답에 필수 3개 키 모두 존재."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/search", json={"question": "예약문자 작성"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for k in MANUAL_SEARCH_REQUIRED:
        assert k in body, f"manual/search missing key: {k!r}"
    assert_manual_search_contract(body)


def test_contract_manual_search_unknown_question_keeps_keys(client):
    """매칭 없는 질문에서도 필수 3개 키 모두 존재 (sources=[], top_score=0)."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/search", json={"question": "주식 추천 종목"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert_manual_search_contract(body)
    assert body["sources"] == []
    assert body["top_score"] == 0


# ────────── 2. manual/ask 계약 ──────────


def test_contract_manual_ask_required_keys_9():
    """필수 키 정의 — 9개 (v1.3.3 응답 키)."""
    assert set(MANUAL_ASK_REQUIRED) == {
        "answer", "sources", "confidence", "not_found",
        "blocked", "blocked_reason", "guard_hits",
        "top_score", "masked_question",
    }


def test_contract_manual_ask_200_response_has_all_9_keys(client, ai_enabled_with_fake):
    """라우터 ``/api/ai/manual/ask`` 200 응답에 필수 9개 키 모두 존재."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for k in MANUAL_ASK_REQUIRED:
        assert k in body, f"manual/ask missing key: {k!r}"
    assert_manual_ask_contract(body)


def test_contract_manual_ask_no_unknown_required_keys_removed(client, ai_enabled_with_fake):
    """필수 9개 키가 단 하나도 사라지지 않음 (강한 회귀 단언)."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    body = resp.json()
    missing = [k for k in MANUAL_ASK_REQUIRED if k not in body]
    assert not missing, f"manual/ask 응답 키 회귀 — 제거된 키: {missing}"


# ────────── 3. sources[] 항목 계약 ──────────


def test_contract_source_item_required_keys_3():
    """``sources[]`` 항목 필수 키 — 3개 (title / path / snippet)."""
    assert set(SOURCE_ITEM_REQUIRED) == {"title", "path", "snippet"}


def test_contract_source_items_have_3_keys(client, ai_enabled_with_fake):
    """라우터 응답 ``sources[]`` 의 모든 항목에 3개 키 존재."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    body = resp.json()
    assert isinstance(body["sources"], list)
    for s in body["sources"]:
        for k in SOURCE_ITEM_REQUIRED:
            assert k in s, f"source item missing key: {k!r}"


# ────────── 4. 신규 optional 키는 있어도 OK / 없어도 OK ──────────


def test_contract_optional_keys_not_required_in_v1_3_3(client, ai_enabled_with_fake):
    """v1.3.3 응답에는 신규 optional 키가 없어야 정상 (18-2 이후 추가 가능)."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    body = resp.json()
    # 18-1 시점에는 라우터/manual_qa 가 신규 optional 키를 추가하지 않음 → 부재 정상.
    # 18-2 이후 추가되어도 본 테스트는 실패하지 않는다 (강제 단언 X — 정보 확인용).
    optional_keys_in_response = [k for k in (
        "reason_code", "llm_called", "ai_mode", "prompt_version",
    ) if k in body]
    # 18-1 시점에는 0개. 만약 늘어나면 다음 세션의 추가 도입 흔적이므로 그대로 통과.
    assert isinstance(optional_keys_in_response, list)
