from __future__ import annotations

import uuid


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


def _make_category(client, prefix: str = "inventory-cat") -> dict:
    resp = client.post("/api/employee-categories", json={
        "name": _unique(prefix),
        "color": "#0EA5E9",
        "active": True,
        "sort_order": 80,
        "default_can_doctor_treatment": False,
        "default_can_manual": True,
        "default_can_eswt": False,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _section(data: dict, category_id: str) -> dict:
    return next(x for x in data["categories"] if x["category"]["id"] == category_id)


def test_inventory_category_item_field_value_and_author(client):
    headers = _admin_headers(client)
    category = _make_category(client)

    first = client.get("/api/inventory")
    assert first.status_code == 200, first.text
    assert _section(first.json(), category["id"])["items"] == []

    item = client.post("/api/inventory/items", json={
        "category_id": category["id"],
        "name": "젤",
        "unit": "박스",
        "author": "김관리",
    }, headers=headers)
    assert item.status_code == 200, item.text
    item_id = item.json()["id"]

    field = client.post("/api/inventory/fields", json={
        "category_id": category["id"],
        "name": "현재수량",
        "field_type": "number",
        "author": "김관리",
    }, headers=headers)
    assert field.status_code == 200, field.text
    field_id = field.json()["id"]

    value = client.post("/api/inventory/values", json={
        "item_id": item_id,
        "field_id": field_id,
        "value": "12",
        "author": "김관리",
    }, headers=headers)
    assert value.status_code == 200, value.text

    data = client.get("/api/inventory").json()
    sec = _section(data, category["id"])
    assert sec["state"]["last_author"] == "김관리"
    assert sec["state"]["last_written_at"]
    assert sec["fields"][0]["name"] == "현재수량"
    assert sec["fields"][0]["field_type"] == "number"
    assert sec["items"][0]["name"] == "젤"
    assert sec["items"][0]["unit"] == "박스"
    assert sec["items"][0]["values"][field_id] == "12"

    saved_author = client.post("/api/inventory/category-state", json={
        "category_id": category["id"],
        "last_author": "박팀장",
    }, headers=headers)
    assert saved_author.status_code == 200, saved_author.text
    assert saved_author.json()["last_author"] == "박팀장"

    deleted = client.delete(f"/api/inventory/fields/{field_id}?author=박팀장", headers=headers)
    assert deleted.status_code == 200, deleted.text
    after_delete = _section(client.get("/api/inventory").json(), category["id"])
    assert after_delete["fields"] == []
    assert after_delete["items"][0]["values"] == {}


def test_inventory_value_rejects_cross_category_field(client):
    headers = _admin_headers(client)
    category_a = _make_category(client, "inventory-a")
    category_b = _make_category(client, "inventory-b")

    item = client.post("/api/inventory/items", json={
        "category_id": category_a["id"],
        "name": "소독솜",
    }, headers=headers)
    assert item.status_code == 200, item.text

    field = client.post("/api/inventory/fields", json={
        "category_id": category_b["id"],
        "name": "위치",
    }, headers=headers)
    assert field.status_code == 200, field.text

    value = client.post("/api/inventory/values", json={
        "item_id": item.json()["id"],
        "field_id": field.json()["id"],
        "value": "창고",
    }, headers=headers)
    assert value.status_code == 400
    assert "과가 다릅니다" in value.text


def test_inventory_writes_require_admin(client):
    category = _make_category(client, "inventory-auth")
    resp = client.post("/api/inventory/items", json={
        "category_id": category["id"],
        "name": "테이프",
    })
    assert resp.status_code == 401
