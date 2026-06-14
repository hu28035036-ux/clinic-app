"""035 - add daily date to record entries."""

MIGRATION_ID = 35
DESCRIPTION = "daily date for record entries"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    cols = _columns(cur, "record_entries")
    if "record_date" not in cols:
        cur.execute(
            "ALTER TABLE record_entries "
            "ADD COLUMN record_date TEXT NOT NULL DEFAULT ''"
        )
        cur.execute(
            """
            UPDATE record_entries
               SET record_date = COALESCE(NULLIF(substr(created_at, 1, 10), ''), date('now'))
             WHERE record_date = ''
            """
        )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_entries_record_date "
        "ON record_entries(record_date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_entries_tab_date "
        "ON record_entries(tab_key, record_date)"
    )
    conn.commit()
