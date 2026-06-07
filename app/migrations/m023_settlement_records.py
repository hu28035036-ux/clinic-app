"""023 - settlement records."""

MIGRATION_ID = 23
DESCRIPTION = "settlement records with snapshots"


def up(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settlement_records (
            id TEXT PRIMARY KEY,
            performed_on TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            treatment_id TEXT NOT NULL,
            treatment_code TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            memo TEXT NOT NULL DEFAULT '',
            employee_name_snapshot TEXT NOT NULL DEFAULT '',
            employee_category_id_snapshot TEXT,
            employee_category_name_snapshot TEXT NOT NULL DEFAULT '',
            treatment_name_snapshot TEXT NOT NULL DEFAULT '',
            treatment_short_snapshot TEXT NOT NULL DEFAULT '',
            treatment_code_snapshot TEXT NOT NULL DEFAULT '',
            price_snapshot INTEGER NOT NULL DEFAULT 0,
            incentive_type_snapshot TEXT NOT NULL DEFAULT 'none',
            incentive_value_snapshot REAL NOT NULL DEFAULT 0,
            incentive_amount INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(performed_on, employee_id, treatment_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_settlement_records_performed_on "
        "ON settlement_records(performed_on)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_settlement_records_employee_id "
        "ON settlement_records(employee_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_settlement_records_treatment_id "
        "ON settlement_records(treatment_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_settlement_records_treatment_code "
        "ON settlement_records(treatment_code)"
    )
    conn.commit()
