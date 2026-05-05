"""020 — Phase 1: 치료항목 alias 테이블 (treatment_aliases).

용도:
  AI 가 사용자 자연어 명령 ("도수30 주 충") 을 DB 등록 치료항목으로 매칭하기
  위한 별칭 테이블. "도수30" → "도수치료 30분", "충" → "체외충격파" 등.

설계:
  - treatment_id: 매칭되는 실제 치료항목 ID
  - alias_name: 별칭 (예: "도30", "도수30", "체외", "충격파", "ESWT")
  - alias 충돌 시 (한 alias 가 여러 treatment_id 를 가리킴) AI 는
    treatment_alias_conflict 상태로 두고 사용자 선택 요구 (자동 매칭 금지).

IF NOT EXISTS 로 멱등성 보장.
"""

MIGRATION_ID = 20
DESCRIPTION = "Phase 1: 치료항목 alias 테이블 (treatment_aliases) 신설"


def up(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treatment_aliases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            treatment_id    TEXT NOT NULL,
            alias_name      TEXT NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(treatment_id, alias_name)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_treatment_aliases_alias
            ON treatment_aliases(alias_name)
    """)
    conn.commit()
