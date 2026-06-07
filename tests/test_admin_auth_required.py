"""인증이 필요한 엔드포인트들에 대한 회귀 방지 테스트.

운영 위험 감사에서 발견된 인증 누수 7개 케이스 — 토큰 없이 호출 시 401 반환 확인.
+ peer 노드 동기화용 X-Sync-Token 듀얼 인증 검증.

이 테스트가 실패한다면 누군가 기존 require_admin/require_admin_or_sync_token 의존성을
실수로 제거했거나, 새 엔드포인트가 인증 없이 추가된 것 — 즉시 코드 리뷰 필요.
"""
from __future__ import annotations

import json
from datetime import datetime

from app.config import get_config_path, load_config, save_config


def _admin_token(client) -> str:
    """관리자 로그인 토큰 (테스트 시드 비번)."""
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json().get("token", "")


def _sync_token() -> str:
    """현재 config 의 sync_secret 반환 (load_config 가 자동 생성/저장)."""
    cfg = load_config()
    secret = cfg.get("sync_secret")
    assert secret, "load_config 가 sync_secret 을 자동 생성하지 않음 — config.py 회귀."
    return secret


# ─────────────────────────────────────────────────────────
# 인증 누수 회귀 방지: 토큰 없으면 모두 401 이어야 함
# ─────────────────────────────────────────────────────────


def test_sync_pull_requires_admin(client):
    resp = client.get("/api/sync/pull", params={"since": datetime.utcnow().isoformat()})
    assert resp.status_code == 401, (
        "GET /api/sync/pull 은 관리자 인증이 필요합니다 — 같은 네트워크 누구나 SyncOp 큐를 노출하면 안 됨."
    )


def test_sync_push_requires_admin(client):
    resp = client.post("/api/sync/push", json={"ops": []})
    assert resp.status_code == 401, (
        "POST /api/sync/push 는 관리자 인증이 필요합니다 — 외부에서 임의 op 주입을 막아야 함."
    )


def test_sync_now_requires_admin(client):
    resp = client.post("/api/sync/now")
    assert resp.status_code == 401, (
        "POST /api/sync/now 는 관리자 인증이 필요합니다 — 누구나 동기화 트리거를 막아야 함."
    )


def test_backup_requires_admin(client):
    resp = client.get("/api/backup")
    assert resp.status_code == 401, (
        "GET /api/backup 은 관리자 인증이 필요합니다 — DB 파일 자체가 환자정보·SMS키·admin해시를 포함."
    )


