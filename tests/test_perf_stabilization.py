"""대량 데이터 안정화 — 신규 경량 엔드포인트 회귀.

목적: 예약 상세를 열 때 연간 전체 예약을 받아 JS 에서 find 하던 비효율을
``GET /api/appointments/{aid}`` 단건 조회로, 환자 수 배지를 위해 전체 환자를
light 로드하던 것을 ``GET /api/patients/count`` 로 대체한 변경의 회귀 보호.
"""
from __future__ import annotations

from datetime import datetime

from app.database import SessionLocal
from app.models import models
from tests.harness.helpers import make_appointment
from tests.harness.seed_data import get_test_patient_id


def test_get_appointment_by_id(client):
    """단건 예약 조회 — list_appointments 항목과 동일 shape(id/start/end/extendedProps)."""
    pid = get_test_patient_id("홍길동테스트")
    r = make_appointment(
        client, patient_id=pid, start_at=datetime(2026, 5, 27, 11, 30),
        treatment_codes=["manual30"],
    )
    assert r.status_code == 200, r.text
    aid = r.json()["id"]

    g = client.get(f"/api/appointments/{aid}")
    assert g.status_code == 200, g.text
    body = g.json()
    assert body["id"] == aid
    assert "start" in body and "end" in body
    assert body["extendedProps"]["patient_id"] == pid


def test_get_appointment_404(client):
    """없는 예약 id → 404 (연간 목록 fetch 대체 경로의 미존재 처리)."""
    g = client.get("/api/appointments/nonexistent-aid-xyz")
    assert g.status_code == 404


def test_patients_count_matches_db_and_route_order(client):
    """/patients/count 가 실제 COUNT 와 일치 + ``/patients/{pid}`` 보다 먼저 매칭됨.

    (라우트 순서가 틀리면 'count' 가 {pid} 로 잡혀 환자 조회 404 가 났을 것.)
    """
    get_test_patient_id("홍길동테스트")  # 최소 1명 시드
    r = client.get("/api/patients/count")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body.get("count"), int)

    db = SessionLocal()
    try:
        actual = db.query(models.Patient).count()
    finally:
        db.close()
    assert body["count"] == actual
    assert actual >= 1
