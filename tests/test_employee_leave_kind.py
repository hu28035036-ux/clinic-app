"""leave_kind (연차/월차) 필드 계약 테스트.

휴무 관리 모달과 FullCalendar 이벤트 타이틀이 leave_kind 필드에 의존한다.
- /api/employee-leaves (POST/GET) 라운드트립
- /api/employee-leaves/bulk-set 라운드트립
- /api/therapist-leaves (alias) GET 응답에도 포함

향후 _serialize 누락이나 컬럼 드리프트 발생 시 즉시 빨간 불.
"""
from __future__ import annotations

from tests.harness.seed_data import get_test_therapist_id


def test_employee_leaves_get_includes_leave_kind_default_annual(client):
    """모델 default(annual)가 신규 row 에 적용되는지."""
    eid = get_test_therapist_id("김테스트치료사")
    body = {
        "employee_id": eid,
        "leave_date": "2099-07-01",
        "leave_type": "full",
        # leave_kind 생략 — default 'annual' 적용 확인
    }
    r = client.post("/api/employee-leaves", json=body)
    assert r.status_code == 200, r.text
    created = r.json()
    assert "leave_kind" in created, "POST 응답에 leave_kind 키 누락"
    assert created["leave_kind"] == "annual"

    listed = client.get("/api/employee-leaves?date=2099-07-01").json()
    row = next(x for x in listed if x["employee_id"] == eid)
    assert row["leave_kind"] == "annual"

    # 정리
    client.delete(f"/api/employee-leaves/{created['id']}")


def test_employee_leaves_bulk_set_round_trips_leave_kind(client):
    """bulk-set 으로 leave_kind=monthly 저장 → GET 으로 보임."""
    eid_full = get_test_therapist_id("김테스트치료사")
    eid_am = get_test_therapist_id("이테스트치료사")
    date = "2099-07-02"

    payload = {
        "leave_date": date,
        "items": [
            {"therapist_id": eid_full, "leave_type": "full", "leave_kind": "monthly"},
            {"therapist_id": eid_am,   "leave_type": "am",   "leave_kind": "annual"},
        ],
        "memo": "테스트",
    }
    r = client.post("/api/employee-leaves/bulk-set", json=payload)
    assert r.status_code == 200, r.text

    listed = client.get(f"/api/employee-leaves?date={date}").json()
    by_emp = {x["employee_id"]: x for x in listed}
    assert by_emp[eid_full]["leave_kind"] == "monthly"
    assert by_emp[eid_full]["leave_type"] == "full"
    assert by_emp[eid_am]["leave_kind"] == "annual"
    assert by_emp[eid_am]["leave_type"] == "am"

    # therapist-leaves alias 응답에도 leave_kind 포함되는지
    alias = client.get(f"/api/therapist-leaves?date={date}").json()
    by_emp2 = {x["therapist_id"]: x for x in alias}
    assert by_emp2[eid_full]["leave_kind"] == "monthly"
    assert by_emp2[eid_am]["leave_kind"] == "annual"

    # 정리
    for x in listed:
        client.delete(f"/api/employee-leaves/{x['id']}")


def test_leave_kind_field_name_is_snake_case(client):
    """프론트가 obj.leave_kind 로 읽으니 snake_case 정확성 보호."""
    eid = get_test_therapist_id("박테스트치료사")
    body = {
        "employee_id": eid,
        "leave_date": "2099-07-03",
        "leave_type": "pm",
        "leave_kind": "monthly",
    }
    r = client.post("/api/employee-leaves", json=body)
    assert r.status_code == 200
    created = r.json()
    # 정확히 snake_case 이어야 함 (camelCase / kebab-case 드리프트 차단)
    assert "leave_kind" in created
    assert "leaveKind" not in created
    assert "leave-kind" not in created
    assert created["leave_kind"] == "monthly"

    # 정리
    client.delete(f"/api/employee-leaves/{created['id']}")


def test_post_employee_leaves_upserts_existing_row(client):
    """동일 (employee_id, leave_date) 로 재 POST 하면 leave_type/leave_kind/memo 가 갱신되어야 한다.

    회귀: 이전 구현은 exists 분기에서 payload 무시하고 기존 값만 반환 →
    프론트에서 '연차로 만든 휴무를 월차로 변경' 이 저장되지 않았음.
    """
    eid = get_test_therapist_id("김테스트치료사")
    date = "2099-07-04"

    first = client.post("/api/employee-leaves", json={
        "employee_id": eid,
        "leave_date": date,
        "leave_type": "full",
        "leave_kind": "annual",
        "memo": "최초",
    })
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["leave_kind"] == "annual"
    assert first_body["leave_type"] == "full"
    assert first_body["memo"] == "최초"
    leave_id = first_body["id"]

    try:
        # 동일 키로 재 POST — 다른 leave_type/leave_kind/memo
        second = client.post("/api/employee-leaves", json={
            "employee_id": eid,
            "leave_date": date,
            "leave_type": "am",
            "leave_kind": "monthly",
            "memo": "변경",
        })
        assert second.status_code == 200, second.text
        second_body = second.json()
        # 같은 row id 유지 (새 row 생성하면 안 됨)
        assert second_body["id"] == leave_id
        # 응답에 갱신 값 반영
        assert second_body["leave_kind"] == "monthly"
        assert second_body["leave_type"] == "am"
        assert second_body["memo"] == "변경"

        # GET 으로도 갱신 값 확인
        listed = client.get(f"/api/employee-leaves?date={date}").json()
        row = next(x for x in listed if x["employee_id"] == eid)
        assert row["leave_kind"] == "monthly"
        assert row["leave_type"] == "am"
        assert row["memo"] == "변경"

        # leave_kind 생략 시 기본값 annual 유지 — 동일 키 재 POST
        third = client.post("/api/employee-leaves", json={
            "employee_id": eid,
            "leave_date": date,
            "leave_type": "full",
            # leave_kind 생략
            "memo": "기본값",
        })
        assert third.status_code == 200
        assert third.json()["leave_kind"] == "annual"
    finally:
        client.delete(f"/api/employee-leaves/{leave_id}")
