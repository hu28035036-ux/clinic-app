"""정적 자산 캐시 정책 + 새 버전 감지(/api/version) 계약.

업데이트 시 서브 PC 가 "새로고침 한 번"으로 최신 버전을 받도록 하는 메커니즘:
  - HTML 문서(/, /setup)는 no-cache → 매번 최신 ``?v=<버전>`` 을 집어옴
  - 정적 자산은 배포(frozen) + 버전 쿼리(?v=)면 immutable(영구 캐시 안전),
    dev 이거나 버전 쿼리가 없으면 no-cache(항상 최신 파일)
  - /api/version 은 현재 서버 버전만 반환하는 폴링용 초경량 endpoint
"""
from pathlib import Path

import app.main as app_main
from app.config import APP_VERSION

_MAIN_JS = Path(__file__).resolve().parent.parent / "app" / "static" / "js" / "main.js"
_MAIN_HTML = Path(__file__).resolve().parent.parent / "app" / "templates" / "main.html"


def test_version_endpoint_returns_app_version(client):
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.json() == {"version": APP_VERSION}
    assert "no-cache" in r.headers.get("cache-control", "")


def test_html_document_is_no_cache(client):
    # /setup 은 mode 와 무관하게 항상 렌더 — / 와 동일한 no-cache 헤더 공유.
    r = client.get("/setup")
    assert r.status_code == 200
    assert "no-cache" in r.headers.get("cache-control", "")


def test_static_asset_no_cache_in_dev(client):
    # 테스트 환경 = frozen 아님 → 버전 쿼리가 있어도 no-cache (편집 즉시 반영용).
    r = client.get(f"/static/js/main.js?v={APP_VERSION}")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"


def test_static_asset_immutable_when_frozen(client, monkeypatch):
    # 배포(frozen) + 버전 쿼리 → 영구 캐시(immutable). URL 이 버전마다 바뀌므로 안전.
    monkeypatch.setattr(app_main, "IS_FROZEN", True)
    r = client.get(f"/static/js/main.js?v={APP_VERSION}")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "immutable" in cc and "max-age=31536000" in cc


def test_static_asset_no_cache_when_frozen_but_unversioned(client, monkeypatch):
    # frozen 이라도 버전 쿼리 없는 자산은 no-cache (버전 무효화가 안 되므로 영구 캐시 금지).
    monkeypatch.setattr(app_main, "IS_FROZEN", True)
    r = client.get("/static/js/main.js")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"


def test_frozen_immutable_does_not_match_lookalike_param(client, monkeypatch):
    # 'rev=' 처럼 v= 를 포함하는 다른 파라미터는 버전으로 오인하지 않음 → no-cache.
    monkeypatch.setattr(app_main, "IS_FROZEN", True)
    r = client.get("/static/js/main.js?rev=2")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"


def test_update_banner_wiring_present():
    """새 버전 감지 배너 배선이 프론트에 존재하는지(실수로 제거 방지)."""
    js = _MAIN_JS.read_text(encoding="utf-8")
    assert "function checkForUpdate" in js
    assert "/api/version" in js
    assert "showUpdateBanner" in js
    html = _MAIN_HTML.read_text(encoding="utf-8")
    assert "APP_LOADED_VERSION" in html
