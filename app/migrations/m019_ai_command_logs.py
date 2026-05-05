"""019 — Phase 1: AI 명령 로그 테이블 (ai_command_logs).

용도:
  병원 예약관리 AI 명령 (예약 도우미 / 휴무 도우미 등) 의 처리 과정을
  완전 기록. 원본 명령 / AI 파싱 / DB 매칭 / 검증 / 사용자 선택 / 승인 /
  실행 결과 / 오류 메시지를 모두 보관.

설계:
  - 17 필드 (AI_COMMAND_ARCHITECTURE.md § 5.1 정합)
  - JSON 필드는 TEXT 로 저장 (parsed_json / resolved_json 등)
  - 신환 등록과 예약 등록은 **각각 별도 row** 로 기록
  - 인덱스: user_id (관리자 로그 조회), created_at (시간 순)

IF NOT EXISTS 로 멱등성 보장.
"""

MIGRATION_ID = 19
DESCRIPTION = "Phase 1: AI 명령 로그 테이블 (ai_command_logs) 신설"


def up(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_command_logs (
            id                              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id                         TEXT,
            raw_text                        TEXT NOT NULL,
            intent                          TEXT,
            status                          TEXT NOT NULL DEFAULT 'received',
            parsed_json                     TEXT,
            resolved_json                   TEXT,
            validation_result               TEXT,
            preview_json                    TEXT,
            selected_patient_id             INTEGER,
            selected_treatment_items_json   TEXT,
            approved_by                     TEXT,
            executed_result                 TEXT,
            error_message                   TEXT,
            created_at                      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at                      DATETIME DEFAULT CURRENT_TIMESTAMP,
            executed_at                     DATETIME
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_ai_command_logs_user
            ON ai_command_logs(user_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_ai_command_logs_created
            ON ai_command_logs(created_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_ai_command_logs_status
            ON ai_command_logs(status)
    """)
    conn.commit()
