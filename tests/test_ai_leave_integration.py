"""AI 휴무 도우미 (Phase 8 ai_leave + commands router) 통합 테스트.

검증:
- POST /api/ai/commands/parse 에 휴무 키워드 → run_leave_pipeline 분기
- 결과 dict 의 intent="create_leave"
- approve → execute_approved_leave → 실제 EmployeeLeave INSERT
- main.html 에 _ai_leave_helper partial 포함
- ai_leave_helper.js 서빙
"""
from __future__ import annotations

import pytest

from app.database import SessionLocal
from app.models import models


def _admin_token(client) -> str:
    r = client.post("/api/admin/login", json={"password": "admin1234"})
    assert r.status_code == 200, r.text
    return r.json().get("token", "")


@pytest.fixture
def seeded(client):
    db = SessionLocal()
    try:
        for eid, name in [
            ("leave-e1", "박치료사휴무"),
            ("leave-e2", "김치료사휴무"),
        ]:
            if not db.query(models.Employee).filter_by(id=eid).first():
                db.add(models.Employee(
                    id=eid, name=name, role="therapist",
                    color="#9CA3AF", active=True,
                ))
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        # 본 테스트가 만든 휴무 row 정리
        db.query(models.EmployeeLeave).filter(
            models.EmployeeLeave.employee_id.in_(["leave-e1", "leave-e2"])
        ).delete(synchronize_session=False)
        for eid in ["leave-e1", "leave-e2"]:
            db.query(models.Employee).filter_by(id=eid).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _ensure_main_mode():
    from app.config import load_config, save_config
    cfg = load_config()
    if cfg.get("mode") != "main":
        cfg["mode"] = "main"
        save_config(cfg)
    yield


# ────────────────────────────── parse — leave intent 자동 분기 ──────────────────────────────


def test_parse_leave_full(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박치료사휴무 5월 30일 종일 휴무", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["result"]["intent"] == "create_leave"
    assert body["result"]["leave_type"] == "full"
    assert body["result"]["leave_date"] == "2026-05-30"
    assert body["result"]["therapist_id"] == "leave-e1"
    assert body["result"]["status"] in ("needs_approval", "validation_failed")


def test_parse_leave_am(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박치료사휴무 5월 30일 오전반차", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    body = r.json()
    assert body["result"]["leave_type"] == "am"


def test_parse_leave_pm(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박치료사휴무 5월 30일 오후반차", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    body = r.json()
    assert body["result"]["leave_type"] == "pm"


def test_parse_leave_unknown_therapist(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "없는치료사xyz 5월 30일 종일 휴무", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    body = r.json()
    assert body["result"]["therapist_not_found"] is True
    assert body["result"]["status"] == "needs_clarification"


# ────────────────────────────── approve — EmployeeLeave INSERT ──────────────────────────────


def test_approve_leave_inserts_row(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박치료사휴무 5월 30일 종일 휴무", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    assert r.json()["result"]["status"] == "needs_approval"

    db = SessionLocal()
    try:
        before = db.query(models.EmployeeLeave).filter_by(
            employee_id="leave-e1", leave_date="2026-05-30"
        ).count()
    finally:
        db.close()

    r2 = client.post(
        f"/api/ai/commands/{cmd_id}/approve",
        json={"memo": "통합 테스트"},
        headers={"X-Admin-Token": token},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["ok"] is True, body
    assert body["execution_status"] == "executed"
    assert body["result_payload"].get("leave_date") == "2026-05-30"

    db = SessionLocal()
    try:
        after = db.query(models.EmployeeLeave).filter_by(
            employee_id="leave-e1", leave_date="2026-05-30"
        ).count()
    finally:
        db.close()
    assert after == before + 1


def test_approve_leave_blocks_when_unknown_therapist(client, seeded):
    """v1.3.5+ 정책 갱신: stored-state 게이트가 *parsed/validation_failed* 등
    needs_approval 아닌 상태에서 approve 호출 시 409 차단 (Codex HIGH fix).

    기존엔 200 + ok=false (필드 누락 검증) 으로 차단됐으나, 새 게이트는 *더 일찍 차단*.
    AI_SAFETY_POLICY § 1.1.6 (휴무 승인 우회) 정합.
    """
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "없는치료사xyz 5월 30일 종일 휴무", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    r2 = client.post(
        f"/api/ai/commands/{cmd_id}/approve",
        json={},
        headers={"X-Admin-Token": token},
    )
    # v1.3.5+: 409 차단 (stored-state 가 needs_approval 아님)
    assert r2.status_code == 409, r2.text
    assert "needs_approval" in r2.text or "approve" in r2.text


# ────────────────────────────── UI 통합 ──────────────────────────────


def test_main_html_includes_ai_leave_helper(client):
    r = client.get("/")
    html = r.text
    assert "ai-leave-helper-card" in html
    assert "AI 휴무 도우미" in html
    assert 'x-data="aiLeaveHelper"' in html
    # 기존 RAG 카드도 보존
    assert 'id="ai-leave-card"' in html
    assert "✨ AI 휴무 등록" in html
    # 새 카드가 기존 카드 *위에* 위치
    helper_idx = html.find("ai-leave-helper-card")
    legacy_idx = html.find('id="ai-leave-card"')
    assert helper_idx > 0 and legacy_idx > 0
    assert helper_idx < legacy_idx


def test_ai_leave_helper_js_served(client):
    r = client.get("/static/js/ai_leave_helper.js")
    assert r.status_code == 200
    js = r.text
    assert "window.aiLeaveHelper" in js
    assert "/api/ai/commands/parse" in js
    assert "/api/ai/commands/" in js  # approve / reject endpoint
