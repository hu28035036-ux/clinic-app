"""Phase 12 (Post-Phase 11) — SSOT § 11 commands router 통합 테스트.

검증:
- 7 endpoint 모두 동작 (parse / select-patient / select-treatment / approve / reject / GET / logs)
- 인증 (X-Admin-Token) 강제
- DB 직접 수정 0 (parse / select / get / logs / reject)
- approve 만 실제 service 호출 → DB 변경
- audit log 단계별 갱신
- AI 응답에 PII 외부 전송 ⊥
"""
from __future__ import annotations

import pytest

from app.database import SessionLocal
from app.models import models


def _admin_token(client) -> str:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return resp.json().get("token", "")


@pytest.fixture
def seeded(client):
    """테스트용 환자 / 치료사 / 치료항목 + alias 시드 (멱등)."""
    db = SessionLocal()
    try:
        for pid, name, chart, birth, phone in [
            ("cmd-p1", "박환자", "88001", "1980-04-15", "010-1111-2222"),
            ("cmd-p2", "박환자", "88002", "1975-09-02", "010-3333-4444"),
        ]:
            if not db.query(models.Patient).filter_by(id=pid).first():
                db.add(models.Patient(
                    id=pid, name=name, chart_no=chart,
                    birth_date=birth, phone=phone,
                ))
        for eid, name in [("cmd-e1", "박치료사")]:
            if not db.query(models.Employee).filter_by(id=eid).first():
                db.add(models.Employee(
                    id=eid, name=name, role="therapist",
                    color="#9CA3AF", active=True,
                ))
        db.commit()
        # alias 시드 — manual30 / eswt 에 표준 alias
        from sqlalchemy import text
        manual30 = db.query(models.Treatment).filter_by(code="manual30").first()
        if manual30:
            for alias in ["도수30", "도30"]:
                try:
                    db.execute(
                        text(
                            "INSERT INTO treatment_aliases (treatment_id, alias_name) "
                            "VALUES (:tid, :alias) ON CONFLICT(treatment_id, alias_name) DO NOTHING"
                        ),
                        {"tid": manual30.id, "alias": alias},
                    )
                except Exception:  # noqa: BLE001
                    pass
            db.commit()
    finally:
        db.close()
    yield
    # 정리
    db = SessionLocal()
    try:
        for pid in ["cmd-p1", "cmd-p2"]:
            db.query(models.Patient).filter_by(id=pid).delete()
        for eid in ["cmd-e1"]:
            db.query(models.Employee).filter_by(id=eid).delete()
        db.commit()
    finally:
        db.close()


# ────────────────────────────── 인증 ──────────────────────────────


def test_commands_parse_works_without_admin_token(client):
    """정책 변경 (v1.3.5+): 일반 사용자도 AI 예약 도우미 사용 가능 — 인증 없으면 anonymous."""
    resp = client.post("/api/ai/commands/parse", json={"raw_text": "테스트"})
    # 401 ❌ — 200 또는 422 (validation) 이지만 인증 거부 ❌
    assert resp.status_code != 401, (
        "AI commands parse 가 401 반환 — 일반 사용자 흐름이 깨졌다. "
        "ai_commands_router.get_actor_user_id 가 토큰 없을 때 anonymous 반환하는지 확인."
    )


def test_commands_parse_rejects_invalid_token(client):
    """토큰 *있는데* invalid → 401 (만료 토큰 silent ignore ❌, 보안)."""
    resp = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "테스트"},
        headers={"X-Admin-Token": "invalid-token-deadbeef"},
    )
    assert resp.status_code == 401


def test_commands_logs_requires_admin(client):
    """전체 로그 조회는 *관리자 전용* 유지 — 인증 정책 변경 영향 ⊥."""
    resp = client.get("/api/ai/commands/logs")
    assert resp.status_code == 401


# ────────────────────────────── parse ──────────────────────────────


