"""033 - revenue record field memos."""

MIGRATION_ID = 33
DESCRIPTION = "field-level memos for daily revenue records"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    cols = _columns(cur, "revenue_records")
    if "field_memos_json" not in cols:
        cur.execute(
            "ALTER TABLE revenue_records "
            "ADD COLUMN field_memos_json TEXT NOT NULL DEFAULT '{}'"
        )
    conn.commit()
