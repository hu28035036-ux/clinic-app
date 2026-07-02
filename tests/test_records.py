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


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


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


def _make_record_treatment(client, headers: dict, category_id: str, name_prefix: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post("/api/treatments", json={
        "name": _unique(name_prefix),
        "short": f"R{suffix[:7]}",
        "category_id": category_id,
        "default_minutes": 30,
        "role": "therapist",
        "count_increment": 1,
        "show_in_patient": False,
        "active": True,
        "sort_order": 10,
        "code": f"rectx_{suffix}",
        "price": 0,
        "requires_record": True,
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requires_record"] is True
    return body


def test_record_tabs_come_from_record_required_treatments(client):
    headers = _admin_headers(client)
    category = _make_category(client, "records-category")
    other_category = _make_category(client, "records-other-category")
    employee = _make_employee(client, category["id"], "records-employee")
    other_employee = _make_employee(client, other_category["id"], "records-other-employee")

    # '기록 필요' 치료항목이 곧 기록 탭이 된다 (tab_key = 치료항목 code).
    tx = _make_record_treatment(client, headers, category["id"], "도수기록")
    code = tx["code"]

    initial = client.get("/api/records")
    assert initial.status_code == 200, initial.text
    tab_by_key = {tab["tab_key"]: tab for tab in initial.json()["tabs"]}
    assert code in tab_by_key
    assert tab_by_key[code]["label"] == tx["name"]
    assert tab_by_key[code]["category_id"] == category["id"]

    # 탭 이름 인라인 수정 → 치료항목 이름이 바뀐다.
    renamed = client.put(f"/api/records/tabs/{code}", json={
        "label": "도수기록-수정",
        "category_id": category["id"],
    })
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["label"] == "도수기록-수정"
    assert renamed.json()["tab_key"] == code

    created = client.post("/api/records/entries", json={
        "tab_key": code,
        "record_date": "2026-06-12",
        "chart_no": "1001",
        "patient_name": "홍길동",
        "employee_id": employee["id"],
    })
    assert created.status_code == 200, created.text
    created_id = created.json()["id"]
    assert created.json()["tab_key"] == code
    assert created.json()["treatment_id"] == tx["id"]

    updated = client.put(f"/api/records/entries/{created_id}", json={
        "record_date": "2026-06-12",
        "chart_no": "1001-수정",
        "patient_name": "홍길동수정",
        "employee_id": employee["id"],
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["chart_no"] == "1001-수정"

    # 다른 과 직원은 거부 (과 기준 검증).
    rejected = client.post("/api/records/entries", json={
        "tab_key": code,
        "record_date": "2026-06-12",
        "chart_no": "1002",
        "patient_name": "김길동",
        "employee_id": other_employee["id"],
    })
    assert rejected.status_code == 400
    assert "선택한 과의 직원만" in rejected.text

    # 기록필요가 아닌 코드로는 입력 불가.
    bad = client.post("/api/records/entries", json={
        "tab_key": "manual",
        "record_date": "2026-06-12",
        "chart_no": "1003",
        "patient_name": "박길동",
        "employee_id": employee["id"],
    })
    assert bad.status_code == 400

    data = client.get("/api/records?record_date=2026-06-12").json()
    assert data["record_date"] == "2026-06-12"
    assert data["week_start"] == "2026-06-08"
    assert data["week_end"] == "2026-06-14"
    entries = [row for row in data["entries"] if row["tab_key"] == code]
    assert any(row["chart_no"] == "1001-수정" and row["patient_name"] == "홍길동수정" for row in entries)
    assert data["counts"][code][employee["id"]] == 1
    assert data["week_counts"][code]["2026-06-12"] == 1
    assert other_employee["id"] not in data["counts"].get(code, {})

    other_day = client.get("/api/records?record_date=2026-06-13").json()
    assert not [row for row in other_day["entries"] if row["tab_key"] == code]
    assert other_day["week_counts"][code]["2026-06-12"] == 1


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
