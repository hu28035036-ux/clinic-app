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


def test_inventory_normal_value_open_to_staff(client):
    """일반 칸 값은 관리자 인증 없이 직원도 입력 가능."""
    headers = _admin_headers(client)
    category = _make_category(client, "inventory-open")
    item = client.post("/api/inventory/items", json={
        "category_id": category["id"], "name": "거즈",
    }, headers=headers)
    assert item.status_code == 200, item.text
    field = client.post("/api/inventory/fields", json={
        "category_id": category["id"], "name": "현재수량", "field_type": "number",
    }, headers=headers)
    assert field.status_code == 200, field.text
    assert field.json()["admin_only"] is False

    # 토큰 없이 값 입력 → 일반 칸이므로 허용 (직원).
    value = client.post("/api/inventory/values", json={
        "item_id": item.json()["id"],
        "field_id": field.json()["id"],
        "value": "7",
        "author": "직원",
    })
    assert value.status_code == 200, value.text
    assert value.json()["value"] == "7"


def test_inventory_admin_only_field_blocks_staff(client):
    """관리자 전용 칸은 직원(토큰 없음) 입력 시 401, 관리자는 허용."""
    headers = _admin_headers(client)
    category = _make_category(client, "inventory-adminonly")
    item = client.post("/api/inventory/items", json={
        "category_id": category["id"], "name": "특수약품",
    }, headers=headers)
    assert item.status_code == 200, item.text

    field = client.post("/api/inventory/fields", json={
        "category_id": category["id"],
        "name": "발주승인",
        "admin_only": True,
    }, headers=headers)
    assert field.status_code == 200, field.text
    field_id = field.json()["id"]
    assert field.json()["admin_only"] is True

    # 직원(토큰 없음) → 차단.
    blocked = client.post("/api/inventory/values", json={
        "item_id": item.json()["id"], "field_id": field_id, "value": "승인",
    })
    assert blocked.status_code == 401

    # 관리자 → 허용.
    allowed = client.post("/api/inventory/values", json={
        "item_id": item.json()["id"], "field_id": field_id, "value": "승인",
    }, headers=headers)
    assert allowed.status_code == 200, allowed.text


def test_inventory_admin_only_field_sorts_after_normal(client):
    """관리자 전용 칸은 일반 칸 뒤(관리 열 왼쪽)에 정렬된다."""
    headers = _admin_headers(client)
    category = _make_category(client, "inventory-sort")
    # admin_only 칸을 먼저 만들어도 정렬상 일반 칸 뒤로 가야 한다.
    client.post("/api/inventory/fields", json={
        "category_id": category["id"], "name": "원가", "admin_only": True, "sort_order": 1,
    }, headers=headers)
    client.post("/api/inventory/fields", json={
        "category_id": category["id"], "name": "현재수량", "admin_only": False, "sort_order": 2,
    }, headers=headers)
    sec = _section(client.get("/api/inventory", headers=headers).json(), category["id"])
    names = [f["name"] for f in sec["fields"]]
    assert names == ["현재수량", "원가"]
    assert sec["fields"][0]["admin_only"] is False
    assert sec["fields"][1]["admin_only"] is True


def test_inventory_get_hides_admin_field_without_token(client):
    """미인증 조회 시 관리자 전용 칸과 그 값이 응답에서 제외된다 (직원은 확인 불가)."""
    headers = _admin_headers(client)
    category = _make_category(client, "inventory-hide")
    item = client.post("/api/inventory/items", json={
        "category_id": category["id"], "name": "약품",
    }, headers=headers)
    item_id = item.json()["id"]
    f_norm = client.post("/api/inventory/fields", json={
        "category_id": category["id"], "name": "현재수량", "admin_only": False,
    }, headers=headers).json()
    f_admin = client.post("/api/inventory/fields", json={
        "category_id": category["id"], "name": "발주", "admin_only": True,
    }, headers=headers).json()
    client.post("/api/inventory/values", json={
        "item_id": item_id, "field_id": f_admin["id"], "value": "비밀",
    }, headers=headers)
    client.post("/api/inventory/values", json={
        "item_id": item_id, "field_id": f_norm["id"], "value": "10",
    }, headers=headers)

    # 미인증(직원) 조회 → 관리자 전용 칸과 값 숨김
    pub = _section(client.get("/api/inventory").json(), category["id"])
    pub_names = [f["name"] for f in pub["fields"]]
    assert "현재수량" in pub_names
    assert "발주" not in pub_names
    assert f_admin["id"] not in pub["items"][0]["values"]
    assert pub["items"][0]["values"].get(f_norm["id"]) == "10"

    # 관리자 인증 조회 → 관리자 전용 칸과 값 보임
    adm = _section(client.get("/api/inventory", headers=headers).json(), category["id"])
    adm_names = [f["name"] for f in adm["fields"]]
    assert "발주" in adm_names
    assert adm["items"][0]["values"][f_admin["id"]] == "비밀"
