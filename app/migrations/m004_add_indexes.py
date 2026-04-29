"""004 — v1.1.0: 대량 데이터 대응 인덱스.

patients 검색 속도 + 환자 이력 조회 속도 최적화.
IF NOT EXISTS 라 중복 실행 안전.
"""

MIGRATION_ID = 4
DESCRIPTION = "성능 인덱스 (patients 검색 + appointments 조회)"


def up(conn):
    cur = conn.cursor()
    for stmt in (
        "CREATE INDEX IF NOT EXISTS ix_patients_name ON patients(name)",
        "CREATE INDEX IF NOT EXISTS ix_patients_phone ON patients(phone)",
        "CREATE INDEX IF NOT EXISTS ix_patients_birth_date ON patients(birth_date)",
        "CREATE INDEX IF NOT EXISTS ix_appointments_patient_id ON appointments(patient_id)",
        "CREATE INDEX IF NOT EXISTS ix_appointments_therapist_id ON appointments(therapist_id)",
    ):
        cur.execute(stmt)
    conn.commit()
