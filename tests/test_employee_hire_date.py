"""hire_date (입사일) 필드 계약 테스트.

치료사 정보 수정 모달에서 입사일을 입력/저장한다.
- /api/employees (GET/PUT) 에서 hire_date 라운드트립
- snake_case 정확성 (camelCase / kebab-case 드리프트 차단)
- None 으로 다시 비울 수 있어야 함

향후 _serialize_employee 누락이나 EmployeeIn 스키마 드리프트 시 즉시 빨간 불.
"""
from __future__ import annotations

from tests.harness.seed_data import get_test_therapist_id


def _get_employee(client, eid: str) -> dict:
    rows = client.get("/api/employees").json()
    return next(e for e in rows if e["id"] == eid)


def _payload(initial: dict, **overrides) -> dict:
    """기존 직원 dict 에서 EmployeeIn 페이로드 만들기."""
    p = {
        "name": initial["name"],
        "category_id": initial["category_id"],
        "color": initial["color"],
        "active": initial["active"],
        "birth_date": initial.get("birth_date"),
        "phone": initial.get("phone"),
        "hire_date": initial.get("hire_date"),
        "can_doctor_treatment_override": initial["can_doctor_treatment_override"],
        "can_eswt_override": initial["can_eswt_override"],
        "can_manual_override": initial["can_manual_override"],
    }
    p.update(overrides)
    return p


def test_hire_date_field_present_in_get(client):
    """GET /api/employees 응답에 hire_date 키가 항상 존재해야 한다."""
    eid = get_test_therapist_id("김테스트치료사")
    e = _get_employee(client, eid)
    assert "hire_date" in e, "GET /api/employees 응답에 hire_date 키 누락"
    # snake_case 정확성 (프론트가 e.hire_date 로 읽음)
    assert "hireDate" not in e
    assert "hire-date" not in e


def test_hire_date_round_trips_via_put(client):
    """PUT 으로 hire_date 설정 → 응답/GET 양쪽에 반영."""
    eid = get_test_therapist_id("김테스트치료사")
    initial = _get_employee(client, eid)

    try:
        r = client.put(f"/api/employees/{eid}",
                       json=_payload(initial, hire_date="2020-03-15"))
        assert r.status_code == 200, r.text
        assert r.json()["hire_date"] == "2020-03-15", "PUT 응답에 hire_date 미반영"

        after = _get_employee(client, eid)
        assert after["hire_date"] == "2020-03-15", "GET 재조회에서 hire_date 미반영"
    finally:
        # 다른 테스트(시드 의존 테스트 포함)에 영향 없도록 원복
        client.put(f"/api/employees/{eid}",
                   json=_payload(initial, hire_date=initial.get("hire_date")))


def test_hire_date_can_be_cleared(client):
    """PUT hire_date=None 으로 비울 수 있어야 한다 (선택 필드)."""
    eid = get_test_therapist_id("이테스트치료사")
    initial = _get_employee(client, eid)

    try:
        # 일단 값을 설정
        r = client.put(f"/api/employees/{eid}",
                       json=_payload(initial, hire_date="2021-06-01"))
        assert r.status_code == 200
        assert r.json()["hire_date"] == "2021-06-01"

        # 그 다음 None 으로 비우기
        r2 = client.put(f"/api/employees/{eid}",
                        json=_payload(initial, hire_date=None))
        assert r2.status_code == 200, r2.text
        assert r2.json()["hire_date"] is None, "PUT hire_date=None 미반영"

        after = _get_employee(client, eid)
        assert after["hire_date"] is None, "GET 재조회에서 hire_date=None 미반영"
    finally:
        client.put(f"/api/employees/{eid}",
                   json=_payload(initial, hire_date=initial.get("hire_date")))
