from __future__ import annotations

import uuid


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


def _make_category(client, prefix: str = "revenue-cat") -> dict:
    resp = client.post("/api/employee-categories", json={
        "name": _unique(prefix),
        "color": "#0EA5E9",
        "active": True,
        "sort_order": 75,
        "default_can_doctor_treatment": False,
        "default_can_manual": True,
        "default_can_eswt": False,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_treatment(client, headers: dict, category_id: str, *, short: str, price: int) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post("/api/treatments", json={
        "name": f"revenue-treatment-{suffix}",
        "short": f"{short}{suffix[:4]}",
        "category_id": category_id,
        "default_minutes": 30,
        "role": "therapist",
        "count_increment": 1,
        "show_in_patient": False,
        "active": True,
        "sort_order": 10,
        "code": f"revenue_{suffix}",
        "price": price,
        "incentive_pct": None,
        "incentive_amount": 0,
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_employee(client, category_id: str, treatment_ids: list[str]) -> dict:
    resp = client.post("/api/employees", json={
        "name": _unique("revenue-employee"),
        "category_id": category_id,
        "color": "#10B981",
        "active": True,
        "treatment_override_enabled": True,
        "treatment_ids": treatment_ids,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_revenue_records_grid_stats_and_delete(client):
    headers = _admin_headers(client)
    category = _make_category(client)
    payload = {
        "date_from": "2099-09-01",
        "date_to": "2099-09-02",
        "category_id": category["id"],
        "entries": [
            {
                "record_date": "2099-09-01",
                "category_id": category["id"],
                "cash_amount": 1000,
                "card_amount": 2000,
                "transfer_amount": 3000,
                "other_amount": 4000,
                "memo": "첫 매출",
            },
            {
                "record_date": "2099-09-02",
                "category_id": category["id"],
                "cash_amount": 0,
                "card_amount": 0,
                "transfer_amount": 0,
                "other_amount": 0,
                "memo": "",
            },
        ],
    }

    saved = client.post("/api/revenue/records/grid", json=payload, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["changed"] == {"upserted": 1, "deleted": 0}

    listed = client.get(
        f"/api/revenue/records?date_from=2099-09-01&date_to=2099-09-02&category_id={category['id']}",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    records = listed.json()["records"]
    assert [r["record_date"] for r in records] == ["2099-09-01", "2099-09-02"]
    assert records[0]["total_amount"] == 10000
    assert records[0]["memo"] == "첫 매출"
    assert records[1]["total_amount"] == 0

    stats = client.get(
        f"/api/revenue/stats?date_from=2099-09-01&date_to=2099-09-02&category_id={category['id']}",
        headers=headers,
    )
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert body["current"]["revenue_total"] == 10000
    assert body["current"]["record_count"] == 1
    assert body["previous"]["revenue_total"] == 0
    assert body["delta"]["revenue_total"] == {"amount": 10000, "pct": None}
    by_payment = {row["key"]: row["amount"] for row in body["current"]["by_payment"]}
    assert by_payment == {
        "cash_amount": 1000,
        "card_amount": 2000,
        "transfer_amount": 3000,
        "other_amount": 4000,
    }
    assert body["settlement"]["price_total"] == 0
    assert body["settlement"]["revenue_minus_settlement_price"] == 10000
    assert body["settlement"]["revenue_after_incentive"] == 10000

    payload["entries"][0].update({
        "cash_amount": 0,
        "card_amount": 0,
        "transfer_amount": 0,
        "other_amount": 0,
        "memo": "",
    })
    deleted = client.post("/api/revenue/records/grid", json=payload, headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["changed"] == {"upserted": 0, "deleted": 1}

    after_delete = client.get(
        f"/api/revenue/stats?date_from=2099-09-01&date_to=2099-09-02&category_id={category['id']}",
        headers=headers,
    )
    assert after_delete.status_code == 200, after_delete.text
    assert after_delete.json()["current"]["revenue_total"] == 0


def test_revenue_stats_settlement_by_treatment(client):
    headers = _admin_headers(client)
    category = _make_category(client, "revenue-settle-cat")
    treatment_a = _make_treatment(client, headers, category["id"], short="RA", price=50000)
    treatment_b = _make_treatment(client, headers, category["id"], short="RB", price=70000)
    employee = _make_employee(client, category["id"], [treatment_a["id"], treatment_b["id"]])

    saved = client.post("/api/settlement/records/grid", json={
        "date_from": "2099-09-10",
        "date_to": "2099-09-10",
        "category_id": category["id"],
        "entries": [
            {
                "performed_on": "2099-09-10",
                "employee_id": employee["id"],
                "treatment_id": treatment_a["id"],
                "quantity": 2,
            },
            {
                "performed_on": "2099-09-10",
                "employee_id": employee["id"],
                "treatment_id": treatment_b["id"],
                "quantity": 1,
            },
        ],
    }, headers=headers)
    assert saved.status_code == 200, saved.text

    stats = client.get(
        f"/api/revenue/stats?date_from=2099-09-10&date_to=2099-09-10&category_id={category['id']}",
        headers=headers,
    )
    assert stats.status_code == 200, stats.text
    by_treatment = {
        row["treatment_id"]: row
        for row in stats.json()["settlement"]["by_treatment"]
    }
    assert by_treatment[treatment_a["id"]]["quantity_total"] == 2
    assert by_treatment[treatment_a["id"]]["price_total"] == 100000
    assert by_treatment[treatment_b["id"]]["quantity_total"] == 1
    assert by_treatment[treatment_b["id"]]["price_total"] == 70000


def test_revenue_writes_require_admin(client):
    resp = client.post("/api/revenue/records/grid", json={
        "date_from": "2099-09-01",
        "date_to": "2099-09-01",
        "entries": [],
    })
    assert resp.status_code == 401
