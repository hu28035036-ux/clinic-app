"""당직 관리 (EmployeeDuty) API 계약 + 동작 테스트.

휴무(EmployeeLeave)와 같은 캘린더 관리. duty_type 으로 아침당직(morning) /
야간당직(night) 분리 — 같은 직원이 같은 날 둘 다 가능, 유형별 독립 관리.
격리 DB(conftest) + 세션 시드 치료사 사용. 테스트마다 고유 날짜로 상호 간섭 차단.
"""
from __future__ import annotations

from app.routers.api import _duty_baseline, _duty_overtime_minutes
from tests.harness.seed_data import get_test_therapist_id

# 충분히 미래 + 당직 전용 날짜 (휴무 시드 FIXED_LEAVE_DATE 2099-06-15 와 무관)
_BASE = "2099-09-"


def _emp(name="김테스트치료사") -> str:
    return get_test_therapist_id(name)


def _clear(client, date: str) -> None:
    """해당 날짜의 모든 당직 제거 (아침/점심/야간 각각 bulk-set 빈 items)."""
    for t in ("morning", "lunch", "night"):
        client.post("/api/employee-duties/bulk-set", json={
            "duty_date": date, "duty_type": t, "items": [],
        })


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
    assert set(rows[0].keys()) == {
        "id", "employee_id", "duty_date", "duty_type", "end_time", "overtime_minutes", "memo",
    }
    # duty_type 미지정 생성은 야간(night) 기본 — 기존 '당직 관리' 데이터 호환
    assert rows[0]["duty_type"] == "night"
    # end_time 미지정은 빈 문자열, 초과분 0
    assert rows[0]["end_time"] == ""
    assert rows[0]["overtime_minutes"] == 0


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
    assert "uq_employee_duty_date_type" in names


# ──────────────────────── 7. 아침당직 / 야간당직 분리 (duty_type) ────────────────────────


def test_morning_and_night_are_independent(client):
    """같은 직원이 같은 날 아침당직 + 야간당직 둘 다 가능, 유형별 필터 동작."""
    date = _BASE + "10"
    _clear(client, date)
    emp = _emp()

    r1 = client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "morning", "memo": "아침",
    })
    r2 = client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "night", "memo": "야간",
    })
    assert r1.status_code == 200 and r1.json()["duty_type"] == "morning"
    assert r2.status_code == 200 and r2.json()["duty_type"] == "night"

    assert len(_duties_on(client, date)) == 2

    for t, memo in (("morning", "아침"), ("night", "야간")):
        r = client.get(f"/api/employee-duties?date={date}&duty_type={t}")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        assert rows[0]["duty_type"] == t
        assert rows[0]["memo"] == memo


def test_upsert_scoped_by_duty_type(client):
    """upsert 키는 (직원, 날짜, 유형) — 같은 유형만 갱신, 다른 유형은 별도 행."""
    date = _BASE + "11"
    _clear(client, date)
    emp = _emp()

    client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "morning", "memo": "v1",
    })
    client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "morning", "memo": "v2",
    })

    rows = client.get(f"/api/employee-duties?date={date}&duty_type=morning").json()
    assert len(rows) == 1
    assert rows[0]["memo"] == "v2"


def test_bulk_set_scoped_by_duty_type(client):
    """아침당직 bulk-set 이 같은 날 야간당직을 삭제하지 않아야 함 (유형별 독립)."""
    date = _BASE + "12"
    _clear(client, date)
    emp_a = _emp("김테스트치료사")
    emp_b = _emp("이테스트치료사")

    client.post("/api/employee-duties", json={
        "employee_id": emp_a, "duty_date": date, "duty_type": "night",
    })
    r = client.post("/api/employee-duties/bulk-set", json={
        "duty_date": date, "duty_type": "morning",
        "items": [{"employee_id": emp_b}],
    })
    assert r.status_code == 200

    night = client.get(f"/api/employee-duties?date={date}&duty_type=night").json()
    morning = client.get(f"/api/employee-duties?date={date}&duty_type=morning").json()
    assert [x["employee_id"] for x in night] == [emp_a]
    assert [x["employee_id"] for x in morning] == [emp_b]

    # 아침당직을 빈 목록으로 교체해도 야간은 그대로
    client.post("/api/employee-duties/bulk-set", json={
        "duty_date": date, "duty_type": "morning", "items": [],
    })
    assert client.get(f"/api/employee-duties?date={date}&duty_type=morning").json() == []
    assert len(client.get(f"/api/employee-duties?date={date}&duty_type=night").json()) == 1


