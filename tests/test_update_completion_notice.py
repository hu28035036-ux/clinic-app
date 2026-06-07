from __future__ import annotations

from pathlib import Path

from app import config as app_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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
