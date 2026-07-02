"""039 — 당직 관리 테이블 (employee_duties) 신설.

용도:
  휴무일 관리(employee_leaves)와 같은 캘린더형 당직 관리. 유형/종류 구분 없이
  직원 + 날짜 + 메모만 보관. 정보성 기능 — 예약 차단/통계 로직과 무관.

원칙 (m016/m018 패턴 정합):
  - DROP/DELETE/TRUNCATE 절대 없음.
  - CREATE TABLE IF NOT EXISTS 멱등 가드 + Base.metadata.create_all 분담.
  - 두 번 실행해도 안전.

분담:
  - 테이블 생성: ``Base.metadata.create_all`` (ORM 모델 EmployeeDuty 기준).
  - 본 마이그레이션은 신규 테이블 멱등 보강 — 테이블/인덱스/UNIQUE 보장.
"""

MIGRATION_ID = 39
DESCRIPTION = "당직 관리 테이블 (employee_duties) 신설 + UNIQUE(employee_id, duty_date)"


def up(conn):
    cur = conn.cursor()

    # ── 테이블 본체 (create_all 분담이나, 마이그레이션 단독으로도 안전하게) ──
    cur.execute(
        "CREATE TABLE IF NOT EXISTS employee_duties ("
        " id VARCHAR(32) PRIMARY KEY,"
        " employee_id VARCHAR(32) NOT NULL,"
        " duty_date VARCHAR(10) NOT NULL,"
        " memo TEXT DEFAULT '',"
        " created_at DATETIME"
        ")"
    )

    # ── 인덱스 / UNIQUE 멱등 보강 ──
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_duties_date "
        "ON employee_duties (duty_date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_duties_employee_id "
        "ON employee_duties (employee_id)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_duty_date "
        "ON employee_duties (employee_id, duty_date)"
    )

    conn.commit()
