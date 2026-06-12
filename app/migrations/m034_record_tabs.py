"""034 - record tab settings and entries."""

MIGRATION_ID = 34
DESCRIPTION = "record tab settings and entries"


def up(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS record_tab_settings (
            id TEXT PRIMARY KEY,
            tab_key TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL DEFAULT '',
            category_id TEXT NOT NULL DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS record_entries (
            id TEXT PRIMARY KEY,
            tab_key TEXT NOT NULL,
            chart_no TEXT NOT NULL DEFAULT '',
            patient_name TEXT NOT NULL DEFAULT '',
            employee_id TEXT NOT NULL,
            employee_name_snapshot TEXT NOT NULL DEFAULT '',
            employee_category_id_snapshot TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_tab_settings_tab_key "
        "ON record_tab_settings(tab_key)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_entries_tab_key "
        "ON record_entries(tab_key)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_record_entries_employee_id "
        "ON record_entries(employee_id)"
    )
    cur.execute(
        """
        INSERT OR IGNORE INTO record_tab_settings
            (id, tab_key, label, category_id, sort_order)
        VALUES
            ('record_tab_manual', 'manual', '메뉴얼', '', 1),
            ('record_tab_carm', 'carm', 'C-Arm', '', 2)
        """
    )
    conn.commit()
