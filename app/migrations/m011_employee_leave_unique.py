"""011 — v1.3.3: EmployeeLeave (employee_id, leave_date) UNIQUE 제약 추가.

용도:
  다중 워커 race 시 동일 직원·동일 날짜 휴무 row 가 중복 생성되는 것을
  DB 레벨에서 차단. v1 AI 휴무 액션 출시 후 정합성 보강.

⚠️ 파괴적 마이그레이션 — 운영 데이터 정책 예외:
  본 프로젝트 표준은 DROP/DELETE/TRUNCATE 금지지만, 신규 UNIQUE 제약을
  적용하려면 기존 중복 row 가 있을 경우 1건만 남기고 나머지를 삭제해야
  한다. 이는 의도적 정책 예외이며, 다음 안전 가드를 둔다:
    1) 자동 백업: 운영자는 마이그레이션 실행 전(즉, 업데이트 적용 전)
       %APPDATA%/도수치료예약/clinic.db 를 별도 위치로 백업해 두기 권장.
       프로그램 자체의 자동 백업(backups/)은 매일 도므로 직전 24h 백업이
       이미 존재하지만, 안전을 위해 수동 백업 1부 추가 권장.
    2) 사전 카운트: 정리 전 중복 그룹 수를 stderr 로 로깅 (_log).
    3) 삭제 대상 식별: 삭제될 row 의 (id, employee_id, leave_date,
       created_at) 를 stderr 로 로깅 — 사후 추적 가능.
    4) 정리 후 검증: 정리 SQL 종료 후 잔존 중복이 있으면 경고 로그
       (다음 단계의 인덱스 생성이 IntegrityError 로 실패 → 마이그레이션
       전체 롤백 → 사용자 환경엔 변경 없음).

보존 우선순위 (결정적):
  (employee_id, leave_date) 그룹 내에서 (created_at DESC, id DESC)
  최상위 1건 보존, 나머지 DELETE. tie-breaker 로 id (UUID hex) 추가하여
  동일 마이크로초 race 시에도 결정적.

기술적 세부:
  - PRAGMA index_list 가드로 인덱스 멱등성 보장.
  - SQLite 는 CREATE UNIQUE INDEX 를 기존 테이블에 즉시 적용 가능 →
    테이블 재생성 불필요.
"""

MIGRATION_ID = 11
DESCRIPTION = "EmployeeLeave (employee_id, leave_date) UNIQUE 제약"

INDEX_NAME = "uq_employee_leave_date"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _index_exists(cur, table: str, index: str) -> bool:
    rows = cur.execute(f"PRAGMA index_list({table})").fetchall()
    # PRAGMA index_list 결과: (seq, name, unique, origin, partial)
    return any(r[1] == index for r in rows)


def _count_duplicate_groups(cur) -> int:
    row = cur.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT employee_id, leave_date
            FROM employee_leaves
            GROUP BY employee_id, leave_date
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()
    return int(row[0]) if row else 0


def _log(msg: str) -> None:
    import sys
    try:
        print(f"[MIGRATE m011] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


def up(conn):
    cur = conn.cursor()

    if not _table_exists(cur, "employee_leaves"):
        # 테이블 자체가 없으면 다음 부팅의 create_all 이 신규 스키마(UniqueConstraint 포함)
        # 로 생성한다. 마이그레이션은 no-op.
        return

    # ── Step 1: 중복 row 정리 (정책 예외) ──
    dup_groups = _count_duplicate_groups(cur)
    if dup_groups > 0:
        _log(f"중복 그룹 {dup_groups}개 발견 → 최신 row 1건만 보존하고 정리")
        # 삭제 대상 식별 — 사후 추적용 stderr 로깅 (id 까지 포함)
        delete_targets = cur.execute(
            """
            SELECT id, employee_id, leave_date, created_at FROM employee_leaves
            WHERE id NOT IN (
                SELECT id FROM employee_leaves el2
                WHERE el2.employee_id = employee_leaves.employee_id
                  AND el2.leave_date = employee_leaves.leave_date
                ORDER BY el2.created_at DESC, el2.id DESC
                LIMIT 1
            )
            """
        ).fetchall()
        _log(f"삭제 대상 {len(delete_targets)}건 (id, employee_id, leave_date, created_at):")
        for row in delete_targets:
            _log(f"  - {row}")

        cur.execute(
            """
            DELETE FROM employee_leaves
            WHERE id NOT IN (
                SELECT id FROM employee_leaves el2
                WHERE el2.employee_id = employee_leaves.employee_id
                  AND el2.leave_date = employee_leaves.leave_date
                ORDER BY el2.created_at DESC, el2.id DESC
                LIMIT 1
            )
            """
        )
        remaining = _count_duplicate_groups(cur)
        if remaining > 0:
            # 정리 SQL 의 가정이 깨졌다는 신호. 인덱스 생성은 IntegrityError 로 실패할 것.
            _log(f"⚠️ 정리 후에도 중복 그룹 {remaining}개 잔존 — 인덱스 생성 실패 예상")

    # ── Step 2: UNIQUE INDEX 생성 (멱등) ──
    if not _index_exists(cur, "employee_leaves", INDEX_NAME):
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} "
            "ON employee_leaves(employee_id, leave_date)"
        )

    conn.commit()
