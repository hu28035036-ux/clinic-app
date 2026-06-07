"""025 - daily revenue records."""

MIGRATION_ID = 25
DESCRIPTION = "daily revenue records for revenue statistics"


def up(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS revenue_records (
            id TEXT PRIMARY KEY,
            record_date TEXT NOT NULL,
            category_id TEXT NOT NULL DEFAULT '',
            cash_amount INTEGER NOT NULL DEFAULT 0,
            card_amount INTEGER NOT NULL DEFAULT 0,
            transfer_amount INTEGER NOT NULL DEFAULT 0,
            other_amount INTEGER NOT NULL DEFAULT 0,
            memo TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_date, category_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_revenue_records_record_date "
        "ON revenue_records(record_date)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_revenue_records_category_id "
        "ON revenue_records(category_id)"
    )
    conn.commit()
