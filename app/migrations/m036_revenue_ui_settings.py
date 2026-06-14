"""036 - synced revenue UI settings."""

MIGRATION_ID = 36
DESCRIPTION = "synced revenue UI settings"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    cols = _columns(cur, "system_settings")
    if cols and "revenue_ui_settings_json" not in cols:
        cur.execute(
            "ALTER TABLE system_settings "
            "ADD COLUMN revenue_ui_settings_json TEXT NOT NULL DEFAULT '{}'"
        )
    conn.commit()
