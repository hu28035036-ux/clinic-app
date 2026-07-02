"""집계 자동화 (v1.3.37+) — 치료완료(예약) + 기록 자동 집계.

검증:
  1. '기록 필요'가 아닌 치료항목: approved 예약이 집계에 자동 반영.
  2. manual_counts 는 자동값 위에 더하는 '수동 보정 델타'.
  3. '기록 필요' 치료항목: 기록 탭에 등장하고 record_entries 가 집계에 자동 반영.
  4. 합산 집계 (v1.3.51+): 기록필요 항목은 approved 예약 건수와 기록 건수가
     **합산**되어 집계에 반영된다 (기존 '경로 분리' 정책 폐지).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import models


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


def _make_category(client) -> dict:
    resp = client.post("/api/employee-categories", json={
        "name": _unique("agg-cat"),
        "color": "#2563EB",
        "active": True,
        "sort_order": 90,
        "default_can_doctor_treatment": False,
        "default_can_manual": True,
        "default_can_eswt": False,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_treatment(client, headers, category_id, *, requires_record=False) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post("/api/treatments", json={
        "name": f"agg-tx-{suffix}",
        "short": f"A{suffix[:7]}",
        "category_id": category_id,
        "default_minutes": 30,
        "role": "therapist",
        "count_increment": 1,
        "show_in_patient": False,
        "active": True,
        "sort_order": 10,
        "code": f"agg_{suffix}",
        "price": 50000,
        "requires_record": requires_record,
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_employee(client, category_id) -> dict:
    resp = client.post("/api/employees", json={
        "name": _unique("agg-emp"),
        "category_id": category_id,
        "color": "#10B981",
        "active": True,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _add_approved_appt(therapist_id, codes, start):
    from tests.harness.seed_data import get_test_patient_id

    pid = get_test_patient_id("홍길동테스트")
    db = SessionLocal()
    try:
        obj = models.Appointment(
            patient_id=pid,
            therapist_id=therapist_id,
            start_at=start,
            end_at=start + timedelta(minutes=30),
            duration_min=30,
            treatment_codes=json.dumps(codes),
            status="approved",
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj.id
    finally:
        db.close()


def _agg_cell(client, category_id, date, employee_id):
    resp = client.get(
        f"/api/stats/direct-aggregate?date_from={date}&date_to={date}&category_id={category_id}"
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["items"][0]["employee_data"][employee_id]


def test_approved_appointment_auto_aggregates_with_manual_delta(client):
    headers = _admin_headers(client)
    cat = _make_category(client)
    tx = _make_treatment(client, headers, cat["id"])
    emp = _make_employee(client, cat["id"])
    _add_approved_appt(emp["id"], [tx["code"]], datetime(2099, 9, 1, 10, 0))

    cell = _agg_cell(client, cat["id"], "2099-09-01", emp["id"])
    assert cell["auto"][tx["code"]] == 1
    assert cell["manual"][tx["code"]] == 0
    assert cell["counts"][tx["code"]] == 1

    # 수동 보정(walk-in) — manual_counts 는 자동값 위에 더해진다.
    mc = client.post("/api/manual-counts", json={
        "date": "2099-09-01",
        "therapist_id": emp["id"],
        "treatment_code": tx["code"],
        "count": 2,
    })
    assert mc.status_code == 200, mc.text

    cell2 = _agg_cell(client, cat["id"], "2099-09-01", emp["id"])
    assert cell2["auto"][tx["code"]] == 1
    assert cell2["manual"][tx["code"]] == 2
    assert cell2["counts"][tx["code"]] == 3


def test_record_required_treatment_sums_records_and_appointments(client):
    headers = _admin_headers(client)
    cat = _make_category(client)
    rec_tx = _make_treatment(client, headers, cat["id"], requires_record=True)
    emp = _make_employee(client, cat["id"])

    # 기록 탭에 등장.
    rec = client.get("/api/records?record_date=2099-09-02").json()
    assert any(t["tab_key"] == rec_tx["code"] for t in rec["tabs"])

    # 기록 입력.
    created = client.post("/api/records/entries", json={
        "tab_key": rec_tx["code"],
        "record_date": "2099-09-02",
        "chart_no": "C1",
        "patient_name": "기록환자",
        "employee_id": emp["id"],
    })
    assert created.status_code == 200, created.text

    # 합산 (v1.3.51+): 같은 코드의 approved 예약이 있으면 기록 건수와 합산된다.
    _add_approved_appt(emp["id"], [rec_tx["code"]], datetime(2099, 9, 2, 10, 0))

    cell = _agg_cell(client, cat["id"], "2099-09-02", emp["id"])
    assert cell["auto"][rec_tx["code"]] == 2  # 기록 1 + 치료완료 예약 1
    assert cell["counts"][rec_tx["code"]] == 2


def test_record_required_treatment_not_counted_as_manual_therapy(client):
    """role=therapist 라도 requires_record 면 도수치료(manual_treatments)에서 제외."""
    headers = _admin_headers(client)
    cat = _make_category(client)
    rec_tx = _make_treatment(client, headers, cat["id"], requires_record=True)
    plain_tx = _make_treatment(client, headers, cat["id"], requires_record=False)

    meta = client.get("/api/treatment-meta").json()
    # 기록필요 항목은 도수치료가 아님 — 통계/B-2 한도 오집계 방지.
    assert rec_tx["code"] not in meta["manual_treatments"]
    assert rec_tx["code"] in meta["record_treatments"]
    # 일반 치료사 항목은 그대로 도수치료.
    assert plain_tx["code"] in meta["manual_treatments"]
    assert plain_tx["code"] not in meta["record_treatments"]
