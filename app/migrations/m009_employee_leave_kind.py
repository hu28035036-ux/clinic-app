"""009 — employee_leaves.leave_kind 컬럼 추가 (연차/월차).

휴무 관리 모달에서 치료사별 휴가 종류(연차 annual / 월차 monthly)를 선택할 수 있도록
EmployeeLeave 에 분류 컬럼을 추가한다.

원칙:
  - IF NOT EXISTS / 컬럼 체크로 멱등성 보장.
  - 기존 row 는 NULL/빈문자열 → 'annual' 로 backfill (사용자 결정).
  - DROP / DELETE 절대 없음.
"""

MIGRATION_ID = 9
DESCRIPTION = "employee_leaves.leave_kind 컬럼 추가 (annual/monthly, 기존 annual 로 backfill)"


def up(conn):
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(employee_leaves)").fetchall()]
    if "leave_kind" not in cols:
        cur.execute(
            "ALTER TABLE employee_leaves "
            "ADD COLUMN leave_kind VARCHAR(10) DEFAULT 'annual'"
        )
    cur.execute(
        "UPDATE employee_leaves SET leave_kind = 'annual' "
        "WHERE leave_kind IS NULL OR leave_kind = ''"
    )
    conn.commit()
