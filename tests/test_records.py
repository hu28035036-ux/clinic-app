from __future__ import annotations

import uuid

import pytest


@pytest.fixture(autouse=True)
def _ensure_main_mode():
    from app.config import load_config, save_config

    cfg = load_config()
    if cfg.get("mode") != "main":
        cfg["mode"] = "main"
        save_config(cfg)
    yield


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _make_category(client, name_prefix: str) -> dict:
    resp = client.post("/api/employee-categories", json={
        "name": _unique(name_prefix),
        "color": "#3B82F6",
        "active": True,
        "sort_order": 80,
        "default_can_doctor_treatment": False,
        "default_can_manual": True,
        "default_can_eswt": True,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_employee(client, category_id: str, name_prefix: str) -> dict:
    resp = client.post("/api/employees", json={
        "name": _unique(name_prefix),
        "category_id": category_id,
        "color": "#10B981",
        "active": True,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_records_tabs_settings_entries_and_counts(client):
    category = _make_category(client, "records-category")
    other_category = _make_category(client, "records-other-category")
    employee = _make_employee(client, category["id"], "records-employee")
    other_employee = _make_employee(client, other_category["id"], "records-other-employee")

    initial = client.get("/api/records")
    assert initial.status_code == 200, initial.text
    labels = {tab["tab_key"]: tab["label"] for tab in initial.json()["tabs"]}
    assert labels["manual"] == "메뉴얼"
    assert labels["carm"] == "C-Arm"
    assert labels["review_event"] == "리뷰이벤트"

    renamed = client.put("/api/records/tabs/manual", json={
        "label": "도수기록",
        "category_id": category["id"],
    })
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["label"] == "도수기록"
    assert renamed.json()["category_id"] == category["id"]

    created = client.post("/api/records/entries", json={
        "tab_key": "manual",
        "record_date": "2026-06-12",
        "chart_no": "1001",
        "patient_name": "홍길동",
        "employee_id": employee["id"],
    })
    assert created.status_code == 200, created.text
    created_id = created.json()["id"]

    updated = client.put(f"/api/records/entries/{created_id}", json={
        "record_date": "2026-06-12",
        "chart_no": "1001-수정",
        "patient_name": "홍길동수정",
        "employee_id": employee["id"],
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["chart_no"] == "1001-수정"
    assert updated.json()["patient_name"] == "홍길동수정"

    rejected_update = client.put(f"/api/records/entries/{created_id}", json={
        "record_date": "2026-06-12",
        "chart_no": "1001-수정",
        "patient_name": "홍길동수정",
        "employee_id": other_employee["id"],
    })
    assert rejected_update.status_code == 400
    assert "선택한 과의 직원만" in rejected_update.text

    review_created = client.post("/api/records/entries", json={
        "tab_key": "review_event",
        "record_date": "2026-06-12",
        "chart_no": "R1001",
        "patient_name": "리뷰환자",
        "employee_id": employee["id"],
    })
    assert review_created.status_code == 200, review_created.text

    rejected = client.post("/api/records/entries", json={
        "tab_key": "manual",
        "record_date": "2026-06-12",
        "chart_no": "1002",
        "patient_name": "김길동",
        "employee_id": other_employee["id"],
    })
    assert rejected.status_code == 400
    assert "선택한 과의 직원만" in rejected.text

    data = client.get("/api/records?record_date=2026-06-12").json()
    assert data["record_date"] == "2026-06-12"
    assert data["week_start"] == "2026-06-08"
    assert data["week_end"] == "2026-06-14"
    assert data["week_dates"] == [
        "2026-06-08", "2026-06-09", "2026-06-10", "2026-06-11",
        "2026-06-12", "2026-06-13", "2026-06-14",
    ]
    entries = [row for row in data["entries"] if row["tab_key"] == "manual"]
    assert any(row["chart_no"] == "1001-수정" and row["patient_name"] == "홍길동수정" for row in entries)
    review_entries = [row for row in data["entries"] if row["tab_key"] == "review_event"]
    assert any(row["chart_no"] == "R1001" and row["patient_name"] == "리뷰환자" for row in review_entries)
    assert data["counts"]["manual"][employee["id"]] == 1
    assert data["counts"]["review_event"][employee["id"]] == 1
    assert data["week_counts"]["manual"]["2026-06-12"] == 1
    assert data["week_counts"]["review_event"]["2026-06-12"] == 1
    assert other_employee["id"] not in data["counts"]["manual"]

    other_day = client.get("/api/records?record_date=2026-06-13").json()
    assert not [row for row in other_day["entries"] if row["tab_key"] == "manual"]
    assert employee["id"] not in other_day["counts"].get("manual", {})
    assert other_day["week_counts"]["manual"]["2026-06-12"] == 1


def test_main_html_has_records_subtab_shell(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "record-subtabs" in html
    assert "record-weekdays" in html
    assert "record-date" in html
    assert "record-chart-no" in html
    assert "record-patient-name" in html
    assert "record-employee" in html
    assert "record-counts" in html
