"""007 — v1.3.0: AI 기능 기본 테이블 추가 (ai_settings, ai_usage_logs).

용도:
  AI/RAG 기능을 위한 관리자 설정 + 호출 감사 로그.
  Provider 선택형 (openai/anthropic/local) — 기본 비활성(enabled=0).

원칙:
  - Base.metadata.create_all 이 모델 정의로 테이블을 만들지만,
    이 마이그레이션은 (a) 단일 설정 row(id=1) 시드 (b) 인덱스 보강을 담당.
  - IF NOT EXISTS / 컬럼 체크로 멱등성 보장.
  - DROP / DELETE 절대 없음 — 데이터 영구 보존 원칙.
"""

MIGRATION_ID = 7
DESCRIPTION = "AI 기능 테이블 시드 (ai_settings 단일 row, ai_usage_logs 인덱스)"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def up(conn):
    cur = conn.cursor()

    # ai_settings — 모델로 만들어진 후 단일 row 시드
    if _table_exists(cur, "ai_settings"):
        existing = cur.execute("SELECT COUNT(*) FROM ai_settings").fetchone()[0]
        if existing == 0:
            cur.execute(
                "INSERT INTO ai_settings "
                "(id, enabled, provider, model, api_key, base_url, "
                " max_tokens, temperature, pii_guard_enabled) "
                "VALUES (1, 0, 'openai', '', '', '', 512, 0.3, 1)"
            )

    # ai_usage_logs — ts 인덱스는 모델에서 index=True 로 잡지만,
    # 기존 환경에서 모델 정의 외 추가 인덱스가 필요하면 여기서 보강.
    if _table_exists(cur, "ai_usage_logs"):
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_feature "
            "ON ai_usage_logs(feature)"
        )

    conn.commit()
