"""030 - daily medical summaries."""

MIGRATION_ID = 30
DESCRIPTION = "imported date-based medical summaries for daily reports"


def up(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_medical_summaries (
            id TEXT PRIMARY KEY,
            summary_date TEXT NOT NULL UNIQUE,
            total_medical_fee INTEGER NOT NULL DEFAULT 0,
            nhis_burden_total INTEGER NOT NULL DEFAULT 0,
            patient_burden_total INTEGER NOT NULL DEFAULT 0,
            covered_total INTEGER NOT NULL DEFAULT 0,
            uncovered_total INTEGER NOT NULL DEFAULT 0,
            source_filename TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_medical_summaries_summary_date "
        "ON daily_medical_summaries(summary_date)"
    )
    conn.commit()
