from __future__ import annotations

import uuid


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


def _create_category(client, name_prefix: str, *, default_can_manual=True) -> dict:
    resp = client.post("/api/employee-categories", json={
        "name": _unique(name_prefix),
        "color": "#22C55E",
        "active": True,
        "sort_order": 70,
        "default_can_doctor_treatment": False,
        "default_can_manual": default_can_manual,
        "default_can_eswt": True,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_treatment(client, headers: dict, category_id: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post("/api/treatments", json={
        "name": f"aggregate-treatment-{suffix}",
        "short": f"A{suffix[:7]}",
        "category_id": category_id,
        "default_minutes": 30,
        "role": "therapist",
        "count_increment": 1,
        "show_in_patient": False,
        "active": True,
        "sort_order": 10,
        "code": f"agg_{suffix}",
        "price": 0,
        "incentive_pct": None,
        "incentive_amount": None,
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_employee_categories_are_user_created_not_seeded(client):
    r = client.get("/api/employee-categories")
    assert r.status_code == 200
    rows = r.json()
    names = {row["name"] for row in rows}

    assert "\uc9c4\ub8cc\uacfc" not in names
    assert "\uce58\ub8cc\uacfc" not in names


def test_employee_requires_user_created_category(client):
    before = client.get("/api/employee-categories")
    assert before.status_code == 200
    before_names = {row["name"] for row in before.json()}

    created = client.post("/api/employees", json={
        "name": _unique("pytest-no-category-employee"),
        "color": "#9CA3AF",
        "active": True,
    })
    assert created.status_code == 400, created.text

    after = client.get("/api/employee-categories")
    assert after.status_code == 200
    after_names = {row["name"] for row in after.json()}
    assert after_names == before_names
    assert "\uce58\ub8cc\uacfc" not in after_names


def test_category_crud_reorder_and_employee_effective_permissions(client):
    cat_name = _unique("pytest-category")
    emp_name = _unique("pytest-employee")
    category_payload = {
        "name": cat_name,
        "color": "#12ABCD",
        "active": True,
        "sort_order": 50,
        "default_can_doctor_treatment": True,
        "default_can_manual": False,
        "default_can_eswt": True,
    }

    created = client.post("/api/employee-categories", json=category_payload)
    assert created.status_code == 200, created.text
    category = created.json()
    assert category["name"] == cat_name

    employee_payload = {
        "name": emp_name,
        "category_id": category["id"],
        "color": "#12ABCD",
        "active": True,
        "birth_date": None,
        "phone": None,
        "hire_date": None,
        "can_doctor_treatment_override": None,
        "can_manual_override": None,
        "can_eswt_override": None,
    }

    employee = client.post("/api/employees", json=employee_payload)
    assert employee.status_code == 200, employee.text
    body = employee.json()
    assert "role" not in body
    assert body["category_id"] == category["id"]
    assert body["category_name"] == cat_name
    assert body["can_doctor_treatment"] is True
    assert body["can_manual"] is False
    assert body["can_eswt"] is True

    employee_payload["can_manual_override"] = True
    overridden = client.put(f"/api/employees/{body['id']}", json=employee_payload)
    assert overridden.status_code == 200, overridden.text
    assert overridden.json()["can_manual"] is True

    reordered = client.post(
        "/api/employee-categories/reorder",
        json=[{"id": category["id"], "sort_order": 5}],
    )
    assert reordered.status_code == 200, reordered.text
    assert reordered.json() == {"ok": True}

    category_payload["sort_order"] = 5
    category_payload["active"] = False
    disabled = client.put(
        f"/api/employee-categories/{category['id']}",
        json=category_payload,
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["active"] is False

    active_rows = client.get("/api/employee-categories?active=true").json()
    assert category["id"] not in {row["id"] for row in active_rows}


def test_delete_category_hard_deletes_when_unreferenced_and_deactivates_when_referenced(client):
    headers = _admin_headers(client)
    unused_payload = {
        "name": _unique("pytest-unused-category"),
        "color": "#EF4444",
        "active": True,
        "sort_order": 80,
        "default_can_doctor_treatment": False,
        "default_can_manual": True,
        "default_can_eswt": False,
    }
    unused = client.post("/api/employee-categories", json=unused_payload)
    assert unused.status_code == 200, unused.text
    unused_id = unused.json()["id"]

    deleted = client.delete(f"/api/employee-categories/{unused_id}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] is True
    rows = client.get("/api/employee-categories").json()
    assert unused_id not in {row["id"] for row in rows}

    used_payload = dict(unused_payload)
    used_payload["name"] = _unique("pytest-used-category")
    used = client.post("/api/employee-categories", json=used_payload)
    assert used.status_code == 200, used.text
    used_category = used.json()
    emp = client.post("/api/employees", json={
        "name": _unique("pytest-used-employee"),
        "category_id": used_category["id"],
        "color": "#EF4444",
        "active": True,
    })
    assert emp.status_code == 200, emp.text

    deactivated = client.delete(
        f"/api/employee-categories/{used_category['id']}",
        headers=headers,
    )
    assert deactivated.status_code == 200, deactivated.text
    body = deactivated.json()
    assert body["deleted"] is False
    assert body["deactivated"] is True
    rows = client.get("/api/employee-categories").json()
    assert next(row for row in rows if row["id"] == used_category["id"])["active"] is False


def test_employee_treatment_override_and_direct_aggregate(client):
    headers = _admin_headers(client)
    therapy = _create_category(client, "pytest-therapy-category")
    selected_treatment = _create_treatment(client, headers, therapy["id"])

    employee = client.post("/api/employees", json={
        "name": _unique("pytest-treatment-employee"),
        "category_id": therapy["id"],
        "color": "#3B82F6",
        "active": True,
        "treatment_override_enabled": True,
        "treatment_ids": [selected_treatment["id"]],
    })
    assert employee.status_code == 200, employee.text
    emp_body = employee.json()
    assert emp_body["treatment_override_enabled"] is True
    assert emp_body["treatment_ids"] == [selected_treatment["id"]]

    empty_employee = client.post("/api/employees", json={
        "name": _unique("pytest-empty-treatment-employee"),
        "category_id": therapy["id"],
        "color": "#9CA3AF",
        "active": True,
        "treatment_override_enabled": True,
        "treatment_ids": [],
    })
    assert empty_employee.status_code == 200, empty_employee.text
    empty_emp_id = empty_employee.json()["id"]

    saved = client.post("/api/manual-counts", json={
        "date": "2099-07-01",
        "therapist_id": emp_body["id"],
        "treatment_code": selected_treatment["code"],
        "count": 4,
    })
    assert saved.status_code == 200, saved.text

    aggregate = client.get(
        "/api/stats/direct-aggregate"
        f"?date_from=2099-07-01&date_to=2099-07-01&category_id={therapy['id']}"
    )
    assert aggregate.status_code == 200, aggregate.text
    data = aggregate.json()
    employee_ids = {row["id"] for row in data["employees"]}
    assert emp_body["id"] in employee_ids
    assert empty_emp_id not in employee_ids
    assert data["items"][0]["employee_data"][emp_body["id"]]["counts"][selected_treatment["code"]] == 4

    default_aggregate = client.get(
        "/api/stats/direct-aggregate?date_from=2099-07-01&date_to=2099-07-01"
    )
    assert default_aggregate.status_code == 200, default_aggregate.text
    default_data = default_aggregate.json()
    assert default_data["category_id"]
    assert default_data["treatments"]

    legacy_employee = client.post("/api/employees", json={
        "name": _unique("pytest-legacy-treatment-employee"),
        "category_id": therapy["id"],
        "color": "#10B981",
        "active": True,
    })
    assert legacy_employee.status_code == 200, legacy_employee.text
    legacy_id = legacy_employee.json()["id"]

    from app.database import SessionLocal
    from app.models import models

    db = SessionLocal()
    try:
        legacy = db.get(models.Employee, legacy_id)
        legacy.category_id = None
        legacy.treatment_override_enabled = False
        legacy.role = "therapist"
        legacy.can_manual = True
        legacy.can_eswt = True
        legacy.can_manual_override = True
        legacy.can_eswt_override = True
        db.commit()
    finally:
        db.close()

    legacy_aggregate = client.get(
        "/api/stats/direct-aggregate"
        f"?date_from=2099-07-01&date_to=2099-07-01&category_id={therapy['id']}"
    )
    assert legacy_aggregate.status_code == 200, legacy_aggregate.text
    legacy_data = legacy_aggregate.json()
    assert not any(row["id"] == legacy_id for row in legacy_data["employees"])


def test_direct_aggregate_selected_category_does_not_use_other_category_fallback(client):
    headers = _admin_headers(client)
    empty_category = _create_category(client, "pytest-empty-aggregate-category")
    other_category = _create_category(client, "pytest-other-aggregate-category")
    other_treatment = _create_treatment(client, headers, other_category["id"])

    empty_employee = client.post("/api/employees", json={
        "name": _unique("pytest-empty-category-employee"),
        "category_id": empty_category["id"],
        "color": "#22C55E",
        "active": True,
        "treatment_override_enabled": False,
    })
    assert empty_employee.status_code == 200, empty_employee.text

    other_employee = client.post("/api/employees", json={
        "name": _unique("pytest-other-category-employee"),
        "category_id": other_category["id"],
        "color": "#3B82F6",
        "active": True,
        "treatment_override_enabled": True,
        "treatment_ids": [other_treatment["id"]],
    })
    assert other_employee.status_code == 200, other_employee.text

    aggregate = client.get(
        "/api/stats/direct-aggregate"
        f"?date_from=2099-07-02&date_to=2099-07-02&category_id={empty_category['id']}"
    )
    assert aggregate.status_code == 200, aggregate.text
    data = aggregate.json()
    assert data["category_id"] == empty_category["id"]
    assert data["treatments"] == []
    assert data["employees"] == []
    assert data["items"] == [{"date": "2099-07-02", "employee_data": {}}]
