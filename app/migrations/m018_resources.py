"""018 — v1.3.4: Resource 테이블 + Appointment.resource_id (post-19-P / 20-3-5 / F-3).

용도:
  F-3 자원 도입 — 사용자 §7-7 결정값:
  - (a) 치료실만 (type 컬럼은 'room' / 'equipment' 분기 보존, v1 = 'room' 만)
  - (i) F-1 Room 과 별개 (F-1 (c) 가벼운 의사 결정 정합)
  - (i) capacity=1 동시 ⊥ (1:1 도수치료 표준)
  - (i) 인력 자원 미도입 (Employee 분기 충분)

원칙 (docs/ai_rag_migration_plan.md §0/§3 정합):
  - DROP/DELETE/TRUNCATE 절대 없음.
  - CREATE TABLE 멱등 가드 (Base.metadata.create_all 분담).
  - ALTER TABLE 멱등 가드 (Appointment.resource_id).
  - 두 번 실행해도 안전.

호환성:
  - 기존 Appointment 컬럼 보존 — resource_id 만 추가 (FK nullable).
  - 단일 예약은 resource_id=None 으로 기존 동작 그대로.
  - 응답 dict 신설 키 resource_id 만 추가 (기존 18 extendedProps 보존, 19키로 확장).
"""

MIGRATION_ID = 18
DESCRIPTION = "Resource 테이블 + Appointment.resource_id FK + 충돌 인덱스 (post-19-P / F-3 자원)"


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

    # ── Appointment.resource_id 컬럼 추가 (idempotent ALTER TABLE) ──
    if _table_exists(cur, "appointments"):
        if not _column_exists(cur, "appointments", "resource_id"):
            cur.execute(
                "ALTER TABLE appointments ADD COLUMN resource_id VARCHAR(32) DEFAULT NULL"
            )
        # 자원 + 시간 충돌 검사 가속 — 같은 resource_id + start_at 범위 query
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_appointments_resource_time "
            "ON appointments (resource_id, start_at)"
        )

    # ── resources 테이블 인덱스 보강 (Base.metadata.create_all 이후) ──
    if _table_exists(cur, "resources"):
        # 활성 + 정렬 가속
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_resources_type_active "
            "ON resources (type, active, sort_order)"
        )

    conn.commit()
