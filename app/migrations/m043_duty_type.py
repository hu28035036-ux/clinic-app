"""043 — 당직 아침/야간 분리 (employee_duties.duty_type).

용도:
  당직 관리를 아침당직(morning) / 야간당직(night) 으로 분리.
  기존 당직 데이터는 전부 야간당직('night') 으로 이전 (기존 '당직 관리' 탭이
  '야간당직' 으로 이름이 바뀌는 것과 정합).

UNIQUE 제약 변경이 필요한 이유:
  기존 UNIQUE(employee_id, duty_date) 는 같은 직원이 같은 날 아침당직과
  야간당직을 동시에 서는 것을 막는다 → (employee_id, duty_date, duty_type) 로
  확장해야 함. SQLite 는 테이블 내장(inline) UNIQUE 제약을 ALTER 로 못 바꾸므로
  copy-rename 재구성이 유일한 방법이다.

데이터 보존 (원칙 예외 아님):
  - 재구성은 INSERT SELECT 로 전 행(id 포함)을 새 테이블에 복사한 뒤 교체 —
    데이터 파괴 없음. id 가 보존되므로 sync(entity=employee_duty) 참조도 안전.
  - 전 과정이 단일 커밋(트랜잭션) — 중간 실패 시 원본 그대로.
  - 두 번 실행해도 안전 (duty_type 존재 시 재구성 생략).

m039 의 UNIQUE INDEX 정리:
  신규 DB 는 create_all(새 모델) → m039 순으로 돌아서 m039 가 옛 2컬럼 UNIQUE
  INDEX(uq_employee_duty_date) 를 다시 만든다 → 본 마이그레이션(항상 m039 뒤)이
  DROP INDEX IF EXISTS 로 제거해 아침+야간 동시 등록을 보장한다.
  (인덱스 제거는 데이터 파괴가 아님.)
"""

MIGRATION_ID = 43
DESCRIPTION = "당직 아침/야간 분리 — duty_type 컬럼 + UNIQUE(employee_id, duty_date, duty_type)"


def _columns(cur, table):
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}


def up(conn):
    cur = conn.cursor()

    cols = _columns(cur, "employee_duties")
    if not cols:
        # 테이블이 아직 없음 — create_all(새 모델) 분담. 인덱스 보강만 아래에서.
        pass
    elif "duty_type" not in cols:
        # ── copy-rename 재구성 (데이터 전량 보존, id 유지) ──
        cur.execute(
            "CREATE TABLE IF NOT EXISTS employee_duties_new ("
            " id VARCHAR(32) PRIMARY KEY,"
            " employee_id VARCHAR(32) NOT NULL REFERENCES employees(id),"
            " duty_date VARCHAR(10) NOT NULL,"
            " duty_type VARCHAR(10) NOT NULL DEFAULT 'night',"
            " memo TEXT DEFAULT '',"
            " created_at DATETIME,"
            " CONSTRAINT uq_employee_duty_date_type"
            "  UNIQUE (employee_id, duty_date, duty_type)"
            ")"
        )
        cur.execute(
            "INSERT OR IGNORE INTO employee_duties_new"
            " (id, employee_id, duty_date, duty_type, memo, created_at)"
            " SELECT id, employee_id, duty_date, 'night', memo, created_at"
            " FROM employee_duties"
        )
        cur.execute("DROP TABLE employee_duties")
        cur.execute("ALTER TABLE employee_duties_new RENAME TO employee_duties")

    # ── 값 보정 (NULL/빈 값 → night) — 어떤 경로로 생겼든 멱등 정리 ──
    if "duty_type" in _columns(cur, "employee_duties"):
        cur.execute(
            "UPDATE employee_duties SET duty_type = 'night'"
            " WHERE duty_type IS NULL OR duty_type = ''"
        )

    # ── 옛 2컬럼 UNIQUE INDEX 제거 (m039 잔재 — 아침+야간 동시 등록 차단 방지) ──
    cur.execute("DROP INDEX IF EXISTS uq_employee_duty_date")

    # ── 인덱스 멱등 보강 ──
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_duties_date "
        "ON employee_duties (duty_date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_duties_employee_id "
        "ON employee_duties (employee_id)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_duty_date_type "
        "ON employee_duties (employee_id, duty_date, duty_type)"
    )

    conn.commit()
