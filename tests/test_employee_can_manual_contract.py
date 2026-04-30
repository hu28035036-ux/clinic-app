"""can_manual 필드 계약 테스트.

예약현황표(main.html renderDayBoard)는 /api/employees 응답의 can_manual 필드로
도수치료 가능 치료사만 컬럼으로 표시한다. 향후 _serialize_employee 또는
EmployeeIn 스키마에서 이 필드가 누락/변경되면 프론트가 조용히 깨지므로,
GET/PUT 라운드트립을 검증해 데이터 계약을 회귀로부터 보호한다.
"""
from __future__ import annotations

from tests.harness.seed_data import get_test_therapist_id


def _get_employee(client, eid: str) -> dict:
    rows = client.get("/api/employees").json()
    return next(e for e in rows if e["id"] == eid)


def test_can_manual_field_present_and_round_trips(client):
    eid = get_test_therapist_id("김테스트치료사")

    initial = _get_employee(client, eid)
    assert "can_manual" in initial, "GET /api/employees 응답에 can_manual 키가 없음"
    assert initial["can_manual"] is True, "시드 치료사 기본값은 can_manual=True"

    payload = {
        "name": initial["name"],
        "role": initial["role"],
        "color": initial["color"],
        "active": initial["active"],
        "birth_date": initial.get("birth_date"),
        "phone": initial.get("phone"),
        "can_eswt": initial["can_eswt"],
        "can_manual": False,
    }
    try:
        r = client.put(f"/api/employees/{eid}", json=payload)
        assert r.status_code == 200, f"PUT 실패: {r.status_code} {r.text}"
        assert r.json()["can_manual"] is False, "PUT 응답에서 can_manual=False 미반영"

        after_put = _get_employee(client, eid)
        assert after_put["can_manual"] is False, "GET 재조회에서 can_manual=False 미반영"
    finally:
        # 다른 테스트(시드 의존 테스트 포함)에 영향 없도록 원복
        payload["can_manual"] = True
        r2 = client.put(f"/api/employees/{eid}", json=payload)
        assert r2.status_code == 200
        assert r2.json()["can_manual"] is True

    restored = _get_employee(client, eid)
    assert restored["can_manual"] is True, "원복 후 can_manual=True 미반영"