def test_mode_first_local_setup_allows_without_admin_and_strips_secrets(client):
    """첫 실행(cfg.mode 없음) + 로컬 접속은 설치 화면 진행을 위해 허용."""
    original = dict(load_config())
    cfg = dict(original)
    cfg["mode"] = None
    save_config(cfg)
    try:
        resp = client.post("/api/mode", json={"mode": "main"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "main"
        assert "sync_secret" not in body
        assert "admin_password_hash" not in body
    finally:
        save_config(original)


def test_mode_change_after_setup_requires_admin(client):
    """한 번 모드가 설정된 뒤에는 무인증 main/sub 전환을 막는다."""
    original = dict(load_config())
    cfg = dict(original)
    cfg["mode"] = "main"
    save_config(cfg)
    try:
        resp = client.post("/api/mode", json={"mode": "sub", "main_url": "http://127.0.0.1:8000"})
        assert resp.status_code == 401, (
            "POST /api/mode 는 첫 로컬 설치가 끝난 뒤 관리자 인증이 필요합니다."
        )
    finally:
        save_config(original)


# ─────────────────────────────────────────────────────────
# 토큰 있을 때 정상 응답 확인 (regression — 토큰 정상 흐름이 안 깨졌는지)
# ─────────────────────────────────────────────────────────


def test_sync_pull_works_with_admin(client):
    token = _admin_token(client)
    resp = client.get(
        "/api/sync/pull",
        params={"since": datetime(1970, 1, 1).isoformat()},
        headers={"x-admin-token": token},
    )
    assert resp.status_code == 200
    assert "ops" in resp.json()


def test_sync_push_returns_failure_count_on_partial(client):
    """sync_push 가 깨진 op 가 섞여 있어도 정상 op 는 적용하고 failures 카운트 반환."""
    token = _admin_token(client)
    # 의도적으로 빈/이상 payload 한 개 — apply_op 가 실패 가능성 (entity 없음)
    resp = client.post(
        "/api/sync/push",
        headers={"x-admin-token": token},
        json={"ops": [{"id": "bad", "node_id": "x", "entity": "_no_such_entity_", "op": "upsert", "payload": {}}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    # 새 응답 스키마에 applied/failed/failures 가 있어야 함
    assert "applied" in body
    assert "failed" in body
    assert "failures" in body


# ─────────────────────────────────────────────────────────
# X-Sync-Token (peer 노드 동기화) 듀얼 인증 검증
# ─────────────────────────────────────────────────────────


def test_sync_pull_works_with_valid_sync_token(client):
    """admin 토큰 없이도 X-Sync-Token 이 config sync_secret 과 일치하면 200."""
    token = _sync_token()
    resp = client.get(
        "/api/sync/pull",
        params={"since": datetime(1970, 1, 1).isoformat()},
        headers={"x-sync-token": token},
    )
    assert resp.status_code == 200
    assert "ops" in resp.json()


def test_sync_pull_rejects_wrong_sync_token(client):
    """잘못된 X-Sync-Token 은 401."""
    resp = client.get(
        "/api/sync/pull",
        params={"since": datetime(1970, 1, 1).isoformat()},
        headers={"x-sync-token": "not-the-real-secret"},
    )
    assert resp.status_code == 401


def test_sync_push_works_with_valid_sync_token(client):
    """X-Sync-Token 으로 sync_push 도 호출 가능."""
    token = _sync_token()
    resp = client.post(
        "/api/sync/push",
        headers={"x-sync-token": token},
        json={"ops": []},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["applied"] == 0
    assert body["failed"] == 0


def test_sync_push_rejects_wrong_sync_token(client):
    """잘못된 X-Sync-Token 은 sync_push 에서도 401."""
    resp = client.post(
        "/api/sync/push",
        headers={"x-sync-token": "not-the-real-secret"},
        json={"ops": []},
    )
    assert resp.status_code == 401


def test_sync_now_still_admin_only_not_token(client):
    """sync_now 는 관리자 트리거 전용 — X-Sync-Token 만으로는 거부 (require_admin 유지)."""
    token = _sync_token()
    resp = client.post("/api/sync/now", headers={"x-sync-token": token})
    assert resp.status_code == 401, (
        "sync_now 는 외부 노드가 호출하는 게 아니라 관리자가 트리거하는 엔드포인트라 "
        "X-Sync-Token 만으로는 통과시키지 않아야 합니다."
    )


def test_load_config_generates_sync_secret_per_node():
    """config 가 비어있을 때 sync_secret 이 자동 생성되어 저장되는지."""
    cfg = load_config()
    secret = cfg.get("sync_secret") or ""
    # token_urlsafe(32) 는 약 43자 — 단순 빈 문자열/짧은 값이면 안 됨
    assert len(secret) >= 32, f"sync_secret 이 너무 짧음 (len={len(secret)})"


def test_load_config_accepts_utf8_bom_config_file():
    """Windows 도구가 BOM을 붙여 저장한 config.json 도 읽을 수 있어야 한다."""
    original = dict(load_config())
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8-sig") as f:
            json.dump(original, f, ensure_ascii=False, indent=2)
        loaded = load_config()
        assert loaded["node_id"] == original["node_id"]
        assert loaded.get("sync_secret") == original.get("sync_secret")
    finally:
        save_config(original)


# ─────────────────────────────────────────────────────────
# sync_secret 노출 회귀 방지
# (이전 회귀: GET /api/config 가 인증 없이 cfg 전체를 반환하면서 sync_secret 까지 노출됨
#   → 누구나 X-Sync-Token 으로 sync pull/push 호출 가능 → 인증 무력화)
# ─────────────────────────────────────────────────────────


def test_get_config_does_not_expose_sync_secret_anonymously(client):
    """인증 없이 GET /api/config 호출 시 응답에 sync_secret 이 없어야 함."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert "sync_secret" not in body, (
        "GET /api/config 응답이 sync_secret 을 노출 — 누구나 X-Sync-Token 을 얻어 "
        "sync 인증을 우회할 수 있는 보안 회귀."
    )
    # admin_password_hash 도 같은 정책으로 노출되지 않아야 함 (기존 정책 유지 확인)
    assert "admin_password_hash" not in body


def test_get_config_admin_path_also_strips_secret(client):
    """관리자 토큰을 들고 호출해도 GET /api/config 응답에는 sync_secret 이 없어야 함.

    secret 조회는 별도 엔드포인트(GET /api/config/sync-secret) 에서만.
    """
    token = _admin_token(client)
    resp = client.get("/api/config", headers={"x-admin-token": token})
    assert resp.status_code == 200
    body = resp.json()
    assert "sync_secret" not in body
    assert "admin_password_hash" not in body


def test_dedicated_sync_secret_endpoint_requires_admin(client):
    """GET /api/config/sync-secret 은 관리자 인증 필수."""
    resp = client.get("/api/config/sync-secret")
    assert resp.status_code == 401


def test_dedicated_sync_secret_endpoint_returns_secret_for_admin(client):
    """관리자 토큰으로 호출 시 GET /api/config/sync-secret 이 원문 반환."""
    expected = _sync_token()
    token = _admin_token(client)
    resp = client.get("/api/config/sync-secret", headers={"x-admin-token": token})
    assert resp.status_code == 200
    assert resp.json().get("sync_secret") == expected


def test_regenerate_sync_secret_requires_admin(client):
    """POST /api/config/regenerate-sync-secret 은 관리자 인증 필수."""
    resp = client.post("/api/config/regenerate-sync-secret")
    assert resp.status_code == 401


def test_regenerate_sync_secret_changes_value(client):
    """관리자 토큰으로 재생성 호출 시 새 secret 으로 교체되고 응답에 그 값이 포함됨."""
    token = _admin_token(client)
    before = _sync_token()
    resp = client.post(
        "/api/config/regenerate-sync-secret",
        headers={"x-admin-token": token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    new_secret = body.get("sync_secret") or ""
    assert len(new_secret) >= 32
    assert new_secret != before, "재생성했는데 secret 값이 그대로임 — 회귀."
    # 새 값이 실제로 저장되어 sync_pull 인증에 통하는지 검증
    resp2 = client.get(
        "/api/sync/pull",
        params={"since": datetime(1970, 1, 1).isoformat()},
        headers={"x-sync-token": new_secret},
    )
    assert resp2.status_code == 200


def test_post_config_does_not_clobber_sync_secret(client):
    """POST /api/config payload 에 sync_secret 이 들어와도 무시되어야 함.

    실수로 빈 값을 보내면 인증이 망가지므로 — 갱신은 전용 regenerate 엔드포인트로만.
    """
    token = _admin_token(client)
    before = _sync_token()
    resp = client.post(
        "/api/config",
        headers={"x-admin-token": token},
        json={"sync_secret": "", "lunch_enabled": False},
    )
    assert resp.status_code == 200, resp.text
    # 응답 본문에도 sync_secret 이 없어야 함 (admin 이라도 echo 금지)
    assert "sync_secret" not in resp.json()
    # 실제 저장된 secret 도 그대로 유지
    after = _sync_token()
    assert after == before, "POST /api/config 가 sync_secret 을 덮어씀 — 회귀."


def test_sync_pull_still_rejects_no_or_wrong_token(client):
    """기존 sync 인증 정책이 그대로 — 토큰 없음/틀린 토큰은 401 (회귀 방지)."""
    # 토큰 없음
    r1 = client.get("/api/sync/pull", params={"since": datetime(1970, 1, 1).isoformat()})
    assert r1.status_code == 401
    # 틀린 토큰
    r2 = client.get(
        "/api/sync/pull",
        params={"since": datetime(1970, 1, 1).isoformat()},
        headers={"x-sync-token": "definitely-not-the-real-secret"},
    )
    assert r2.status_code == 401
