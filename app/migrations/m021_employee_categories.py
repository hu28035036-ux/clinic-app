"""021 - employee categories and capability overrides."""

MIGRATION_ID = 21
DESCRIPTION = "employee_categories table and employee capability overrides"


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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL DEFAULT '#9CA3AF',
            active BOOLEAN DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            default_can_doctor_treatment BOOLEAN DEFAULT 0,
            default_can_manual BOOLEAN DEFAULT 1,
            default_can_eswt BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    emp_cols = _cols(cur, "employees")
    if emp_cols:
        if "category_id" not in emp_cols:
            cur.execute("ALTER TABLE employees ADD COLUMN category_id TEXT")
        if "can_doctor_treatment_override" not in emp_cols:
            cur.execute("ALTER TABLE employees ADD COLUMN can_doctor_treatment_override BOOLEAN")
        if "can_manual_override" not in emp_cols:
            cur.execute("ALTER TABLE employees ADD COLUMN can_manual_override BOOLEAN")
        if "can_eswt_override" not in emp_cols:
            cur.execute("ALTER TABLE employees ADD COLUMN can_eswt_override BOOLEAN")

    # Do not seed default categories. Legacy employees keep category_id empty
    # until the user creates departments and assigns them explicitly.
    cur.execute(
        """
        UPDATE employees
           SET can_doctor_treatment_override=1
         WHERE role='doctor'
           AND can_doctor_treatment_override IS NULL
        """
    )
    cur.execute(
        """
        UPDATE employees
           SET can_manual_override=COALESCE(can_manual, 1)
         WHERE (role IS NULL OR role!='doctor')
           AND can_manual_override IS NULL
        """
    )
    cur.execute(
        """
        UPDATE employees
           SET can_eswt_override=COALESCE(can_eswt, 1)
         WHERE (role IS NULL OR role!='doctor')
           AND can_eswt_override IS NULL
        """
    )

    conn.commit()
