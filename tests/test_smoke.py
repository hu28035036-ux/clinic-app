"""스모크 테스트 — 하네스 자체가 동작하는지 + 핵심 GET API 응답.

이 테스트가 실패하면 그 이후 어떤 기능 테스트도 신뢰할 수 없다.
"""
from __future__ import annotations

from datetime import datetime, timedelta


def test_app_imported():
    """app 객체 import 가능."""
    from app.main import app
    assert app is not None
    assert hasattr(app, "router")


def test_db_path_is_isolated(db_path):
    """테스트 DB 경로가 격리되어 있는지 (temp 또는 test 포함)."""
    norm = db_path.lower().replace("\\", "/")
    assert ("temp" in norm) or ("test" in norm), (
        f"DB 경로가 격리되지 않았습니다: {db_path}"
    )
    assert "/tests/" in norm, (
        f"DB 가 tests/ 폴더 아래에 있어야 합니다: {db_path}"
    )


def test_db_path_not_production(db_path):
    """운영 경로 패턴이 아닌지 — db_guard 와 동일 검사 한 번 더."""
    from tests.harness.db_guard import _is_production_pattern, _normalize
    assert not _is_production_pattern(_normalize(db_path)), (
        f"운영 DB 경로 패턴이 감지되었습니다: {db_path}"
    )


def test_get_treatments(client):
    """치료항목 목록 — 시드된 5개 + manual90 = 6개 이상."""
    resp = client.get("/api/treatments")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    codes = {t["code"] for t in data}
    # init_db 자동 시드 5개 + 우리 시드 manual90
    for required in ("manual30", "manual60", "eswt", "injection", "cartilage", "manual90"):
        assert required in codes, f"치료항목 '{required}' 가 시드되지 않았습니다."


def test_get_employees(client):
    """직원 목록 — 시드된 테스트 치료사 3명 포함."""
    resp = client.get("/api/employees", params={"role": "therapist"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = {e["name"] for e in data}
    for required in ("김테스트치료사", "이테스트치료사", "박테스트치료사"):
        assert required in names, f"테스트 치료사 '{required}' 가 시드되지 않았습니다."


def test_get_appointments(client):
    """예약 목록 — 빈 결과여도 200."""
    now = datetime.now()
    start = (now - timedelta(days=1)).isoformat()
    end = (now + timedelta(days=1)).isoformat()
    resp = client.get("/api/appointments", params={"start": start, "end": end})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_employee_leaves(client):
    """휴무 목록 — 시드된 3건 (FIXED_LEAVE_DATE 에) 포함."""
    from tests.harness.seed_data import FIXED_LEAVE_DATE

    resp = client.get("/api/employee-leaves", params={"date": FIXED_LEAVE_DATE})
    assert resp.status_code == 200
    rows = resp.json()
    types = {r["leave_type"] for r in rows}
    assert {"full", "morning", "afternoon"}.issubset(types), (
        f"시드된 휴무 3종 모두가 보이지 않습니다: {rows}"
    )


def test_get_stats_summary(client):
    """통계 요약 — 빈 데이터여도 200."""
    now = datetime.now()
    resp = client.get("/api/stats/summary", params={
        "year": now.year,
        "month": now.month,
    })
    assert resp.status_code == 200
    body = resp.json()
    for required in ("total", "manual", "approved", "manual_approved", "canceled"):
        assert required in body, f"summary 응답에 '{required}' 누락"
