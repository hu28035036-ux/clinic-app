"""015 — v1.3.4: Employee.permission_level VARCHAR DEFAULT 'staff' (post-19-P / 20-3-2).

용도:
  F-11 권한 다중 등급 도입 — `Employee` 테이블에 `permission_level VARCHAR(20)
  DEFAULT 'staff'` 컬럼 추가. 사용자 §4-6 권장값:
  - (a) 3등급: staff / admin / super
  - (i) admin 별도 게이트 보존 (기존 PBKDF2 + 5회 잠금 + 8h 세션 + require_admin
    86 endpoint 모두 무수정)
  - (ii) viewer 미도입 — 후속 결정

원칙 (docs/ai_rag_migration_plan.md §0/§3 정합):
  - DROP/DELETE/TRUNCATE 절대 없음 — 데이터 영구 보존.
  - 컬럼 추가 + DEFAULT 'staff' — 기존 직원 모두 'staff' 자동 세팅.
  - 두 번 실행해도 안전 (idempotent).
  - 테이블 부재 시 skip.

호환성:
  - 기존 `role` 컬럼 (therapist / doctor) 보존 — *직군 분기*.
  - `permission_level` 은 *권한 등급* — 직군과 별개 (의료직군 + 권한 등급 둘 다).
  - 기존 admin 로그인 흐름 (require_admin) 보존 — *권한 등급 변경은 admin 권한*.
  - 응답 dict 신설 키 `permission_level` 만 추가 (기존 10키 보존, 11키로 확장).
"""

MIGRATION_ID = 15
DESCRIPTION = "Employee.permission_level VARCHAR(20) DEFAULT 'staff' (post-19-P / F-11 권한 다중 등급)"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _column_exists(cur, table: str, column: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def up(conn):
    cur = conn.cursor()

    # ── Employee.permission_level 컬럼 추가 (idempotent) ──
    if _table_exists(cur, "employees"):
        if not _column_exists(cur, "employees", "permission_level"):
            cur.execute(
                "ALTER TABLE employees ADD COLUMN permission_level VARCHAR(20) "
                "DEFAULT 'staff' NOT NULL"
            )

    conn.commit()
