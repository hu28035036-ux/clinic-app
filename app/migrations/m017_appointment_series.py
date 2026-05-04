"""017 — v1.3.4: AppointmentSeries 테이블 + Appointment.series_id (post-19-P / 20-3-4 / F-2).

NOTE: 20-P-2 §3 마이그레이션 계획에서 m017~m020 = F-1 풀 EMR (Department/Room/
DoctorSchedule/Patient.doctor_id) 으로 예약했으나, 사용자 §5-7 (c) "가벼운 의사만"
결정으로 F-1 풀 EMR 패스. m017 은 F-2 반복 예약으로 사용 (연속 번호).

용도:
  F-2 반복 예약 도입 — 사용자 §6-6 결정값:
  - (a) 반복 패턴 = N회만 (interval_days + count)
  - (i) 시리즈 일괄 처리 = 미래만
  - (ii) 충돌 검사 = 등록 후 충돌만 안내 (충돌 슬롯 skip)

원칙 (docs/ai_rag_migration_plan.md §0/§3 정합):
  - DROP/DELETE/TRUNCATE 절대 없음.
  - CREATE TABLE / ALTER TABLE 멱등 가드.
  - 두 번 실행해도 안전.

호환성:
  - 기존 Appointment 컬럼 보존 — series_id 만 추가 (FK nullable).
  - 단일 예약 생성은 series_id=None 으로 기존 동작 그대로.
  - 응답 dict 신설 키 series_id 만 추가 (기존 17 extendedProps 보존, 18키로 확장).

분담:
  - 테이블 생성: ``Base.metadata.create_all`` (ORM 모델 기준)
  - 본 마이그레이션은 ALTER TABLE (Appointment.series_id) + 인덱스 보강.
"""

MIGRATION_ID = 17
DESCRIPTION = "AppointmentSeries 테이블 + Appointment.series_id FK (post-19-P / F-2 반복 예약)"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _column_exists(cur, table: str, column: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def up(conn):
    cur = conn.cursor()

    # ── Appointment.series_id 컬럼 추가 (idempotent ALTER TABLE) ──
    if _table_exists(cur, "appointments"):
        if not _column_exists(cur, "appointments", "series_id"):
            cur.execute(
                "ALTER TABLE appointments ADD COLUMN series_id VARCHAR(32) DEFAULT NULL"
            )
        # series_id 기준 일괄 조회 가속 (DELETE /api/appointment-series/{sid} 미래만)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_appointments_series_id "
            "ON appointments (series_id)"
        )

    # ── appointment_series 테이블 인덱스 보강 (Base.metadata.create_all 이후) ──
    if _table_exists(cur, "appointment_series"):
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_appointment_series_patient_created "
            "ON appointment_series (patient_id, created_at)"
        )

    conn.commit()
