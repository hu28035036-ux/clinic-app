"""013 — v1.3.4: knowledge_vectors 인덱스 보강.

용도:
  18-5 vector store / embedding 의 영속화 테이블 ``knowledge_vectors`` 의
  인덱스/UNIQUE 제약 멱등 생성. 테이블 본체는 ``Base.metadata.create_all`` 이
  ORM 모델 (``app/models/models.py:KnowledgeVector``) 로 자동 생성하며, 본
  마이그레이션은 SQLite 가 ALTER TABLE 로 인덱스 추가가 어려운 한계를
  보완하기 위한 idempotent 인덱스 보강을 담당한다 — m007/m008/m012 와 동일
  패턴.

원칙 (docs/ai_rag_migration_plan.md §0/§3):
  - DROP/DELETE/TRUNCATE 절대 없음 — 데이터 영구 보존.
  - IF NOT EXISTS 멱등 가드.
  - 두 번 실행해도 안전 (idempotent).
  - 테이블 부재 시 (단독 실행 등) 인덱스 생성 skip — 안전.

분담:
  - 테이블 생성: ``Base.metadata.create_all`` (m007/m012 와 동일 패턴)
  - 인덱스 보강: 본 마이그레이션
      * UNIQUE (chunk_id, provider, model)  — ORM __table_args__ 와 동일 이름
      * content_hash 인덱스 (same_hash skip 판정)
      * chunk_id 인덱스 (FK 검색 가속)
"""

MIGRATION_ID = 13
DESCRIPTION = "knowledge_vectors 인덱스 보강 (chunk_id+provider+model UNIQUE / content_hash idx / chunk_id idx)"


def _table_exists(cur, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def up(conn):
    cur = conn.cursor()

    # ── knowledge_vectors 인덱스 보강 ──
    if _table_exists(cur, "knowledge_vectors"):
        # UNIQUE (chunk_id, provider, model) — ORM __table_args__ 와 동일 이름.
        # 같은 청크에 같은 provider+model 조합은 단 1 row.
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_vectors_chunk_provider_model "
            "ON knowledge_vectors (chunk_id, provider, model)"
        )
        # content_hash 인덱스 — same_hash skip 판정에 사용.
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_vectors_content_hash "
            "ON knowledge_vectors (content_hash)"
        )
        # chunk_id 인덱스 — FK 결합 검색 가속 (ORM index=True 로도 잡히지만 보강).
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_vectors_chunk_id "
            "ON knowledge_vectors (chunk_id)"
        )

    conn.commit()
