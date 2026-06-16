"""037 — 장기 데이터(5년+) 대응 성능 인덱스 + 통계 갱신.

배경:
  운영이 길어질수록 appointments / audit_logs / settlement_records 등이
  수십만 행으로 커진다. 단일 컬럼 인덱스만으로는 다음 핫패스가 전체 테이블
  스캔 + 정렬로 떨어져 느려진다.

  1) GET /api/patients/last-appointments
       SELECT patient_id, MAX(start_at) ... WHERE status != 'canceled'
       GROUP BY patient_id
     → 환자관리 탭을 열 때마다 전체 예약을 훑음.
  2) GET /api/patients/{pid}/history
       WHERE patient_id = ? AND status='approved' ORDER BY start_at DESC
     → 장기 환자(수백 방문)에서 patient_id 인덱스만으로는 정렬 비용 발생.
  3) privacy.mask_inactive_patients
       환자별 마지막 예약 = WHERE patient_id=? ORDER BY start_at DESC LIMIT 1

  (patient_id, start_at) 복합 인덱스 하나로 위 3개 모두 인덱스 only/range 로
  처리되어 데이터가 커져도 응답시간이 거의 일정해진다.

원칙 (다른 마이그레이션과 동일):
  - DROP/DELETE/TRUNCATE 없음 — 데이터 절대 안 건드림.
  - CREATE INDEX IF NOT EXISTS — 두 번 실행해도 안전.
  - ANALYZE 는 통계 테이블(sqlite_stat1)만 갱신 — 데이터 무변경.
"""

MIGRATION_ID = 37
DESCRIPTION = "장기 데이터 대응 복합 인덱스 (appointments patient_id+start_at) + ANALYZE"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def up(conn):
    cur = conn.cursor()

    if _table_exists(cur, "appointments"):
        # 환자별 마지막 예약 / 환자 치료이력 정렬 가속.
        # MAX(start_at) GROUP BY patient_id 와 patient_id 필터 + start_at 정렬
        # 둘 다 이 인덱스 하나로 커버된다.
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_appointments_patient_start "
            "ON appointments (patient_id, start_at)"
        )

    # 쿼리 플래너 통계 갱신 — 신규 인덱스를 즉시 활용하도록.
    # (이후로는 일일 유지보수의 PRAGMA optimize 가 지속 갱신)
    try:
        cur.execute("ANALYZE")
    except Exception:
        # ANALYZE 실패는 치명적이지 않음 — 인덱스 자체는 이미 생성됨.
        pass

    conn.commit()
