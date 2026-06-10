"""031 - signed revenue adjustments."""

MIGRATION_ID = 31
DESCRIPTION = "signed revenue adjustments and daily report deduction fields"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    cols = _columns(cur, "revenue_records")
    if "health_living_fee" not in cols:
        cur.execute(
            "ALTER TABLE revenue_records "
            "ADD COLUMN health_living_fee INTEGER NOT NULL DEFAULT 0"
        )
    if "disability_fund" not in cols:
        cur.execute(
            "ALTER TABLE revenue_records "
            "ADD COLUMN disability_fund INTEGER NOT NULL DEFAULT 0"
        )
    if "unpaid_amount" in cols:
        cur.execute(
            "UPDATE revenue_records "
            "SET unpaid_amount = -ABS(unpaid_amount) "
            "WHERE unpaid_amount > 0"
        )
    conn.commit()
