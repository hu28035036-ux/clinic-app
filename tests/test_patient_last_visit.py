"""환자관리 탭 성능/버그 수정 회귀 테스트.

검증 범위:
  1. GET /api/patients/search 의 각 item 에 ``last_visit`` 키가 포함된다
     (전체 last-appointments 맵을 받지 않고 페이지 단위로 계산).
  2. POST /api/patients/by-ids 는 **존재하는 환자만** 반환한다 — 삭제된
     환자가 브라우저 최근목록에 남는 버그를 서버 기준으로 정리하기 위한 계약.
  3. by-ids 의 last_visit 는 취소 제외 마지막 예약을 반영한다.
"""
from __future__ import annotations

from datetime import datetime

from tests.harness.helpers import cancel_appointment, make_appointment


def _new_patient(client, name: str, chart_no: str) -> str:
    resp = client.post("/api/patients", json={"name": name, "chart_no": chart_no})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _first_treatment_code(client) -> str:
    rows = client.get("/api/treatments").json()
    assert rows, "시드 치료항목이 있어야 함"
    return rows[0]["code"]


def test_search_items_include_last_visit(client):
    """검색 응답 item 에 last_visit 키가 있어야 한다 (envelope 6키는 유지)."""
    resp = client.get("/api/patients/search?q=테스트&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"items", "total", "limit", "offset", "q", "has_more"}
    for item in body["items"]:
        assert "last_visit" in item


def test_by_ids_returns_only_existing(client):
    """by-ids 는 존재하는 ID 만 반환 — 없는 ID 는 제외 (삭제 환자 정리 계약)."""
    pid = _new_patient(client, "최근목록테스트A", "LVTEST-A")
    resp = client.post(
        "/api/patients/by-ids",
        json={"ids": [pid, "nonexistent-id-xxxxxxxxxxxxxxxx"]},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    returned = {it["id"] for it in items}
    assert returned == {pid}
    assert "last_visit" in items[0]
    assert items[0]["last_visit"] is None  # 예약 없음


def test_by_ids_empty_input(client):
    resp = client.post("/api/patients/by-ids", json={"ids": []})
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_by_ids_excludes_deleted_patient(client):
    """삭제된 환자는 by-ids 결과에서 빠진다 — 최근목록 잔존 버그의 핵심 수정."""
    pid = _new_patient(client, "최근목록테스트삭제", "LVTEST-DEL")
    # 존재 확인
    assert {it["id"] for it in client.post(
        "/api/patients/by-ids", json={"ids": [pid]}).json()["items"]} == {pid}

    token = client.post("/api/admin/login", json={"password": "admin1234"}).json()["token"]
    dresp = client.delete(f"/api/patients/{pid}", headers={"X-Admin-Token": token})
    assert dresp.status_code == 200, dresp.text

    # 삭제 후엔 by-ids 가 비어 있어야 함
    items = client.post("/api/patients/by-ids", json={"ids": [pid]}).json()["items"]
    assert items == []


def test_by_ids_last_visit_reflects_appointment_and_cancel(client):
    """last_visit = 취소 제외 마지막 예약. 취소하면 다시 None."""
    pid = _new_patient(client, "마지막예약테스트", "LVTEST-APPT")
    code = _first_treatment_code(client)
    start = datetime(2026, 5, 20, 10, 0, 0)
    r = make_appointment(client, patient_id=pid, start_at=start, treatment_codes=[code])
    assert r.status_code == 200, r.text
    appt_id = r.json()["id"]

    items = client.post("/api/patients/by-ids", json={"ids": [pid]}).json()["items"]
    assert items[0]["last_visit"] is not None
    assert items[0]["last_visit"].startswith("2026-05-20")

    # 취소하면 last_visit 에서 제외되어 None
    cresp = cancel_appointment(client, appt_id)
    assert cresp.status_code == 200, cresp.text
    items = client.post("/api/patients/by-ids", json={"ids": [pid]}).json()["items"]
    assert items[0]["last_visit"] is None
