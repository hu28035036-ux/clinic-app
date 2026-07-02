"""040 — 환자 차팅(진료기록) 테이블 (patient_charts) 신설.

용도:
  치료완료(approved) 예약 1건당 SOAP 진료기록 1장. UNIQUE(appointment_id) 로 1:1 보장.
  진료내용을 구조적으로 남기는 첫 도메인 (기존 Patient.memo / Appointment.memo 와 별개).

원칙 (m039 패턴 정합):
  - DROP/DELETE/TRUNCATE 절대 없음.
  - CREATE TABLE IF NOT EXISTS 멱등 가드 + Base.metadata.create_all 분담.
  - 두 번 실행해도 안전.

분담:
  - 테이블 생성: ``Base.metadata.create_all`` (ORM 모델 PatientChart 기준).
  - 본 마이그레이션은 신규 테이블 멱등 보강 — 테이블/인덱스/UNIQUE 보장.
"""

MIGRATION_ID = 40
DESCRIPTION = "환자 차팅 테이블 (patient_charts) 신설 + UNIQUE(appointment_id)"


def up(conn):
    cur = conn.cursor()

    # ── 테이블 본체 (create_all 분담이나, 마이그레이션 단독으로도 안전하게) ──
    cur.execute(
        "CREATE TABLE IF NOT EXISTS patient_charts ("
        " id VARCHAR(32) PRIMARY KEY,"
        " appointment_id VARCHAR(32) NOT NULL,"
        " patient_id VARCHAR(32) NOT NULL,"
        " content TEXT DEFAULT '',"
        " author_id VARCHAR(32),"
        " author_name_snapshot VARCHAR(50) DEFAULT '',"
        " created_at DATETIME,"
        " updated_at DATETIME"
        ")"
    )

    # ── 인덱스 / UNIQUE 멱등 보강 ──
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_patient_chart_appt "
        "ON patient_charts (appointment_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_patient_charts_patient_id "
        "ON patient_charts (patient_id)"
    )

    conn.commit()
