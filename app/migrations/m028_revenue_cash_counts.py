"""028 - revenue cash denomination counts."""

MIGRATION_ID = 28
DESCRIPTION = "cash denomination counts for daily revenue records"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    if "cash_counts_json" not in _columns(cur, "revenue_records"):
        cur.execute(
            "ALTER TABLE revenue_records "
            "ADD COLUMN cash_counts_json TEXT NOT NULL DEFAULT '{}'"
        )
    conn.commit()
