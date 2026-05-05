"""Phase 6 — POST /api/ai/harness/run (관리자 전용) Runtime Test.

검증 항목:
- 관리자 토큰 없이 호출 → 401
- 관리자 토큰 있으면 정상 응답
- raw_text 누락 → 422 (FastAPI 자동 검증)
- 정상 명령 (시드 환자 / 시드 치료사 / 시드 치료항목 활용) → status / parsed / preview 반환
- privacy / hallucination diagnostics 포함
- DB 직접 수정 0 — 호출 전후 row 수 동일
- 알 수 없는 환자명 → patient_not_found + new_patient_proposal
- 동명이인 → patient_selection_required
- selected_patient_id 명시 → 동명이인 중 선택 → validation 통과
- 외부 AI API 호출 0 (정규식 fallback)
"""
from __future__ import annotations

import pytest

from app.database import SessionLocal
from app.models import models

# ────────────────────────────── 시드 / 토큰 ──────────────────────────────


def _admin_token(client) -> str:
    """관리자 로그인 토큰 (테스트 시드 비번 admin1234)."""
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json().get("token", "")


@pytest.fixture
def seeded(client):
    """harness Runtime Test 용 시드 — 환자 / 치료사 / 치료항목 / alias.

    conftest 의 seed_data 가 이미 일부 환자 / 직원 / 휴무를 시드하므로,
    본 fixture 는 본 테스트가 의존하는 row 만 멱등 추가.
    """
    db = SessionLocal()
    try:
        # 환자 — 박환자 동명이인 2명, 김민수 1명 (chart 충돌 회피)
        for pid, name, chart, birth, phone in [
            ("ph-test-1", "박환자테스트", "99001", "1980-04-15", "010-1111-2222"),
            ("ph-test-2", "박환자테스트", "99002", "1975-09-02", "010-3333-4444"),
            ("ph-test-3", "김민수테스트", "99003", "1990-01-01", "010-5555-6666"),
        ]:
            if not db.query(models.Patient).filter_by(id=pid).first():
                db.add(
                    models.Patient(
                        id=pid, name=name, chart_no=chart,
                        birth_date=birth, phone=phone,
                    )
                )
        # 치료사
        for eid, name in [("therap-test-1", "박치료사테스트"), ("therap-test-2", "김치료사테스트")]:
            if not db.query(models.Employee).filter_by(id=eid).first():
                db.add(
                    models.Employee(
                        id=eid, name=name, role="therapist",
                        color="#9CA3AF", active=True,
                    )
                )
        db.commit()
        # 시드된 manual30 / eswt 에 표준 alias 멱등 추가 — m020 마이그레이션이 테이블 만들어둠
        from sqlalchemy import text
        manual30 = db.query(models.Treatment).filter_by(code="manual30").first()
        eswt = db.query(models.Treatment).filter_by(code="eswt").first()
        alias_pairs = []
        if manual30:
            alias_pairs += [(manual30.id, "도수30"), (manual30.id, "도30")]
        if eswt:
            alias_pairs += [(eswt.id, "ESWT"), (eswt.id, "체외")]
        for tid, alias in alias_pairs:
            try:
                db.execute(
                    text(
                        "INSERT INTO treatment_aliases (treatment_id, alias_name) "
                        "VALUES (:tid, :alias) ON CONFLICT(treatment_id, alias_name) DO NOTHING"
                    ),
                    {"tid": tid, "alias": alias},
                )
            except Exception:  # noqa: BLE001
                # ON CONFLICT 미지원 시 무시 (멱등 try)
                pass
        db.commit()
    finally:
        db.close()
    yield
    # 정리 — 본 테스트가 추가한 row / alias 만 제거 (시드된 manual30 / eswt 자체는 유지)
    db = SessionLocal()
    try:
        for pid in ["ph-test-1", "ph-test-2", "ph-test-3"]:
            db.query(models.Patient).filter_by(id=pid).delete()
        for eid in ["therap-test-1", "therap-test-2"]:
            db.query(models.Employee).filter_by(id=eid).delete()
        # alias 정리는 다른 테스트에 영향 없도록 본 테스트가 INSERT 한 것만 삭제
        from sqlalchemy import text
        manual30 = db.query(models.Treatment).filter_by(code="manual30").first()
        eswt = db.query(models.Treatment).filter_by(code="eswt").first()
        delete_pairs = []
        if manual30:
            delete_pairs += [(manual30.id, "도수30"), (manual30.id, "도30")]
        if eswt:
            delete_pairs += [(eswt.id, "ESWT"), (eswt.id, "체외")]
        for tid, alias in delete_pairs:
            db.execute(
                text("DELETE FROM treatment_aliases WHERE treatment_id=:tid AND alias_name=:alias"),
                {"tid": tid, "alias": alias},
            )
        db.commit()
    finally:
        db.close()


# ────────────────────────────── 인증 ──────────────────────────────


