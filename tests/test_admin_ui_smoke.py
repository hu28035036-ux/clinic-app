"""18-7 관리자 UI smoke — 상태 API 라우트 등록 + 권한 일관성.

본 세션 (사용자 18-7 지시문) 의 UI 결정:
  - main.html / app.css 무수정 — 사용자 명시 "화면 또는 상태 API" 중 API 만 구현.
  - main.html UI 통합 / Reindex 버튼 / vector 토글은 18-8 또는 별도 세션.
  - 따라서 본 smoke 는 main.html DOM 검사 대신, 라우트 등록 + 권한 일관성 +
    응답 본체 sanity 만 확인.

검증:
  1. ``/api/ai/status`` 가 라우터에 등록됨 (FastAPI app.routes 검사).
  2. ``/api/ai/health`` / ``/api/ai/health/public`` / ``/api/ai/status`` 권한 일관:
     - public: 토큰 불필요
     - admin (status/health): 토큰 필수
  3. status 응답이 sane (top-level 키 모두 존재 + 타입 정확).
  4. 운영 DB 미사용.
"""
from __future__ import annotations

from app.services.ai.health import (
    AI_MODE_LOCAL_FIRST,
    AI_MODE_LOCAL_ONLY,
    SEARCH_MODE_KEYWORD,
)


def _admin_token(client) -> str:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200
    return resp.json().get("token", "")


# ──────────────────────── 1. 라우트 등록 ────────────────────────


def test_status_route_registered_in_app():
    """``/api/ai/status`` 가 FastAPI app.routes 에 등록되어 있어야 함."""
    from app.main import app as _app

    paths = {r.path for r in _app.routes if hasattr(r, "path")}
    assert "/api/ai/status" in paths, (
        f"`/api/ai/status` 라우트 미등록. 현재 paths: "
        f"{sorted(p for p in paths if p.startswith('/api/ai'))}"
    )


def test_existing_ai_routes_still_registered():
    """18-7 변경이 기존 라우트를 제거하지 않았는지."""
    from app.main import app as _app

    paths = {r.path for r in _app.routes if hasattr(r, "path")}
    # v1.3.3 + 18-7 시점에 반드시 존재해야 할 라우트.
    must_have = {
        "/api/ai/health",
        "/api/ai/health/public",
        "/api/ai/providers",
        "/api/ai/settings",
        "/api/ai/manual/search",
        "/api/ai/manual/ask",
        "/api/ai/sms/validate",
        "/api/ai/sms/draft",
        "/api/ai/status",  # 18-7 신규
    }
    missing = must_have - paths
    assert not missing, f"필수 AI 라우트 누락: {missing}"


# ──────────────────────── 2. 권한 일관성 ────────────────────────


def test_status_requires_admin_consistent_with_health(client):
    """``/api/ai/status`` 와 ``/api/ai/health`` 모두 admin 토큰 강제."""
    saved = client.headers.pop("X-Admin-Token", None)
    try:
        resp_status = client.get("/api/ai/status")
        resp_health = client.get("/api/ai/health")
    finally:
        if saved:
            client.headers["X-Admin-Token"] = saved
    assert resp_status.status_code == 401
    assert resp_health.status_code == 401


def test_public_endpoint_no_token_still_works(client):
    """``/api/ai/health/public`` 만 토큰 불필요 — status 와 동시 호출 시에도."""
    saved = client.headers.pop("X-Admin-Token", None)
    try:
        resp = client.get("/api/ai/health/public")
    finally:
        if saved:
            client.headers["X-Admin-Token"] = saved
    assert resp.status_code == 200


# ──────────────────────── 3. status 응답 sanity ────────────────────────


def test_status_response_top_level_keys_sane(client):
    """status 응답에 9개 최상위 키 모두 존재."""
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    body = resp.json()
    expected_top_level = {
        "ai_mode", "search_mode", "version",
        "ai_settings", "vector_status", "external_api",
        "knowledge", "prompt_versions", "recent_ai_logs",
    }
    missing = expected_top_level - set(body.keys())
    assert not missing, f"status 응답 누락 키: {missing}"


