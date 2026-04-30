"""/api/ai/health/public — 인증 불필요 + 응답 4 필드 한정 회귀 테스트.

- public 은 토큰 없이 200, 응답 키가 정확히 {enabled, ready, provider, api_key_set} 4개.
- admin /api/ai/health 는 여전히 토큰 없으면 401, 토큰 있으면 9 필드 풀 응답
  (sdk_errors 포함 — provider 별 import 실패 사유 진단용. admin 전용).
"""
from __future__ import annotations

PUBLIC_FIELDS = {"enabled", "ready", "provider", "api_key_set"}
ADMIN_FIELDS = PUBLIC_FIELDS | {
    "model", "sdk_installed", "sdk_errors", "knowledge_doc_count", "version",
}


def _admin_token(client) -> str:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json().get("token", "")


def test_ai_health_public_no_token_returns_200(client):
    """토큰 없이 GET → 200, 응답 키가 정확히 public 4 필드만."""
    # 헤더 leak 방지 — 다른 테스트 모듈이 client 헤더에 토큰을 set 했을 수 있음
    saved = client.headers.pop("X-Admin-Token", None)
    try:
        resp = client.get("/api/ai/health/public")
    finally:
        if saved:
            client.headers["X-Admin-Token"] = saved

    assert resp.status_code == 200, f"public 은 인증 없이 200 이어야 함: {resp.status_code} {resp.text}"
    body = resp.json()
    assert set(body.keys()) == PUBLIC_FIELDS, (
        f"public 응답 키가 정확히 {PUBLIC_FIELDS} 이어야 합니다. "
        f"실제: {set(body.keys())}"
    )
    # 타입 검증 — 모두 bool / str
    assert isinstance(body["enabled"], bool)
    assert isinstance(body["ready"], bool)
    assert isinstance(body["api_key_set"], bool)
    assert isinstance(body["provider"], str)


def test_ai_health_admin_still_requires_token(client):
    """기존 /api/ai/health 는 토큰 없으면 401 그대로."""
    saved = client.headers.pop("X-Admin-Token", None)
    try:
        resp = client.get("/api/ai/health")
    finally:
        if saved:
            client.headers["X-Admin-Token"] = saved

    assert resp.status_code == 401, (
        f"/api/ai/health 는 admin 전용으로 토큰 없으면 401 이어야 함: {resp.status_code}"
    )


def test_ai_health_admin_with_token_returns_full_payload(client):
    """토큰 있으면 admin /health 는 9 필드 모두 포함 (sdk_errors 포함)."""
    token = _admin_token(client)
    resp = client.get("/api/ai/health", headers={"X-Admin-Token": token})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == ADMIN_FIELDS, (
        f"admin 응답이 9 필드 모두 포함해야 합니다. 실제: {set(body.keys())}"
    )
    assert isinstance(body["sdk_installed"], dict)
    assert isinstance(body["sdk_errors"], dict)
    assert isinstance(body["knowledge_doc_count"], int)
    assert isinstance(body["version"], str)


def test_ai_health_admin_sdk_errors_only_on_failure(client):
    """sdk_errors 는 import 실패한 provider 만 키로 가짐.

    venv 에 openai/anthropic 둘 다 정상 설치돼 있으면 빈 dict.
    누락 시 해당 키에 짧은 에러 메시지 포함.
    """
    token = _admin_token(client)
    resp = client.get("/api/ai/health", headers={"X-Admin-Token": token})
    body = resp.json()
    sdk_installed = body["sdk_installed"]
    sdk_errors = body["sdk_errors"]
    # 설치된 provider 는 sdk_errors 에 등장하지 않아야 함
    for prov, ok in sdk_installed.items():
        if ok:
            assert prov not in sdk_errors, (
                f"설치된 {prov} 가 sdk_errors 에 있으면 안 됨: {sdk_errors[prov]!r}"
            )
    # public 엔드포인트에는 sdk_errors 가 노출되면 안 됨
    saved = client.headers.pop("X-Admin-Token", None)
    try:
        pub = client.get("/api/ai/health/public").json()
    finally:
        if saved:
            client.headers["X-Admin-Token"] = saved
    assert "sdk_errors" not in pub, "sdk_errors 는 admin 전용이어야 함"