def test_harness_router_requires_admin_token(client):
    """토큰 없으면 401."""
    resp = client.post(
        "/api/ai/harness/run",
        json={"raw_text": "테스트"},
    )
    assert resp.status_code == 401


def test_harness_router_invalid_token_blocked(client):
    resp = client.post(
        "/api/ai/harness/run",
        json={"raw_text": "테스트"},
        headers={"X-Admin-Token": "invalid-xyz"},
    )
    assert resp.status_code == 401


# ────────────────────────────── 정상 호출 ──────────────────────────────


def test_harness_router_runs_with_admin_token(client, seeded):
    """관리자 토큰 + 시드 환자 → status / parsed / preview 반환."""
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/harness/run",
        json={
            "raw_text": "차트번호 99003 5월30일 9시 도수30 예약",
            "current_calendar_year": 2026,
            "current_calendar_month": 5,
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["result"]["status"] in (
        "needs_approval",
        "validation_failed",
        "patient_mismatch",
        "patient_not_found",
    )
    assert body["result"]["raw_text"].startswith("차트번호 99003")
    # 진단 결과 포함
    assert "diagnostics" in body
    assert "privacy" in body["diagnostics"]
    assert "hallucination" in body["diagnostics"]
    assert body["diagnostics"]["privacy"]["ok"] is True


def test_harness_router_chart_lookup_finds_patient(client, seeded):
    """차트번호 단일 환자 확정."""
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/harness/run",
        json={
            "raw_text": "차트번호 99003 5월30일 9시 도수30 예약",
            "current_calendar_year": 2026,
            "current_calendar_month": 5,
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    body = resp.json()
    assert body["ok"] is True
    assert body["result"]["selected_patient"] is not None
    assert body["result"]["selected_patient"]["chart_no"] == "99003"


def test_harness_router_homonym_returns_panel(client, seeded):
    """동명이인 박환자테스트 2명 → patient_selection_required."""
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/harness/run",
        json={
            "raw_text": "박환자테스트 5월30일 9시 도수30 예약",
            "current_calendar_year": 2026,
            "current_calendar_month": 5,
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["status"] == "patient_selection_required"
    assert body["result"]["selected_patient"] is None
    assert len(body["result"]["patient_resolution"]["candidates"]) == 2


def test_harness_router_homonym_with_selected_patient(client, seeded):
    """동명이인 + selected_patient_id 명시 → 확정."""
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/harness/run",
        json={
            "raw_text": "박환자테스트 5월30일 9시 도수30 예약",
            "current_calendar_year": 2026,
            "current_calendar_month": 5,
            "today_iso": "2026-05-01",
            "selected_patient_id": "ph-test-2",
        },
        headers={"X-Admin-Token": token},
    )
    body = resp.json()
    assert body["ok"] is True
    assert body["result"]["selected_patient"]["patient_id"] == "ph-test-2"
    assert body["result"]["validation"] is not None


def test_harness_router_unknown_patient_proposes_new(client):
    """검색 실패 환자 → patient_not_found + new_patient_proposal."""
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/harness/run",
        json={
            "raw_text": "절대로없는환자xyz 5월30일 9시 테도30 예약",
            "current_calendar_year": 2026,
            "current_calendar_month": 5,
            "today_iso": "2026-05-01",
        },
        headers={"X-Admin-Token": token},
    )
    body = resp.json()
    assert body["ok"] is True
    assert body["result"]["status"] == "patient_not_found"
    assert body["result"]["new_patient_proposal"] is not None
    # AI 가 생년월일 / 연락처 임의 생성 안 함
    assert body["result"]["new_patient_proposal"]["prefill"]["birth_date"] is None
    assert body["result"]["new_patient_proposal"]["prefill"]["phone"] is None


# ────────────────────────────── 안전 ──────────────────────────────


def test_harness_router_does_not_modify_db(client, seeded):
    """endpoint 호출 전후 Patient / Appointment row 수 동일."""
    token = _admin_token(client)
    db = SessionLocal()
    try:
        before_p = db.query(models.Patient).count()
        before_a = db.query(models.Appointment).count()
    finally:
        db.close()

    client.post(
        "/api/ai/harness/run",
        json={"raw_text": "차트번호 99003 5월30일 9시 도수30 예약",
              "today_iso": "2026-05-01"},
        headers={"X-Admin-Token": token},
    )

    db = SessionLocal()
    try:
        after_p = db.query(models.Patient).count()
        after_a = db.query(models.Appointment).count()
    finally:
        db.close()
    assert before_p == after_p
    assert before_a == after_a


def test_harness_router_validates_payload(client):
    """raw_text 누락 → 422."""
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/harness/run",
        json={},
        headers={"X-Admin-Token": token},
    )
    assert resp.status_code == 422


def test_harness_router_invalid_today_iso(client):
    """today_iso 형식 오류 → 400."""
    token = _admin_token(client)
    resp = client.post(
        "/api/ai/harness/run",
        json={"raw_text": "테스트", "today_iso": "2026/05/01"},
        headers={"X-Admin-Token": token},
    )
    assert resp.status_code == 400
