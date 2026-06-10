"""027 - daily work reports."""

MIGRATION_ID = 27
DESCRIPTION = "daily work reports for revenue tab"


def up(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_work_reports (
            id TEXT PRIMARY KEY,
            report_date TEXT NOT NULL UNIQUE,
            selected_treatment_codes_json TEXT NOT NULL DEFAULT '[]',
            custom_fields_json TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_work_reports_report_date "
        "ON daily_work_reports(report_date)"
    )
    conn.commit()
