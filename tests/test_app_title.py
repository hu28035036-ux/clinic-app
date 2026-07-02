"""앱/홈페이지 이름(app_title) 편집 기능 테스트.

좌측 상단 헤더 + 브라우저 탭 제목을 관리자 탭에서 수정 가능하게 한 기능.
- config.json 의 새 키 `app_title` 로 저장 (POST/GET /api/config 재사용).
- base.html 이 Jinja 전역 app_title() 로 라이브 렌더 → 저장 후 새로고침 시 반영.

이 테스트가 깨지면 헤더/탭 제목 커스터마이즈가 회귀한 것 — 코드 리뷰 필요.
"""
from __future__ import annotations

from app.config import load_config, save_config

DEFAULT_TITLE = "병원 예약 관리"


def _admin_token(client) -> str:
    """관리자 로그인 토큰 (테스트 시드 비번)."""
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json().get("token", "")


def _set_app_title(client, value: str):
    """관리자 토큰으로 app_title 저장 후 응답 반환."""
    token = _admin_token(client)
    return client.post(
        "/api/config",
        headers={"x-admin-token": token},
        json={"app_title": value},
    )


# ─────────────────────────────────────────────────────────
# 기본값 / 조회
# ─────────────────────────────────────────────────────────


def test_get_config_exposes_app_title_default(client):
    """GET /api/config 응답에 app_title 이 노출되고 기본값을 가진다."""
    # 다른 테스트가 바꿔놨을 수 있으니 먼저 기본값으로 리셋
    original = dict(load_config())
    try:
        cfg = dict(original)
        cfg["app_title"] = DEFAULT_TITLE
        save_config(cfg)
        body = client.get("/api/config").json()
        assert "app_title" in body, "GET /api/config 가 app_title 을 노출하지 않음 — DEFAULT_CONFIG 회귀."
        assert body["app_title"] == DEFAULT_TITLE
    finally:
        save_config(original)


# ─────────────────────────────────────────────────────────
# 저장 / 정규화
# ─────────────────────────────────────────────────────────


def test_post_app_title_persists(client):
    """관리자가 새 이름을 저장하면 GET /api/config 에 반영된다."""
    original = dict(load_config())
    try:
        resp = _set_app_title(client, "우리정형외과 예약")
        assert resp.status_code == 200, resp.text
        # 응답 본문(out)에도 즉시 반영
        assert resp.json().get("app_title") == "우리정형외과 예약"
        # 재조회로도 영속 확인
        assert client.get("/api/config").json()["app_title"] == "우리정형외과 예약"
    finally:
        save_config(original)


def test_post_app_title_empty_falls_back_to_default(client):
    """빈 문자열/공백만 저장하면 기본값으로 복원된다."""
    original = dict(load_config())
    try:
        assert _set_app_title(client, "   ").status_code == 200
        assert client.get("/api/config").json()["app_title"] == DEFAULT_TITLE
    finally:
        save_config(original)


def test_post_app_title_truncated_to_40_chars(client):
    """40자를 넘는 이름은 40자로 잘린다 (헤더 레이아웃 보호)."""
    original = dict(load_config())
    try:
        long_name = "가" * 50
        assert _set_app_title(client, long_name).status_code == 200
        stored = client.get("/api/config").json()["app_title"]
        assert stored == "가" * 40
        assert len(stored) == 40
    finally:
        save_config(original)


def test_post_app_title_does_not_touch_sync_secret(client):
    """app_title 저장이 다른 비밀값(sync_secret)을 건드리지 않는다."""
    original = dict(load_config())
    before = load_config().get("sync_secret")
    try:
        assert _set_app_title(client, "테스트병원").status_code == 200
        assert load_config().get("sync_secret") == before
    finally:
        save_config(original)


# ─────────────────────────────────────────────────────────
# 페이지 렌더 — 저장한 이름이 헤더/탭 제목(= 홈페이지 이름)에 반영
# ─────────────────────────────────────────────────────────


def test_page_renders_custom_app_title(client):
    """저장한 app_title 이 렌더된 HTML 의 <title> 와 헤더 brand 에 들어간다.

    setup.html 은 base.html 을 상속하며 title 블록을 오버라이드하지 않으므로
    두 위치 모두 app_title() 을 사용한다.
    """
    original = dict(load_config())
    try:
        assert _set_app_title(client, "튼튼병원 예약").status_code == 200
        html = client.get("/setup").text
        assert "<title>튼튼병원 예약</title>" in html, "브라우저 탭 제목에 커스텀 이름 미반영."
        assert "튼튼병원 예약" in html and "class=\"brand\"" in html, "헤더 brand 에 커스텀 이름 미반영."
        # 기본 하드코딩 문자열이 잔존하면 안 됨 (변수화가 실제로 적용됐는지)
        assert ">병원 예약 관리<" not in html or "튼튼병원 예약" in html
    finally:
        save_config(original)


def test_app_title_helper_normalizes(client):
    """pages._app_title 헬퍼가 None/공백을 기본값으로 처리한다."""
    from app.routers.pages import _app_title

    original = dict(load_config())
    try:
        cfg = dict(original)
        cfg["app_title"] = "  "
        save_config(cfg)
        assert _app_title() == DEFAULT_TITLE

        cfg["app_title"] = "마이클리닉"
        save_config(cfg)
        assert _app_title() == "마이클리닉"
    finally:
        save_config(original)
