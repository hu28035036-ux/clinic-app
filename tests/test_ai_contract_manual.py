"""18-7 API 계약 회귀 — `/api/ai/status` 도입 후에도 v1.3.3 응답 키 보존.

본 테스트는 18-1 의 ``test_ai_manual_rag_contract.py`` 와 동일한 계약을
"18-7 라우터 변경 후" 시점에 한 번 더 단언한다.

검증:
  1. ``/api/ai/manual/search`` 응답 3개 키 (sources/masked_question/top_score)
  2. ``/api/ai/manual/ask`` 응답 9개 키 (v1.3.3) — 추가 0, 제거 0
  3. ``sources[]`` 항목 3개 키 (title/path/snippet)
  4. ``/api/ai/status`` 추가가 manual/* 응답에 영향 0
  5. 신규 optional 키 (``reason_code`` / ``llm_called`` / ``ai_mode`` /
     ``prompt_version``) 는 본 세션에서 응답에 도입하지 않음 — 부재 정상
     (사용자 18-7 지시문: 기존 API 응답 key 변경 금지).

상세: ``docs/checklists/18-7_admin_ui_checklist.md`` 완료 조건,
``docs/ai_rag_test_plan.md`` §4-3.
"""
from __future__ import annotations

from tests.harness.contract import (
    MANUAL_ASK_REQUIRED,
    MANUAL_SEARCH_REQUIRED,
    SOURCE_ITEM_REQUIRED,
    assert_manual_ask_contract,
    assert_manual_search_contract,
)

# ──────────────────────── 1. manual/search 계약 (18-7 회귀) ────────────────────────


def test_18_7_manual_search_keys_preserved(client):
    """``/api/ai/manual/search`` 응답이 18-1 시점과 동일 — 18-7 health 모듈
    추가가 영향 X."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/search", json={"question": "예약문자 작성"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert_manual_search_contract(body)
    for k in MANUAL_SEARCH_REQUIRED:
        assert k in body, f"manual/search missing key: {k!r}"
    # 18-7 시점 추가 키가 응답에 들어가지 않았는지 확인.
    extra = set(body.keys()) - set(MANUAL_SEARCH_REQUIRED)
    assert extra == set(), (
        f"18-7 시점 manual/search 응답에 신규 키 추가됨: {extra} — 사용자 지시문 위반"
    )


def test_18_7_manual_search_unknown_keeps_keys(client):
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/search", json={"question": "주식 추천 종목"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert_manual_search_contract(body)
    assert body["sources"] == []
    assert body["top_score"] == 0


# ──────────────────────── 2. manual/ask 계약 (18-7 회귀) ────────────────────────


def test_18_7_manual_ask_required_9_keys_preserved(client, ai_enabled_with_fake):
    """``/api/ai/manual/ask`` 응답 9키 그대로 — 사용자 18-7 지시문."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert_manual_ask_contract(body)
    for k in MANUAL_ASK_REQUIRED:
        assert k in body, f"manual/ask missing key: {k!r}"
    # 회귀 — 응답 키가 정확히 9개여야 함 (사용자 18-7 지시문: 추가도 안 함).
    extra = set(body.keys()) - set(MANUAL_ASK_REQUIRED)
    assert extra == set(), (
        f"18-7 시점 manual/ask 응답에 신규 키 추가됨: {extra} — 사용자 지시문 위반"
    )


def test_18_7_manual_ask_no_optional_keys_added_in_18_7(client, ai_enabled_with_fake):
    """신규 optional 키 (reason_code / llm_called / embedding_called /
    ai_mode / prompt_version) 가 응답에 부재 — 본 세션 범위 외."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    body = resp.json()
    forbidden_optional_in_18_7 = (
        "reason_code", "llm_called", "embedding_called",
        "ai_mode", "prompt_version",
    )
    leaked = [k for k in forbidden_optional_in_18_7 if k in body]
    assert leaked == [], (
        f"18-7 응답에 신규 optional 키 도입됨: {leaked} — "
        "사용자 18-7 지시문은 manual/ask 응답 구조 유지 (추가 0)"
    )


# ──────────────────────── 3. sources[] 항목 계약 (회귀) ────────────────────────


def test_18_7_source_items_have_3_keys(client, ai_enabled_with_fake):
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    body = resp.json()
    assert isinstance(body["sources"], list)
    for s in body["sources"]:
        assert set(s.keys()) == set(SOURCE_ITEM_REQUIRED), (
            f"sources[] 항목 키 변동: 기대 {SOURCE_ITEM_REQUIRED}, 실제 {set(s.keys())}"
        )


# ──────────────────────── 4. /api/ai/status 추가가 manual/* 영향 0 ────────────────────────


def test_18_7_status_call_does_not_affect_manual_ask(client, ai_enabled_with_fake):
    """``/api/ai/status`` 호출 후 manual/ask 응답이 그대로 9키."""
    from app.services.rag.search import reset_cache

    reset_cache()
    # status 먼저 호출 (admin 토큰 필요).
    login = client.post("/api/admin/login", json={"password": "admin1234"})
    assert login.status_code == 200
    token = login.json().get("token", "")
    resp_status = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp_status.status_code == 200

    # 이후 manual/ask 호출 — 응답 9키 그대로.
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    assert resp.status_code == 200
    body = resp.json()
    assert_manual_ask_contract(body)
    extra = set(body.keys()) - set(MANUAL_ASK_REQUIRED)
    assert extra == set()


def test_18_7_status_call_does_not_affect_manual_search(client):
    """``/api/ai/status`` 호출 후 manual/search 응답이 그대로 3키."""
    from app.services.rag.search import reset_cache

    reset_cache()
    login = client.post("/api/admin/login", json={"password": "admin1234"})
    token = login.json().get("token", "")
    resp_status = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp_status.status_code == 200

    resp = client.post("/api/ai/manual/search", json={"question": "백업"})
    assert resp.status_code == 200
    body = resp.json()
    assert_manual_search_contract(body)
    extra = set(body.keys()) - set(MANUAL_SEARCH_REQUIRED)
    assert extra == set()


# ──────────────────────── 5. /api/ai/health/public 계약 (18-7 회귀) ────────────────────────


def test_18_7_health_public_keys_unchanged(client):
    """``/api/ai/health/public`` 4 필드 — 18-7 health 모듈 추가 후에도 동일."""
    saved = client.headers.pop("X-Admin-Token", None)
    try:
        resp = client.get("/api/ai/health/public")
    finally:
        if saved:
            client.headers["X-Admin-Token"] = saved
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"enabled", "ready", "provider", "api_key_set"}


def test_18_7_health_admin_keys_unchanged(client):
    """``/api/ai/health`` admin 9 필드 — 18-7 후에도 동일."""
    login = client.post("/api/admin/login", json={"password": "admin1234"})
    token = login.json().get("token", "")
    resp = client.get("/api/ai/health", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    body = resp.json()
    expected = {
        "enabled", "ready", "provider", "api_key_set",
        "model", "sdk_installed", "sdk_errors",
        "knowledge_doc_count", "version",
    }
    assert set(body.keys()) == expected, (
        f"/api/ai/health admin 응답 키 변동: {set(body.keys()) - expected}, "
        f"누락: {expected - set(body.keys())}"
    )
