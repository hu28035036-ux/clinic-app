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

    renamed = client.put("/api/records/tabs/manual", json={
        "label": "도수기록",
        "category_id": category["id"],
    })
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["label"] == "도수기록"
    assert renamed.json()["category_id"] == category["id"]

    created = client.post("/api/records/entries", json={
        "tab_key": "manual",
        "chart_no": "1001",
        "patient_name": "홍길동",
        "employee_id": employee["id"],
    })
    assert created.status_code == 200, created.text

    rejected = client.post("/api/records/entries", json={
        "tab_key": "manual",
        "chart_no": "1002",
        "patient_name": "김길동",
        "employee_id": other_employee["id"],
    })
    assert rejected.status_code == 400
    assert "선택한 과의 직원만" in rejected.text

    data = client.get("/api/records").json()
    entries = [row for row in data["entries"] if row["tab_key"] == "manual"]
    assert any(row["chart_no"] == "1001" and row["patient_name"] == "홍길동" for row in entries)
    assert data["counts"]["manual"][employee["id"]] == 1
    assert other_employee["id"] not in data["counts"]["manual"]


def test_main_html_has_records_subtab_shell(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "record-subtabs" in html
    assert "record-chart-no" in html
    assert "record-patient-name" in html
    assert "record-employee" in html
    assert "record-counts" in html
