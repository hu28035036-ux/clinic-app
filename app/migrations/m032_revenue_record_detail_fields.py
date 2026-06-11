"""032 - detailed revenue record fields."""

MIGRATION_ID = 32
DESCRIPTION = "detailed revenue record fields and calculated totals"


def _columns(cur, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def up(conn):
    cur = conn.cursor()
    cols = _columns(cur, "revenue_records")
    fields = {
        "total_medical_fee": "INTEGER NOT NULL DEFAULT 0",
        "nhis_burden_total": "INTEGER NOT NULL DEFAULT 0",
        "receivable_income": "INTEGER NOT NULL DEFAULT 0",
        "certificate_amount": "INTEGER NOT NULL DEFAULT 0",
        "uninsured_amount": "INTEGER NOT NULL DEFAULT 0",
        "meal_amount": "INTEGER NOT NULL DEFAULT 0",
        "discount_amount": "INTEGER NOT NULL DEFAULT 0",
        "free_amount": "INTEGER NOT NULL DEFAULT 0",
        "cash_expense_amount": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, ddl in fields.items():
        if name not in cols:
            cur.execute(f"ALTER TABLE revenue_records ADD COLUMN {name} {ddl}")
    conn.commit()
