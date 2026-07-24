"""045 — 야간당직 퇴근시각 (employee_duties.end_time).

용도:
  야간당직(duty_type='night')에 실제 퇴근시각("HH:MM")을 직원별로 기록.
  기준 퇴근시간(config.duty_baseline_end_time) 초과분을 야간당직 시간으로 집계.
  아침당직(morning)은 미사용(NULL) — 값이 없으면 시간집계 0.

원칙 (m043 가드 패턴 정합):
  - DROP/DELETE/TRUNCATE 절대 없음. ADD COLUMN 만.
  - 컬럼 부재 시에만 추가 (멱등) — 두 번 실행해도 안전.
  - 기존 행은 end_time=NULL 로 남아 시간집계에 영향 없음 (데이터 파괴 없음).

분담:
  - 신규 DB: Base.metadata.create_all 이 새 모델(EmployeeDuty.end_time)로 테이블 생성.
  - 기존 DB: 본 마이그레이션이 end_time 컬럼을 멱등 보강.
"""

MIGRATION_ID = 45
DESCRIPTION = "야간당직 퇴근시각 — employee_duties.end_time 컬럼 추가 (HH:MM, nullable)"


def _columns(cur, table):
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}


def up(conn):
    cur = conn.cursor()

    cols = _columns(cur, "employee_duties")
    if not cols:
        # 테이블이 아직 없음 — create_all(새 모델) 분담. 여기선 할 일 없음.
        conn.commit()
        return

    if "end_time" not in cols:
        cur.execute("ALTER TABLE employee_duties ADD COLUMN end_time VARCHAR(5)")

    conn.commit()
