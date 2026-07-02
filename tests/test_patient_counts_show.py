"""환자탭 '완료 횟수' — 치료완료(approve) → 검색/by-ids 응답 counts_show 반영.

회귀: 환자탭 목록이 search_patients/by-ids 를 쓰는데 응답에 counts_show 가 없어
완료횟수가 항상 '-' 로 보이던 버그(이 키가 빠져 있었음)를 잠근다.
"""
from __future__ import annotations

from datetime import datetime

from tests.harness.helpers import approve_appointment, make_appointment
from tests.harness.seed_data import get_test_patient_id


def _approve_manual(client, pid):
    r = make_appointment(client, patient_id=pid, start_at=datetime(2026, 5, 27, 14, 0),
                         treatment_codes=["manual30"])
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    ar = approve_appointment(client, aid)
    assert ar.status_code == 200, ar.text
    return aid


def test_search_item_has_counts_show_after_approve(client):
    pid = get_test_patient_id("홍길동테스트")
    _approve_manual(client, pid)

    s = client.get("/api/patients/search?q=홍길동테스트&field=name&limit=20&offset=0")
    assert s.status_code == 200, s.text
    item = next((it for it in s.json()["items"] if it["id"] == pid), None)
    assert item is not None
    # 버그였던 핵심: 검색 item 에 counts_show 키가 존재해야 함
    assert "counts_show" in item and isinstance(item["counts_show"], list)

    # approve 가 done_count 를 올렸는지 환자 상세(counts)로 교차 확인
    detail = client.get(f"/api/patients/{pid}").json()
    manual = next((c for c in detail["counts"].values() if c["code"] == "manual30"), None)
    assert manual is not None and manual["done_count"] >= 1
    # manual30 이 환자표시(show_in_patient) 항목이면 counts_show 에 완료>0 으로 들어감
    if manual["show"]:
        done = {c["code"]: c["done_count"] for c in item["counts_show"]}
        assert done.get("manual30", 0) >= 1


def test_by_ids_item_has_counts_show(client):
    pid = get_test_patient_id("김영희테스트")
    _approve_manual(client, pid)
    items = client.post("/api/patients/by-ids", json={"ids": [pid]}).json()["items"]
    assert items and items[0]["id"] == pid
    assert "counts_show" in items[0] and isinstance(items[0]["counts_show"], list)
