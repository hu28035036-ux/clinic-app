from __future__ import annotations

from pathlib import Path

from app import config as app_config
from app.routers import api as api_router

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


def _set_last_seen(version: str) -> dict:
    original = app_config.load_config()
    cfg = dict(original)
    cfg["update_last_seen_version"] = version
    app_config.save_config(cfg)
    return original


def test_about_silently_marks_current_version_on_first_seen(client):
    original = _set_last_seen("")
    try:
        resp = client.get("/api/about")
        assert resp.status_code == 200
        body = resp.json()

        assert body["version"] == app_config.APP_VERSION
        assert body["update_completed"] is None
        assert app_config.load_config()["update_last_seen_version"] == app_config.APP_VERSION
    finally:
        app_config.save_config(original)


def test_about_returns_update_completion_notice_once(client):
    previous_version = "1.3.14"
    original = _set_last_seen(previous_version)
    try:
        first = client.get("/api/about")
        assert first.status_code == 200
        first_body = first.json()

        notice = first_body["update_completed"]
        assert notice["version"] == app_config.APP_VERSION
        assert notice["previous_version"] == previous_version
        assert notice["build_date"] == app_config.APP_BUILD_DATE
        assert app_config.APP_VERSION in notice["message"]
        assert app_config.load_config()["update_last_seen_version"] == app_config.APP_VERSION

        second = client.get("/api/about")
        assert second.status_code == 200
        assert second.json()["update_completed"] is None
    finally:
        app_config.save_config(original)


def test_update_ui_has_one_time_completion_notice_contract():
    src = (PROJECT_ROOT / "app" / "templates" / "main.html").read_text(encoding="utf-8")

    assert "function maybeShowUpdateCompletedNotice(a)" in src
    assert "a && a.update_completed" in src
    assert "sessionStorage.getItem(key)" in src
    assert "maybeShowUpdateCompletedNotice(a)" in src
    assert "업데이트 안내 화면" in src or "update_completed" in src
    assert "자동 새로고침" in src
    assert "화면이 멈춥니다" not in src


def test_check_update_uses_and_saves_payload_manifest_url(client, monkeypatch):
    original = app_config.load_config()
    payload_url = "https://hu28035036-ux.github.io/clinic-updates/manifest.json"
    seen = {}

    def fake_fetch(url: str, timeout: int = 8) -> dict:
        seen["url"] = url
        seen["timeout"] = timeout
        return {
            "version": "9.9.9",
            "download_url": "https://example.com/dosu.zip",
            "sha256": "abc123",
            "notes": "테스트 업데이트",
            "mandatory": False,
        }

    cfg = dict(original)
    cfg["update_manifest_url"] = "https://old.example.invalid/manifest.json"
    app_config.save_config(cfg)
    monkeypatch.setattr(api_router, "_fetch_update_manifest", fake_fetch)
    try:
        resp = client.post(
            "/api/about/check-update",
            json={"update_manifest_url": payload_url},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["available"] is True
        assert body["latest_version"] == "9.9.9"
        assert seen == {"url": payload_url, "timeout": 8}
        assert app_config.load_config()["update_manifest_url"] == payload_url
    finally:
        app_config.save_config(original)


def test_update_ui_sends_manifest_url_in_check_body():
    src = (PROJECT_ROOT / "app" / "templates" / "main.html").read_text(encoding="utf-8")

    assert "const url = (document.getElementById('update-url-input')?.value || '').trim();" in src
    assert "body: JSON.stringify({ update_manifest_url: url })" in src
