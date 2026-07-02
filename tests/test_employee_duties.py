"""당직 관리 (EmployeeDuty) API 계약 + 동작 테스트.

휴무(EmployeeLeave)와 같은 캘린더 관리이나 유형/종류 없이 직원 + 날짜 + 메모만.
격리 DB(conftest) + 세션 시드 치료사 사용. 테스트마다 고유 날짜로 상호 간섭 차단.
"""
from __future__ import annotations

from tests.harness.seed_data import get_test_therapist_id

# 충분히 미래 + 당직 전용 날짜 (휴무 시드 FIXED_LEAVE_DATE 2099-06-15 와 무관)
_BASE = "2099-09-"


def _emp(name="김테스트치료사") -> str:
    return get_test_therapist_id(name)


def _clear(client, date: str) -> None:
    """해당 날짜의 모든 당직 제거 (bulk-set 빈 items)."""
    client.post("/api/employee-duties/bulk-set", json={"duty_date": date, "items": []})


def _duties_on(client, date: str) -> list:
    r = client.get(f"/api/employee-duties?date={date}")
    assert r.status_code == 200
    return r.json()


# ──────────────────────── 1. 단건 생성 / 조회 / 키 계약 ────────────────────────


def test_create_and_list_employee_duty(client):
    date = _BASE + "01"
    _clear(client, date)
    emp = _emp()

    r = client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "memo": "야간 당직",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["employee_id"] == emp
    assert body["duty_date"] == date
    assert body["memo"] == "야간 당직"
    assert body["id"]

    rows = _duties_on(client, date)
    assert len(rows) == 1
    assert rows[0]["employee_id"] == emp


def test_response_keys_contract(client):
    date = _BASE + "02"
    _clear(client, date)
    client.post("/api/employee-duties", json={"employee_id": _emp(), "duty_date": date})
    rows = _duties_on(client, date)
    assert rows, "당직 1건 이상이어야 함"
    assert set(rows[0].keys()) == {"id", "employee_id", "duty_date", "memo"}


# ──────────────────────── 2. upsert (UNIQUE 1건 유지) ────────────────────────


def test_upsert_keeps_single_row(client):
    date = _BASE + "03"
    _clear(client, date)
    emp = _emp()

    client.post("/api/employee-duties", json={"employee_id": emp, "duty_date": date, "memo": "v1"})
    client.post("/api/employee-duties", json={"employee_id": emp, "duty_date": date, "memo": "v2"})

    rows = _duties_on(client, date)
    assert len(rows) == 1
    assert rows[0]["memo"] == "v2"


# ──────────────────────── 3. 삭제 ────────────────────────


def test_delete_employee_duty(client):
    date = _BASE + "04"
    _clear(client, date)
    emp = _emp()

    created = client.post(
        "/api/employee-duties", json={"employee_id": emp, "duty_date": date},
    ).json()

    r = client.delete(f"/api/employee-duties/{created['id']}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert _duties_on(client, date) == []


def test_delete_missing_returns_404(client):
    r = client.delete("/api/employee-duties/nonexistent-id-xyz")
    assert r.status_code == 404


# ──────────────────────── 4. bulk-add (직원 1명 · 여러 날짜) ────────────────────────


def test_bulk_add_multiple_dates(client):
    dates = [_BASE + "05", _BASE + "06", _BASE + "07"]
    for d in dates:
        _clear(client, d)
    emp = _emp()

    r = client.post("/api/employee-duties/bulk-add", json={
        "items": [{"employee_id": emp, "duty_date": d} for d in dates],
        "memo": "주말 당직",
    })
    assert r.status_code == 200
    assert r.json()["count"] == 3
    for d in dates:
        rows = _duties_on(client, d)
        assert len(rows) == 1
        assert rows[0]["memo"] == "주말 당직"


def test_bulk_add_preserves_other_employee(client):
    date = _BASE + "08"
    _clear(client, date)
    emp_a = _emp("김테스트치료사")
    emp_b = _emp("이테스트치료사")

    client.post("/api/employee-duties", json={"employee_id": emp_a, "duty_date": date})
    # bulk-add 는 기존 보존 — emp_a 가 남아 있어야 함
    client.post("/api/employee-duties/bulk-add", json={
        "items": [{"employee_id": emp_b, "duty_date": date}],
    })

    ids = {row["employee_id"] for row in _duties_on(client, date)}
    assert ids == {emp_a, emp_b}


# ──────────────────────── 5. bulk-set (한 날짜 일괄 교체) ────────────────────────


def test_bulk_set_replaces_date(client):
    date = _BASE + "09"
    _clear(client, date)
    emp_a = _emp("김테스트치료사")
    emp_b = _emp("이테스트치료사")

    client.post("/api/employee-duties", json={"employee_id": emp_a, "duty_date": date})
    # bulk-set 은 날짜의 기존 당직 전부 삭제 후 새로 등록 → emp_b 만 남음
    r = client.post("/api/employee-duties/bulk-set", json={
        "duty_date": date,
        "items": [{"employee_id": emp_b}],
        "memo": "교대",
    })
    assert r.status_code == 200
    assert r.json()["count"] == 1

    rows = _duties_on(client, date)
    assert len(rows) == 1
    assert rows[0]["employee_id"] == emp_b
    assert rows[0]["memo"] == "교대"


def test_bulk_set_requires_duty_date(client):
    r = client.post("/api/employee-duties/bulk-set", json={"items": []})
    assert r.status_code == 400


# ──────────────────────── 6. sync ENTITY_MAP 등록 (멀티PC 동기화) ────────────────────────


def test_entity_map_includes_employee_duty():
    from app.models import models
    from app.services.sync import ENTITY_MAP

    assert ENTITY_MAP.get("employee_duty") is models.EmployeeDuty


def test_model_has_unique_constraint():
    from app.models import models

    names = {
        c.name for c in models.EmployeeDuty.__table__.constraints if c.name
    }
    assert "uq_employee_duty_date" in names