def test_status_ai_mode_value_is_valid(client):
    """ai_mode 값이 표준 3개 모드 중 하나."""
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    body = resp.json()
    assert body["ai_mode"] in (
        AI_MODE_LOCAL_ONLY, AI_MODE_LOCAL_FIRST, "ai_assist",
    )


def test_status_search_mode_keyword_in_18_7(client):
    """search_mode = 'keyword' (18-7 시점 — pipeline 미통합)."""
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    body = resp.json()
    assert body["search_mode"] == SEARCH_MODE_KEYWORD


def test_status_knowledge_counts_are_int(client):
    """knowledge.{documents,chunks,vectors} 모두 int."""
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    body = resp.json()
    k = body["knowledge"]
    assert isinstance(k["documents"], int)
    assert isinstance(k["chunks"], int)
    assert isinstance(k["vectors"], int)
    assert k["documents"] >= 0
    assert k["chunks"] >= 0
    assert k["vectors"] >= 0


def test_status_vector_status_disabled_in_18_7(client):
    """vector_status — 18-7 시점 m014 미도입 → enabled=False, available=False."""
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    body = resp.json()
    vs = body["vector_status"]
    assert vs["enabled"] is False
    assert vs["available"] is False
    assert vs["reason"] == "vector_disabled"


def test_status_prompt_versions_includes_manual_qa(client):
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    body = resp.json()
    assert body["prompt_versions"].get("manual_qa.system") == "v1"


def test_status_recent_ai_logs_structure(client):
    """recent_ai_logs 구조 — lookback_hours / total / by_outcome / by_feature / recent."""
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    body = resp.json()
    rl = body["recent_ai_logs"]
    assert isinstance(rl["lookback_hours"], int)
    assert isinstance(rl["total"], int)
    assert isinstance(rl["by_outcome"], dict)
    assert isinstance(rl["by_feature"], dict)
    assert isinstance(rl["recent"], list)
    # 표준 outcome 4개가 by_outcome 에 시드되어 있어야 함.
    for o in ("success", "warning", "blocked", "error"):
        assert o in rl["by_outcome"]


# ──────────────────────── 4. API key / PII 비노출 (응답 본문 검사) ────────────────────────


def test_status_response_does_not_contain_api_key(client, ai_enabled_with_fake):
    """fixture 가 'test-fake-key' 를 등록 — 응답 본문 어디에도 부재."""
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    text = resp.text
    assert "test-fake-key" not in text
    # admin 화면에 마스킹 형식 (`test****`) 도 노출하지 않음 — boolean only.
    assert "test****" not in text
    body = resp.json()
    # api_key_set boolean 만.
    assert body["ai_settings"]["api_key_set"] is True
    # api_key 자체 키 부재.
    assert "api_key" not in body["ai_settings"]
    assert "api_key_masked" not in body["ai_settings"]


# ──────────────────────── 5. 운영 DB 미사용 ────────────────────────


def test_status_does_not_use_operational_db(db_path):
    """conftest 격리 검증."""
    norm = db_path.lower().replace("\\", "/")
    assert ("temp" in norm) or ("test" in norm), db_path


# ──────────────────────── 6. UI 미수정 입증 ────────────────────────


def test_main_html_unchanged_in_18_7():
    """본 세션은 main.html 수정 0 — 사용자 지시문 'API 만으로 충분'.

    main.html 이 신규 ``/api/ai/status`` 엔드포인트 호출 코드를 포함하지 않아도
    OK (UI 통합은 18-8 또는 별도 세션). 본 테스트는 18-7 변경 범위가
    main.html 에 닿지 않았는지 stub 으로 단언 — 실제 UI 통합 세션에서
    본 단언을 갱신/제거 결정.
    """
    from pathlib import Path

    main_html = Path(__file__).resolve().parent.parent / "app" / "templates" / "main.html"
    if not main_html.exists():
        return  # main.html 부재 환경 (PyInstaller 빌드 결과 등) — skip
    text = main_html.read_text(encoding="utf-8", errors="ignore")
    # 18-7 시점 — main.html 이 /api/ai/status 호출 코드를 추가하지 않았는지.
    assert "/api/ai/status" not in text, (
        "18-7 세션은 main.html 수정 0 정책 — `/api/ai/status` 호출 코드가 "
        "main.html 에 추가되었습니다. UI 통합은 별도 세션."
    )
