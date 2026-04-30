"""008 — v1.3.1 (세션 09): AiUsageLog 확장 컬럼 추가.

용도:
  AI/RAG 호출의 운영 추적을 풍부화 — 차단/경고/할루시네이션 가드 사유,
  마스킹 후 prompt/response sha256 해시, PII/할루시네이션 가드 적중수 등.

원칙:
  - ALTER TABLE ADD COLUMN 만 사용 (멱등 가드: PRAGMA table_info 로 컬럼 존재 확인).
  - 기존 status / error_kind 컬럼은 그대로 보존 (이전 데이터 손실 금지).
  - DROP / DELETE / TRUNCATE 절대 없음.
  - 본문(prompt/response) 자체는 절대 저장하지 않음 — 해시(sha256)만 저장.
"""

MIGRATION_ID = 8
DESCRIPTION = "AiUsageLog 확장 컬럼 (outcome/error_detail/hash/guard hits 등)"


_NEW_COLUMNS = [
    # name           type           default
    ("outcome",                  "VARCHAR(20)",  "''"),
    ("error_detail",             "VARCHAR(500)", "''"),
    ("prompt_hash",              "VARCHAR(64)",  "''"),
    ("response_hash",            "VARCHAR(64)",  "''"),
    ("pii_filter_hits",          "INTEGER",      "0"),
    ("hallucination_guard_hits", "INTEGER",      "0"),
    ("response_used",            "INTEGER",      "0"),
    ("sms_sent",                 "INTEGER",      "0"),
]


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

    if not _table_exists(cur, "ai_usage_logs"):
        # Base.metadata.create_all 이 아직 테이블을 안 만든 환경 — 다음 부팅에서 만들어짐.
        return

    for col, ctype, default in _NEW_COLUMNS:
        if not _column_exists(cur, "ai_usage_logs", col):
            cur.execute(
                f"ALTER TABLE ai_usage_logs ADD COLUMN {col} {ctype} DEFAULT {default}"
            )

    # outcome 으로 자주 필터링하므로 인덱스 추가 (멱등)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_outcome "
        "ON ai_usage_logs(outcome)"
    )

    conn.commit()
