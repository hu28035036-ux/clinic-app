"""002 — v1.2.0: patients.gender 컬럼 추가."""

MIGRATION_ID = 2
DESCRIPTION = "patients.gender 컬럼 추가 (M/F)"


def up(conn):
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(patients)").fetchall()]
    if "gender" not in cols:
        cur.execute("ALTER TABLE patients ADD COLUMN gender VARCHAR(2) DEFAULT ''")
    conn.commit()
