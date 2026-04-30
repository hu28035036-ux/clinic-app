"""010 — employees.hire_date 컬럼 추가 (치료사 입사일).

치료사 정보 수정 모달에서 입사일을 입력/관리할 수 있도록
Employee 에 입사일 컬럼을 추가한다.

원칙:
  - IF NOT EXISTS / 컬럼 체크로 멱등성 보장.
  - 기존 row 는 NULL 유지 (선택값).
  - DROP / DELETE 절대 없음.
"""

MIGRATION_ID = 10
DESCRIPTION = "employees.hire_date 컬럼 추가 (YYYY-MM-DD, nullable)"


def up(conn):
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(employees)").fetchall()]
    if "hire_date" not in cols:
        cur.execute(
            "ALTER TABLE employees "
            "ADD COLUMN hire_date VARCHAR(10)"
        )
    conn.commit()
