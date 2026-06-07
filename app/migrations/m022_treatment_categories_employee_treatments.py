"""022 - treatment categories and employee treatment assignments."""

MIGRATION_ID = 22
DESCRIPTION = "treatment category_id and employee_treatments table"


def _cols(cur, table: str) -> set[str]:
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _category_id(cur, name: str) -> str:
    row = cur.execute(
        "SELECT id FROM employee_categories WHERE name=?",
        (name,),
    ).fetchone()
    return row[0] if row else ""


def up(conn):
    cur = conn.cursor()

    tx_cols = _cols(cur, "treatments")
    if tx_cols and "category_id" not in tx_cols:
        cur.execute("ALTER TABLE treatments ADD COLUMN category_id TEXT")

    emp_cols = _cols(cur, "employees")
    if emp_cols and "treatment_override_enabled" not in emp_cols:
        cur.execute(
            "ALTER TABLE employees ADD COLUMN treatment_override_enabled BOOLEAN DEFAULT 0"
        )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_treatments (
            id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            treatment_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, treatment_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_treatments_employee_id "
        "ON employee_treatments(employee_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_treatments_treatment_id "
        "ON employee_treatments(treatment_id)"
    )

    doctor_cat = _category_id(cur, "진료과")
    therapy_cat = _category_id(cur, "치료과")

    if doctor_cat:
        cur.execute(
            """
            UPDATE treatments
               SET category_id=?
             WHERE (category_id IS NULL OR category_id='')
               AND role='doctor'
            """,
            (doctor_cat,),
        )
    if therapy_cat:
        cur.execute(
            """
            UPDATE treatments
               SET category_id=?
             WHERE (category_id IS NULL OR category_id='')
               AND (role IS NULL OR role!='doctor')
            """,
            (therapy_cat,),
        )

    conn.commit()
