"""EmployeeLeave (employee_id, leave_date) UNIQUE 제약 회귀 테스트.

m011 마이그레이션이 적용된 환경에서:
1. 인덱스 자체가 존재하는지 (PRAGMA index_list).
2. 동일 (employee_id, leave_date) 두 번 INSERT 시 IntegrityError.
3. m011 의 중복 정리 SQL 이 (created_at DESC, id DESC) 기준 1건만 남기는지.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from tests.harness.seed_data import get_test_therapist_id


def test_uq_employee_leave_date_index_exists(client):
    """PRAGMA index_list 결과에 uq_employee_leave_date (unique=1) 포함."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        # raw sqlite3.Connection 으로 PRAGMA 직접 실행 (SQLAlchemy 버전 무관)
        raw = db.connection().connection
        cur = raw.cursor()
        cur.execute("PRAGMA index_list('employee_leaves')")
        indices = cur.fetchall()
    finally:
        db.close()

    # PRAGMA index_list 컬럼: (seq, name, unique, origin, partial)
    matches = [r for r in indices if r[1] == "uq_employee_leave_date"]
    assert matches, (
        f"uq_employee_leave_date 인덱스가 없습니다. 발견된 인덱스: {indices}"
    )
    assert int(matches[0][2]) == 1, "uq_employee_leave_date 가 UNIQUE 가 아닙니다."


def test_duplicate_insert_raises_integrity_error(client):
    """동일 (employee_id, leave_date) 두 번 add+commit 시 IntegrityError."""
    from app.database import SessionLocal
    from app.models import models

    eid = get_test_therapist_id("김테스트치료사")
    test_date = "2099-08-21"

    db = SessionLocal()
    try:
        # 사전 정리 (재실행 안전)
        db.query(models.EmployeeLeave).filter(
            models.EmployeeLeave.employee_id == eid,
            models.EmployeeLeave.leave_date == test_date,
        ).delete()
        db.commit()

        # 첫 번째 INSERT 는 성공
        db.add(models.EmployeeLeave(
            employee_id=eid, leave_date=test_date,
            leave_type="full", leave_kind="annual",
        ))
        db.commit()

        # 두 번째 INSERT 는 UNIQUE 제약 위반 → IntegrityError
        db.add(models.EmployeeLeave(
            employee_id=eid, leave_date=test_date,
            leave_type="am", leave_kind="monthly",
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 정리
        db.query(models.EmployeeLeave).filter(
            models.EmployeeLeave.employee_id == eid,
            models.EmployeeLeave.leave_date == test_date,
        ).delete()
        db.commit()
    finally:
        db.close()


def test_m011_cleanup_keeps_latest_by_created_at(client, tmp_path):
    """m011 마이그레이션 함수 단위 테스트.

    독립 SQLite 파일을 만들어 employee_leaves 테이블 + 중복 row 3개 (created_at 다르게)
    를 직접 INSERT 한 뒤 m011.up() 실행 → 1건만 남는지, 그 row 가 가장 최근
    created_at 인지 검증.
    """
    import sqlite3

    from app.migrations.m011_employee_leave_unique import (
        _count_duplicate_groups,
        up,
    )

    db_file = tmp_path / "m011_unit.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    # employee_leaves 테이블 생성 (실제 모델과 동일한 핵심 컬럼)
    cur.execute(
        """
        CREATE TABLE employee_leaves (
            id          VARCHAR(32) PRIMARY KEY,
            employee_id VARCHAR(32) NOT NULL,
            leave_date  VARCHAR(10) NOT NULL,
            leave_type  VARCHAR(10) DEFAULT 'full',
            leave_kind  VARCHAR(10) DEFAULT 'annual',
            memo        TEXT DEFAULT '',
            created_at  DATETIME
        )
        """
    )
    conn.commit()

    eid = "emp_unit_001"
    leave_date = "2099-09-15"

    # 3개 중복 row — created_at 이 다르고, id 도 다름. 중간 시각의 row 가 보존되면 안 됨.
    base = datetime(2026, 1, 1, 12, 0, 0)
    rows = [
        ("id_oldest", eid, leave_date, "full", "annual", "old", base.isoformat()),
        ("id_middle", eid, leave_date, "am",   "annual", "mid", (base + timedelta(hours=1)).isoformat()),
        ("id_latest", eid, leave_date, "pm",   "monthly", "new", (base + timedelta(hours=2)).isoformat()),
    ]
    cur.executemany(
        "INSERT INTO employee_leaves (id, employee_id, leave_date, leave_type, leave_kind, memo, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()

    # 사전 검증 — 중복 그룹 1개
    assert _count_duplicate_groups(cur) == 1

    # 마이그레이션 실행
    up(conn)

    # 사후 검증 — 중복 그룹 0개, row 1건만 남음, 가장 최근 row 보존
    assert _count_duplicate_groups(cur) == 0
    survivors = cur.execute(
        "SELECT id, leave_type, memo FROM employee_leaves WHERE employee_id=? AND leave_date=?",
        (eid, leave_date),
    ).fetchall()
    assert len(survivors) == 1, f"중복 정리 후에도 {len(survivors)}건 잔존: {survivors}"
    assert survivors[0][0] == "id_latest", f"가장 최근 row 가 보존되지 않음: {survivors[0]}"

    # 인덱스 확인
    indices = cur.execute("PRAGMA index_list('employee_leaves')").fetchall()
    assert any(r[1] == "uq_employee_leave_date" and int(r[2]) == 1 for r in indices), (
        f"uq_employee_leave_date 인덱스 미생성: {indices}"
    )

    # 멱등성 확인 — 두 번째 호출도 에러 없음
    up(conn)

    conn.close()
