"""012 — v1.3.4: knowledge_chunks / knowledge_index_runs 인덱스 보강.

용도:
  18-3 chunker 산출물을 SQLite 에 영속화하기 위한 두 테이블의 인덱스/UNIQUE
  제약 멱등 생성. 테이블 본체는 ``Base.metadata.create_all`` 이 ORM 모델
  (``app/models/models.py:KnowledgeChunk|KnowledgeIndexRun``) 로 자동 생성하며,
  본 마이그레이션은 SQLite 가 ALTER TABLE 로 인덱스 추가가 어려운 한계를
  보완하기 위한 idempotent 인덱스 보강을 담당한다.

원칙 (docs/ai_rag_migration_plan.md §0):
  - DROP/DELETE/TRUNCATE 절대 없음 — 데이터 영구 보존.
  - IF NOT EXISTS / PRAGMA index_list 멱등 가드.
  - 두 번 실행해도 안전 (idempotent).
  - reindex 실패 시 기존 chunk 보존 정책은 indexer 책임 (본 마이그레이션 무관).

분담:
  - 테이블 생성: ``Base.metadata.create_all`` (m007 ai_settings 와 동일 패턴)
  - 인덱스 보강: 본 마이그레이션 (UNIQUE (doc_id, chunk_index), content_hash, category, started_at)
"""

MIGRATION_ID = 12
DESCRIPTION = "knowledge_chunks/knowledge_index_runs 인덱스 보강"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def up(conn):
    cur = conn.cursor()

    # ── knowledge_chunks 인덱스 보강 ──
    if _table_exists(cur, "knowledge_chunks"):
        # UNIQUE (doc_id, chunk_index) — ORM __table_args__ 와 동일 이름
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_chunks_doc_chunk "
            "ON knowledge_chunks (doc_id, chunk_index)"
        )
        # content_hash 검색 가속 (skip 판정에 사용)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_hash "
            "ON knowledge_chunks (content_hash)"
        )
        # category 필터 (manuals/sms_guides) 가속
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_category "
            "ON knowledge_chunks (category)"
        )

    # ── knowledge_index_runs 인덱스 보강 ──
    if _table_exists(cur, "knowledge_index_runs"):
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_index_runs_started "
            "ON knowledge_index_runs (started_at)"
        )

    conn.commit()
