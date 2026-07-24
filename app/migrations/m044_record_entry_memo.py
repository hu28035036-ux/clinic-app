"""044 - add optional memo to record entries."""

MIGRATION_ID = 44
DESCRIPTION = "memo column for record entries"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    cols = _columns(cur, "record_entries")
    if "memo" not in cols:
        cur.execute(
            "ALTER TABLE record_entries "
            "ADD COLUMN memo TEXT NOT NULL DEFAULT ''"
        )
    conn.commit()