def test_bulk_add_carries_duty_type(client):
    date = _BASE + "13"
    _clear(client, date)
    emp = _emp()

    r = client.post("/api/employee-duties/bulk-add", json={
        "items": [{"employee_id": emp, "duty_date": date}],
        "duty_type": "morning",
    })
    assert r.status_code == 200
    rows = _duties_on(client, date)
    assert len(rows) == 1
    assert rows[0]["duty_type"] == "morning"


def test_lunch_duty_type(client):
    """점심당직(lunch) — 아침/야간과 독립으로 같은 날 등록/필터/독립 삭제."""
    date = _BASE + "16"
    _clear(client, date)
    emp = _emp()

    for t in ("morning", "lunch", "night"):
        r = client.post("/api/employee-duties", json={
            "employee_id": emp, "duty_date": date, "duty_type": t,
        })
        assert r.status_code == 200 and r.json()["duty_type"] == t

    assert len(_duties_on(client, date)) == 3
    lunch = client.get(f"/api/employee-duties?date={date}&duty_type=lunch").json()
    assert len(lunch) == 1 and lunch[0]["duty_type"] == "lunch"

    # 점심만 비워도 아침/야간은 그대로 (유형별 독립)
    client.post("/api/employee-duties/bulk-set", json={
        "duty_date": date, "duty_type": "lunch", "items": [],
    })
    assert client.get(f"/api/employee-duties?date={date}&duty_type=lunch").json() == []
    assert len(_duties_on(client, date)) == 2


def test_invalid_duty_type_rejected(client):
    date = _BASE + "14"
    emp = _emp()

    r = client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "afternoon",
    })
    assert r.status_code == 400

    r = client.post("/api/employee-duties/bulk-set", json={
        "duty_date": date, "duty_type": "afternoon", "items": [],
    })
    assert r.status_code == 400

    r = client.get(f"/api/employee-duties?date={date}&duty_type=afternoon")
    assert r.status_code == 400


# ──────────────────────── 8. m043 마이그레이션 (구 스키마 → duty_type) ────────────────────────


def test_m043_backfills_night_and_relaxes_unique():
    """구 스키마(2컬럼 UNIQUE) DB 에 m043 적용 시:
    기존 행 duty_type='night' 이전 + 아침/야간 동시 등록 가능 + 멱등."""
    import sqlite3

    import pytest

    from app.migrations import m043_duty_type as m043

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE employee_duties ("
        " id VARCHAR(32) PRIMARY KEY,"
        " employee_id VARCHAR(32) NOT NULL,"
        " duty_date VARCHAR(10) NOT NULL,"
        " memo TEXT DEFAULT '',"
        " created_at DATETIME,"
        " CONSTRAINT uq_employee_duty_date UNIQUE (employee_id, duty_date)"
        ")"
    )
    # m039 가 만들던 옛 2컬럼 UNIQUE INDEX 재현 (신규 DB 경로)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_duty_date "
        "ON employee_duties (employee_id, duty_date)"
    )
    conn.execute(
        "INSERT INTO employee_duties (id, employee_id, duty_date, memo)"
        " VALUES ('d1', 'e1', '2099-01-01', '기존당직')"
    )
    conn.commit()

    m043.up(conn)

    # 기존 행은 야간으로 이전 (id/메모 보존)
    rows = conn.execute(
        "SELECT id, duty_type, memo FROM employee_duties"
    ).fetchall()
    assert rows == [("d1", "night", "기존당직")]

    # 같은 직원·같은 날 아침당직 추가 가능 (UNIQUE 완화 확인)
    conn.execute(
        "INSERT INTO employee_duties (id, employee_id, duty_date, duty_type)"
        " VALUES ('d2', 'e1', '2099-01-01', 'morning')"
    )
    # 같은 (직원, 날짜, 유형) 중복은 여전히 차단
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO employee_duties (id, employee_id, duty_date, duty_type)"
            " VALUES ('d3', 'e1', '2099-01-01', 'morning')"
        )

    # 멱등 — 두 번 실행해도 안전, 데이터 유지
    m043.up(conn)
    assert conn.execute("SELECT COUNT(*) FROM employee_duties").fetchone()[0] == 2


# ──────────────────────── 9. 야간당직 퇴근시각 / 시간 집계 (end_time) ────────────────────────


def test_overtime_minutes_pure():
    """초과분 계산 규칙 — 순수 함수 (기준 18:30)."""
    b = "18:30"
    assert _duty_overtime_minutes("21:00", b) == 150       # 같은 저녁
    assert _duty_overtime_minutes("01:00", b) == 390       # 자정 넘김
    assert _duty_overtime_minutes("18:30", b) == 0         # 정각 = 0
    assert _duty_overtime_minutes("", b) == 0              # 미입력
    assert _duty_overtime_minutes("17:00", b) == 0         # 기준 이전 오후 = 오입력
    assert _duty_overtime_minutes("bad", b) == 0           # 형식 오류
    assert _duty_overtime_minutes("20:00", "19:00") == 60  # 다른 기준값 반영


