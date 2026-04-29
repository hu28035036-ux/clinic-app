"""006 — v1.2.7: 집계 수동 카운트 테이블 추가 (manual_counts).

용도:
  체외충격파 등 **당일 내방 환자**처럼 예약 등록 없이 바로 진행한 경우,
  집계/통계에 즉시 반영할 수 있도록 직원이 표에 숫자만 입력하면 저장되는
  "수동 카운트" 테이블.

구조:
  (count_date, therapist_id, treatment_code) 당 1개 행
  count 를 UPSERT 방식으로 직접 덮어쓰기.

집계/통계 API 는 실제 예약 데이터 + 이 테이블의 count 를 **합산** 해서 반환.

IF NOT EXISTS 로 멱등성 보장 — 여러 번 실행되어도 안전.
"""

MIGRATION_ID = 6
DESCRIPTION = "집계 수동 카운트 테이블 추가 (manual_counts) — 체외충격파 당일 환자 등"


def up(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS manual_counts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            count_date     TEXT NOT NULL,              -- 'YYYY-MM-DD'
            therapist_id   TEXT,                       -- NULL = 미배정
            treatment_code TEXT NOT NULL,              -- 'eswt' 등
            count          INTEGER NOT NULL DEFAULT 0,
            updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(count_date, therapist_id, treatment_code)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_manual_counts_date
            ON manual_counts(count_date)
    """)
    conn.commit()
