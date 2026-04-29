"""005 — v1.2.3: 치료항목에 수가(price) + 인센티브(pct/amount) 컬럼 추가.

- price            : 수가(가격, 원 단위). 기본 0.
- incentive_pct    : 치료사 인센티브 % (예: 10.0 = 10%). NULL 허용.
- incentive_amount : 치료사 인센티브 고정 금액(원). NULL 허용.

사용 규약(앱 레벨 강제):
  - incentive_pct 와 incentive_amount 는 "둘 중 하나만" 입력.
  - 계산 우선순위: incentive_amount → incentive_pct → 0
  - pct 는 price * pct/100 로 계산. amount 는 그대로 사용.

IF NOT EXISTS 가 SQLite ALTER 에는 없으므로 PRAGMA table_info 로 존재 체크.
"""

MIGRATION_ID = 5
DESCRIPTION = "치료항목 수가/인센티브 컬럼 추가 (price, incentive_pct, incentive_amount)"


def _column_exists(cur, table: str, column: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def up(conn):
    cur = conn.cursor()
    # price — NOT NULL, DEFAULT 0 (기존 행 모두 0 으로)
    if not _column_exists(cur, "treatments", "price"):
        cur.execute("ALTER TABLE treatments ADD COLUMN price INTEGER NOT NULL DEFAULT 0")
    # incentive_pct — NULL 허용 (REAL). 기본 NULL.
    if not _column_exists(cur, "treatments", "incentive_pct"):
        cur.execute("ALTER TABLE treatments ADD COLUMN incentive_pct REAL")
    # incentive_amount — NULL 허용 (INTEGER).
    if not _column_exists(cur, "treatments", "incentive_amount"):
        cur.execute("ALTER TABLE treatments ADD COLUMN incentive_amount INTEGER")
    conn.commit()