def test_commands_parse_returns_command_id(client, seeded):
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/commands/parse",
        json={
            "raw_text": "차트번호 88001 5월30일 9시 박치료사 도수30 예약",
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert isinstance(body["command_id"], int)
    assert body["result"]["status"] in (
        "needs_approval", "validation_failed", "patient_not_found",
        "treatment_selection_required", "treatment_alias_conflict",
    )
    assert body["diagnostics"]["privacy"]["ok"] is True


def test_commands_parse_homonym_status(client, seeded):
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/commands/parse",
        json={
            "raw_text": "박환자 5월30일 9시 박치료사 도수30 예약",
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["status"] == "patient_selection_required"
    assert body["result"]["selected_patient"] is None


# ────────────────────────────── select-patient ──────────────────────────────


def test_commands_select_patient(client, seeded):
    token = _admin_token(client)
    # parse
    r = client.post(
        "/api/ai/commands/parse",
        json={
            "raw_text": "박환자 5월30일 9시 박치료사 도수30 예약",
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    # select cmd-p2
    r2 = client.post(
        f"/api/ai/commands/{cmd_id}/select-patient",
        json={"patient_id": "cmd-p2"},
        headers={"X-Admin-Token": token},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["ok"] is True
    assert body["result"]["selected_patient"]["patient_id"] == "cmd-p2"


def test_commands_select_patient_not_found_command(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/9999999/select-patient",
        json={"patient_id": "cmd-p1"},
        headers={"X-Admin-Token": token},
    )
    assert r.status_code == 404


# ────────────────────────────── select-treatment ──────────────────────────────


def test_commands_select_treatment(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={
            "raw_text": "차트번호 88001 5월30일 9시 박치료사 도수30 예약",
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    r2 = client.post(
        f"/api/ai/commands/{cmd_id}/select-treatment",
        json={"items": [{"raw_text": "도수30", "treatment_id": "manual30"}]},
        headers={"X-Admin-Token": token},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["ok"] is True


# ────────────────────────────── reject ──────────────────────────────


def test_commands_reject(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={
            "raw_text": "차트번호 88001 5월30일 9시 박치료사 도수30 예약",
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    r2 = client.post(
        f"/api/ai/commands/{cmd_id}/reject",
        json={"reason": "환자 거부"},
        headers={"X-Admin-Token": token},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["row"]["status"] == "rejected"


# ────────────────────────────── GET command ──────────────────────────────


def test_commands_get(client, seeded):
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={
            "raw_text": "차트번호 88001 5월30일 9시 박치료사 도수30 예약",
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    r2 = client.get(
        f"/api/ai/commands/{cmd_id}",
        headers={"X-Admin-Token": token},
    )
    assert r2.status_code == 200
    assert r2.json()["row"]["id"] == cmd_id


def test_commands_get_not_found(client, seeded):
    token = _admin_token(client)
    r = client.get(
        "/api/ai/commands/9999999",
        headers={"X-Admin-Token": token},
    )
    assert r.status_code == 404


# ────────────────────────────── GET logs ──────────────────────────────


def test_commands_logs_returns_recent(client, seeded):
    token = _admin_token(client)
    # parse 2건 생성
    for _ in range(2):
        client.post(
            "/api/ai/commands/parse",
            json={"raw_text": "박환자 5월30일 9시 도수30 예약", "today_iso": "2026-05-01"},
            headers={"X-Admin-Token": token},
        )
    r = client.get(
        "/api/ai/commands/logs?limit=10",
        headers={"X-Admin-Token": token},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["count"] >= 2


def test_commands_logs_filter_by_intent(client, seeded):
    token = _admin_token(client)
    client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박환자 5월30일 9시 도수30 예약", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    r = client.get(
        "/api/ai/commands/logs?intent=create_appointment&limit=5",
        headers={"X-Admin-Token": token},
    )
    assert r.status_code == 200
    body = r.json()
    for row in body["rows"]:
        assert row["intent"] == "create_appointment"


# ────────────────────────────── approve (실제 service 호출) ──────────────────────────────


def test_commands_approve_blocks_when_status_not_needs_approval(client, seeded):
    """동명이인 → 선택 안 한 상태에서 approve 시도 → 차단."""
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박환자 5월30일 9시 박치료사 도수30 예약", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    # selected 안 함 → patient_selection_required
    r2 = client.post(
        f"/api/ai/commands/{cmd_id}/approve",
        json={},
        headers={"X-Admin-Token": token},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["ok"] is False
    assert body["error"] == "approval_blocked"


def test_commands_approve_blocks_after_reject(client, seeded):
    """v1.3.5+ Codex HIGH fix: rejected 된 명령을 다시 approve 호출 시 409 차단.

    AI_SAFETY_POLICY § 1.1.3-1.1.7 (사용자 승인 우회 ❌) 정합.
    """
    token = _admin_token(client)
    # parse → reject → 다시 approve 시도
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박환자 5월30일 9시 박치료사 도수30 예약", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    rj = client.post(
        f"/api/ai/commands/{cmd_id}/reject",
        json={"reason": "테스트 거절"},
        headers={"X-Admin-Token": token},
    )
    assert rj.status_code == 200, rj.text
    # rejected 상태에서 approve → 409
    ra = client.post(
        f"/api/ai/commands/{cmd_id}/approve",
        json={},
        headers={"X-Admin-Token": token},
    )
    assert ra.status_code == 409, ra.text
    assert "종결" in ra.text or "rejected" in ra.text


def test_commands_approve_blocks_double_approve(client, seeded):
    """v1.3.5+ Codex HIGH fix: 같은 command 의 *연속 approve* 호출 차단.

    첫 approve 가 executed 로 종결되면 두 번째 호출은 409 — 중복 등록 방지.
    이 테스트는 *종결 상태 검증* 만 — 실제 첫 approve 의 성공 여부와 무관 (parse 결과가
    needs_approval 이 아닐 수도 있어 첫 호출은 approval_blocked 일 수 있음).
    """
    token = _admin_token(client)
    # 직접 audit row 를 executed 로 만들어 stored-state 게이트만 검증
    import sqlite3

    from app.config import get_db_path
    conn = sqlite3.connect(str(get_db_path()))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ai_command_logs (raw_text, intent, status) VALUES (?, ?, ?)",
        ("테스트 executed 명령", "create_appointment", "executed"),
    )
    cmd_id = cur.lastrowid
    conn.commit()
    conn.close()
    # executed 상태에서 approve → 409
    ra = client.post(
        f"/api/ai/commands/{cmd_id}/approve",
        json={},
        headers={"X-Admin-Token": token},
    )
    assert ra.status_code == 409, ra.text
    assert "executed" in ra.text or "종결" in ra.text


def test_commands_approve_leave_blocks_when_status_not_needs_approval(client, seeded):
    """v1.3.5+ Codex 추가 HIGH fix: create_leave approve 는 needs_approval 만.

    parsed / validation_failed / patient_selection_required 같은 비종결 상태에서
    필드만 채워졌다고 실행되면 AI_SAFETY_POLICY § 1.1.6 (휴무 승인 우회) 위반.
    """
    import sqlite3

    from app.config import get_db_path
    conn = sqlite3.connect(str(get_db_path()))
    cur = conn.cursor()
    # parsed 상태의 create_leave row 직접 삽입 (resolved_json 채워둠)
    import json as _json
    resolved = _json.dumps({
        "leave_type": "full",
        "leave_date": "2026-06-01",
        "therapist_id": "cmd-e1",
    }, ensure_ascii=False)
    cur.execute(
        "INSERT INTO ai_command_logs (raw_text, intent, status, resolved_json) "
        "VALUES (?, ?, ?, ?)",
        ("박치료사 6월1일 휴무", "create_leave", "parsed", resolved),
    )
    cmd_id = cur.lastrowid
    conn.commit()
    conn.close()
    token = _admin_token(client)
    r = client.post(
        f"/api/ai/commands/{cmd_id}/approve",
        json={},
        headers={"X-Admin-Token": token},
    )
    assert r.status_code == 409, r.text
    assert "needs_approval" in r.text or "parsed" in r.text


def test_commands_approve_unsupported_intent_blocked(client, seeded):
    """update / cancel 등 다른 intent 의 approve 는 향후 (현재 차단)."""
    token = _admin_token(client)
    r = client.post(
        "/api/ai/commands/parse",
        json={"raw_text": "박환자 내일 9시 예약 취소", "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )
    cmd_id = r.json()["command_id"]
    r2 = client.post(
        f"/api/ai/commands/{cmd_id}/approve",
        json={},
        headers={"X-Admin-Token": token},
    )
    assert r2.status_code == 400  # 향후 지원


# ────────────────────────────── DB 직접 수정 0 (parse 단계) ──────────────────────────────


def test_commands_parse_does_not_modify_appointments(client, seeded):
    """parse 호출은 ai_command_logs row 만 추가하고 Appointment / Patient 는 변동 0."""
    db = SessionLocal()
    try:
        before_a = db.query(models.Appointment).count()
        before_p = db.query(models.Patient).count()
    finally:
        db.close()

    token = _admin_token(client)
    for _ in range(3):
        client.post(
            "/api/ai/commands/parse",
            json={"raw_text": "박환자 5월30일 9시 도수30 예약", "today_iso": "2026-05-01"},
            headers={"X-Admin-Token": token},
        )

    db = SessionLocal()
    try:
        after_a = db.query(models.Appointment).count()
        after_p = db.query(models.Patient).count()
    finally:
        db.close()
    assert before_a == after_a, "parse 가 Appointment INSERT 했음"
    assert before_p == after_p, "parse 가 Patient INSERT 했음"