def test_end_time_roundtrip_create_and_list(client):
    date = _BASE + "20"
    _clear(client, date)
    emp = _emp()

    r = client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "night", "end_time": "21:00",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["end_time"] == "21:00"
    assert body["overtime_minutes"] == _duty_overtime_minutes("21:00", _duty_baseline())

    rows = _duties_on(client, date)
    assert rows[0]["end_time"] == "21:00"
    assert rows[0]["overtime_minutes"] == _duty_overtime_minutes("21:00", _duty_baseline())


def test_upsert_updates_end_time(client):
    date = _BASE + "21"
    _clear(client, date)
    emp = _emp()
    client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "night", "end_time": "20:00",
    })
    client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "night", "end_time": "22:30",
    })
    rows = _duties_on(client, date)
    assert len(rows) == 1
    assert rows[0]["end_time"] == "22:30"


def test_bulk_set_carries_per_employee_end_time(client):
    date = _BASE + "22"
    _clear(client, date)
    emp_a = _emp("김테스트치료사")
    emp_b = _emp("이테스트치료사")
    r = client.post("/api/employee-duties/bulk-set", json={
        "duty_date": date, "duty_type": "night",
        "items": [
            {"employee_id": emp_a, "end_time": "20:00"},
            {"employee_id": emp_b, "end_time": "23:00"},
        ],
    })
    assert r.status_code == 200
    got = {x["employee_id"]: x["end_time"] for x in _duties_on(client, date)}
    assert got[emp_a] == "20:00"
    assert got[emp_b] == "23:00"


def test_bulk_add_common_end_time(client):
    dates = [_BASE + "23", _BASE + "24"]
    for d in dates:
        _clear(client, d)
    emp = _emp()
    r = client.post("/api/employee-duties/bulk-add", json={
        "items": [{"employee_id": emp, "duty_date": d} for d in dates],
        "duty_type": "night", "end_time": "21:30",
    })
    assert r.status_code == 200
    for d in dates:
        rows = _duties_on(client, d)
        assert rows[0]["end_time"] == "21:30"


def test_morning_duty_ignores_end_time(client):
    date = _BASE + "25"
    _clear(client, date)
    emp = _emp()
    # 아침당직에 end_time 을 줘도 초과분은 0 (시간 개념 없음)
    client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "morning", "end_time": "21:00",
    })
    rows = client.get(f"/api/employee-duties?date={date}&duty_type=morning").json()
    assert rows[0]["overtime_minutes"] == 0


def test_invalid_end_time_rejected(client):
    date = _BASE + "26"
    emp = _emp()
    r = client.post("/api/employee-duties", json={
        "employee_id": emp, "duty_date": date, "duty_type": "night", "end_time": "25:99",
    })
    assert r.status_code == 400
    r = client.post("/api/employee-duties/bulk-set", json={
        "duty_date": date, "duty_type": "night",
        "items": [{"employee_id": emp, "end_time": "nope"}],
    })
    assert r.status_code == 400


# ──────────────────────── 10. m045 마이그레이션 (end_time 컬럼) ────────────────────────
# NOTE: v1.3.56 에서 기록탭 memo 마이그레이션이 m044 를 선점 → 야간당직 end_time 은 m045 로 재부여.


def test_m045_adds_end_time_column_idempotent():
    """구 스키마(end_time 없음) DB 에 m045 적용 시 컬럼 추가·데이터 보존·멱등."""
    import sqlite3

    from app.migrations import m045_duty_end_time as m044

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE employee_duties ("
        " id VARCHAR(32) PRIMARY KEY,"
        " employee_id VARCHAR(32) NOT NULL,"
        " duty_date VARCHAR(10) NOT NULL,"
        " duty_type VARCHAR(10) NOT NULL DEFAULT 'night',"
        " memo TEXT DEFAULT '',"
        " created_at DATETIME"
        ")"
    )
    conn.execute(
        "INSERT INTO employee_duties (id, employee_id, duty_date, duty_type, memo)"
        " VALUES ('d1', 'e1', '2099-01-01', 'night', '기존당직')"
    )
    conn.commit()

    m044.up(conn)

    cols = {row[1] for row in conn.execute("PRAGMA table_info(employee_duties)")}
    assert "end_time" in cols
    # 기존 행 보존, 새 컬럼은 NULL
    row = conn.execute(
        "SELECT id, memo, end_time FROM employee_duties WHERE id='d1'"
    ).fetchone()
    assert row == ("d1", "기존당직", None)

    # 멱등 — 두 번 실행해도 안전
    m044.up(conn)
    assert conn.execute("SELECT COUNT(*) FROM employee_duties").fetchone()[0] == 1
