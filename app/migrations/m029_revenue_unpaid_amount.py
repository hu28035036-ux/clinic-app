"""029 - revenue unpaid amount."""

MIGRATION_ID = 29
DESCRIPTION = "unpaid amount for daily revenue records"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    if "unpaid_amount" not in _columns(cur, "revenue_records"):
        cur.execute(
            "ALTER TABLE revenue_records "
            "ADD COLUMN unpaid_amount INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()
