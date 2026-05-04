"""014 — v1.3.4: Appointment.no_show 별도 boolean 필드 추가 (post-19-P / 20-3-1).

용도:
  F-10 노쇼 별도 필드 도입 — `Appointment` 테이블에 `no_show BOOLEAN DEFAULT 0`
  컬럼 추가. 사용자 §3-7 결정값 (a) boolean / (i) cancel 동시 / (ii) 통계 별도.

원칙 (docs/ai_rag_migration_plan.md §0/§3 정합):
  - DROP/DELETE/TRUNCATE 절대 없음 — 데이터 영구 보존.
  - 컬럼 추가 + DEFAULT 0 — 기존 row 모두 `no_show=False` 자동 세팅.
  - 두 번 실행해도 안전 (idempotent — sqlite_master pragma_table_info 검사).
  - 테이블 부재 시 (단독 실행 등) skip — 안전.

호환성:
  - 기존 `status` ENUM (`reserved` / `approved` / `canceled`) 보존.
  - `no_show=True` 와 `status="canceled"` 동시 가능 (cancel 동시 정책).
  - 통계는 `no_show_count` 별도 항목 (cancel 과 분리).
  - 응답 dict / API URL 변경 ⊥ — 신설 키 `no_show` 추가만 (기존 33+ 셋 보존).
"""

MIGRATION_ID = 14
DESCRIPTION = "Appointment.no_show BOOLEAN DEFAULT 0 (post-19-P / F-10 노쇼)"


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

    # ── Appointment.no_show 컬럼 추가 (idempotent) ──
    if _table_exists(cur, "appointments"):
        if not _column_exists(cur, "appointments", "no_show"):
            cur.execute(
                "ALTER TABLE appointments ADD COLUMN no_show INTEGER DEFAULT 0 NOT NULL"
            )

    conn.commit()
