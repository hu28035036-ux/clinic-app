"""016 — v1.3.4: Doctor 별도 테이블 신설 (post-19-P / 20-3-3 / F-1 가벼운 의사).

용도:
  F-1 (c) 가벼운 의사만 — `Doctor` 단일 테이블 신설. Department / Room /
  DoctorSchedule / Patient.doctor_id 부재 (사용자 §5-7 (c) 결정).

원칙 (docs/ai_rag_migration_plan.md §0/§3 정합):
  - DROP/DELETE/TRUNCATE 절대 없음.
  - CREATE TABLE IF NOT EXISTS 멱등 가드 + Base.metadata.create_all 분담 (m007/m012/m013 패턴).
  - 두 번 실행해도 안전.

호환성:
  - 기존 `Employee.role="doctor"` 분기 (도수치료 내부 의료직군) 보존.
  - `Doctor` 별도 테이블은 *외부 진료 의사 등록 후보 모델* — Employee 와 별개.
  - `Patient.doctor_id` FK 부재 (사용자 §5-7 (c) 결정 — 가벼운 의사만).
  - `Department` / `Room` / `DoctorSchedule` 부재 (post-(c) 후속 결정).

분담:
  - 테이블 생성: ``Base.metadata.create_all`` (ORM 모델 기준)
  - 본 마이그레이션은 SQLite ALTER 한계 보강 — index / UNIQUE 만 담당.
"""

MIGRATION_ID = 16
DESCRIPTION = "Doctor 별도 테이블 신설 (post-19-P / F-1 (c) 가벼운 의사 — Department/Room/Schedule 부재)"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def up(conn):
    cur = conn.cursor()

    # ── doctors 테이블 인덱스 보강 (Base.metadata.create_all 이후) ──
    if _table_exists(cur, "doctors"):
        # 정렬 / 활성 필터 가속 — list_doctors 응답 빈도 多
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_doctors_active_sort "
            "ON doctors (active, sort_order)"
        )
        # 면허번호 unique (nullable 허용 — SQLite 의 nullable UNIQUE 는 NULL 다수 허용)
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_doctors_license_no "
            "ON doctors (license_no) WHERE license_no IS NOT NULL"
        )

    conn.commit()
