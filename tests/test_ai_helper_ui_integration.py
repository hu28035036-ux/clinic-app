"""AI 도우미 UI 통합 — partial / CSS / JS 가 실제로 서빙되고 main.html 에 포함되는지 검증.

TestClient 로 GET / GET /static/css/_ai_helper.css / GET /static/js/ai_helper.js 호출.
회귀 검증 — 기존 탭 / 검색 / 캘린더 모두 보존.

격리 환경에서 첫 실행은 setup 화면이라 mode=main 강제 후 main.html 검증.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _ensure_main_mode():
    """격리 config.json 의 mode=null → main 으로 강제. config 직접 저장 (admin 인증 우회)."""
    from app.config import load_config, save_config
    cfg = load_config()
    if cfg.get("mode") != "main":
        cfg["mode"] = "main"
        save_config(cfg)
    yield


def test_main_html_includes_ai_helper(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    # AI 도우미 partial 마크업
    assert "ai-helper-card" in html
    assert "AI 예약 도우미" in html
    assert 'x-data="aiHelper"' in html
    # base.html 의 head block 으로 link / script 추가
    assert "_ai_helper.css" in html
    assert "ai_helper.js" in html
    # tab-reserve 안에 위치 확인 — partial 이 layout 위에 와야 함
    helper_idx = html.find("ai-helper-card")
    layout_idx = html.find('class="layout"')
    assert helper_idx > 0 and layout_idx > 0
    assert helper_idx < layout_idx


def test_ai_helper_css_served(client):
    r = client.get("/static/css/_ai_helper.css")
    assert r.status_code == 200
    css = r.text
    # 디자인 토큰 변수 (Phase E 정책 변경 후 — 토큰명 보존, 값은 app.css 에 alias)
    assert "--ai-helper-primary" in css
    assert "var(--primary" in css  # Phase E: 그린 hardcoded → app.css 단일 원천 alias
    assert ".ai-helper-card" in css
    assert ".ai-helper-btn--primary" in css


def test_ai_helper_js_served(client):
    r = client.get("/static/js/ai_helper.js")
    assert r.status_code == 200
    js = r.text
    assert "window.aiHelper" in js
    assert "onParse" in js
    assert "onSelectPatient" in js
    assert "onApprove" in js
    assert "onReject" in js
    assert "/api/ai/commands/parse" in js
    assert "/api/ai/commands/" in js
    assert "X-Admin-Token" in js
    assert "dosu_admin_token" in js  # 기존 토큰 키 정합


def test_existing_tabs_preserved(client):
    """기존 탭 이름 / 메뉴 / 기능 변경 ⊥ (§ 16.2)."""
    r = client.get("/")
    html = r.text
    # 기존 탭 모두 보존 (v1.3.5+ 사용자 요청으로 tab-ai-manual 만 UI 제거)
    assert "switchTab('tab-reserve'" in html
    assert "switchTab('tab-patients'" in html
    assert "switchTab('tab-therapists'" in html
    assert "switchTab('tab-sms'" in html
    # tab-ai-manual (RAG 매뉴얼 Q&A) — UI 제거, 백엔드 보존
    assert "switchTab('tab-ai-manual'" not in html
    assert "askManualQa" not in html
    # 기존 캘린더 / 검색 보존
    assert 'id="day-board"' in html
    assert "patient-quick-search" in html
    # AI 도우미는 *전용 탭 ⊥* — switchTab 으로 추가된 탭 없음
    assert "switchTab('tab-ai-helper'" not in html
    assert "switchTab('tab-ai-commands'" not in html


def test_main_html_does_not_change_existing_styles(client):
    """기존 app.css 가 정상 로드 + main.html 의 기존 markup 변동 ⊥."""
    r = client.get("/")
    html = r.text
    assert "/static/css/app.css" in html
    # 사이드바 / 신규환자 버튼 / 범례 모두 보존
    assert "openNewPatientForReservation" in html
    assert "▤ 금일 예약 환자" in html
    assert "▣ 예약 현황" in html
