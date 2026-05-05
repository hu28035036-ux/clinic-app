"""Phase 1 — AI 명령 스키마 / provider / audit 단위 테스트.

검증 항목:
- 23 상태값 / 9 추출 필드 / 5 데이터 출처 상태 enum 정의
- ParsedCommand.to_dict() 직렬화
- TreatmentItem 기본 상태
- MockProvider 동작
- ai_command_logs INSERT / UPDATE / SELECT (실제 마이그레이션 적용된 DB)
- 마이그레이션 m019 / m020 멱등 실행 확인

운영 DB 사용 금지 — conftest 가 임시 DB 로 격리.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.ai import (
    AiCommandStatus,
    AiIntent,
    AIProvider,
    DataSourceState,
    MockProvider,
    ParsedCommand,
    TreatmentItemStatus,
    get_default_provider,
)
from app.ai.ai_audit import get_log, update_log, write_log
from app.ai.ai_command_schema import ParserContext, TreatmentItem

# ────────────────────────────── 스키마 / Enum ──────────────────────────────


def test_ai_intent_values():
    """1차 ~ 5차 intent 10 종 모두 존재."""
    assert AiIntent.CREATE_APPOINTMENT.value == "create_appointment"
    assert AiIntent.UPDATE_APPOINTMENT.value == "update_appointment"
    assert AiIntent.CANCEL_APPOINTMENT.value == "cancel_appointment"
    assert AiIntent.CREATE_LEAVE.value == "create_leave"
    assert AiIntent.PREPARE_SMS.value == "prepare_sms"
    assert AiIntent.SUMMARIZE_TODAY.value == "summarize_today"
    assert AiIntent.SUMMARIZE_TOMORROW.value == "summarize_tomorrow"
    assert AiIntent.ANALYZE_STATS.value == "analyze_stats"
    assert AiIntent.DATA_QUALITY_CHECK.value == "data_quality_check"
    assert AiIntent.OPS_ASSISTANT.value == "ops_assistant"
    assert len(list(AiIntent)) == 10


def test_ai_command_status_count_23():
    """23 상태값 (기본 9 + 환자 4 + 신환 6 + 치료항목 4) 모두 존재."""
    assert len(list(AiCommandStatus)) == 23


def test_ai_command_status_categories():
    """4 카테고리별 핵심 상태값 확인."""
    # 기본 9
    assert AiCommandStatus.RECEIVED
    assert AiCommandStatus.NEEDS_APPROVAL
    # 환자 후보 4
    assert AiCommandStatus.PATIENT_SELECTION_REQUIRED
    assert AiCommandStatus.PATIENT_MISMATCH
    # 신환 6
    assert AiCommandStatus.PATIENT_NOT_FOUND
    assert AiCommandStatus.APPOINTMENT_NEEDS_REVALIDATION
    # 치료항목 4
    assert AiCommandStatus.TREATMENT_ALIAS_CONFLICT
    assert AiCommandStatus.TREATMENT_NOT_FOUND


def test_data_source_state_5():
    """할루시네이션 방지용 5 상태."""
    assert len(list(DataSourceState)) == 5
    assert DataSourceState.AI_EXTRACTED.value == "ai_extracted"
    assert DataSourceState.DB_VERIFIED.value == "db_verified"


def test_parsed_command_default():
    """ParsedCommand 기본값 — 모든 필드 None / 빈 list."""
    cmd = ParsedCommand(raw_text="박환자 4월30일 9시 도수30 예약")
    assert cmd.intent is None
    assert cmd.patient_name is None
    assert cmd.treatment_items == []
    assert cmd.raw_text == "박환자 4월30일 9시 도수30 예약"


def test_parsed_command_to_dict_roundtrip():
    """ParsedCommand.to_dict() 가 모든 9 필드 + raw_text 포함."""
    ti = TreatmentItem(
        raw_text="도수30",
        matched_treatment_id="manual_30",
        matched_treatment_name="도수치료 30분",
        source=DataSourceState.DB_VERIFIED,
        status=TreatmentItemStatus.DB_VERIFIED,
    )
    cmd = ParsedCommand(
        intent=AiIntent.CREATE_APPOINTMENT,
        patient_name="박환자",
        chart_number="12345",
        date_text="4월30일",
        time_text="9시",
        therapist_name="박치료사",
        treatment_text="도수30 주 충",
        treatment_items=[ti],
        memo=None,
        raw_text="박환자 4월30일 9시 도수30 주 충 예약",
    )
    d = cmd.to_dict()
    assert d["intent"] == "create_appointment"
    assert d["patient_name"] == "박환자"
    assert d["chart_number"] == "12345"
    assert d["treatment_items"][0]["matched_treatment_id"] == "manual_30"
    assert d["treatment_items"][0]["source"] == "db_verified"
    assert d["raw_text"].startswith("박환자")


# ────────────────────────────── Provider ──────────────────────────────


def test_mock_provider_implements_protocol():
    """MockProvider 가 AIProvider Protocol 만족."""
    mp = MockProvider()
    assert isinstance(mp, AIProvider)
    assert mp.name == "mock"


def test_mock_provider_returns_parsed_command():
    """MockProvider.parse_command() 가 ParsedCommand 반환 (raw_text 포함)."""
    mp = MockProvider()
    ctx = ParserContext(
        raw_text="박환자 4월30일 9시 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
    )
    result = mp.parse_command(ctx.raw_text, ctx)
    assert isinstance(result, ParsedCommand)
    assert result.raw_text == "박환자 4월30일 9시 도수30 예약"
    # Phase 1 의 MockProvider 는 추출 안 함 (parser 는 Phase 2)
    assert result.intent is None


def test_get_default_provider_returns_mock_in_phase1():
    """Phase 1 에서는 항상 MockProvider 반환."""
    p = get_default_provider()
    assert p.name == "mock"


# ────────────────────────────── Audit (DB) ──────────────────────────────


@pytest.fixture
def conn():
    """임시 in-memory SQLite + 마이그레이션 m019 / m020 수동 적용."""
    c = sqlite3.connect(":memory:")
    from app.migrations.m019_ai_command_logs import up as up19
    from app.migrations.m020_treatment_aliases import up as up20

    up19(c)
    up20(c)
    yield c
    c.close()


def test_migration_m019_creates_table(conn):
    """ai_command_logs 테이블 + 17 필드 확인."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(ai_command_logs)")
    cols = {row[1] for row in cur.fetchall()}
    expected = {
        "id",
        "user_id",
        "raw_text",
        "intent",
        "status",
        "parsed_json",
        "resolved_json",
        "validation_result",
        "preview_json",
        "selected_patient_id",
        "selected_treatment_items_json",
        "approved_by",
        "executed_result",
        "error_message",
        "created_at",
        "updated_at",
        "executed_at",
    }
    assert expected.issubset(cols), f"누락: {expected - cols}"


def test_migration_m020_creates_aliases_table(conn):
    """treatment_aliases 테이블 + UNIQUE 제약."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(treatment_aliases)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"id", "treatment_id", "alias_name", "created_at", "updated_at"}.issubset(cols)
    cur.execute("INSERT INTO treatment_aliases (treatment_id, alias_name) VALUES ('manual_30', '도수30')")
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO treatment_aliases (treatment_id, alias_name) VALUES ('manual_30', '도수30')"
        )


def test_migration_idempotent(conn):
    """m019 / m020 두 번 실행해도 안전 (IF NOT EXISTS)."""
    from app.migrations.m019_ai_command_logs import up as up19
    from app.migrations.m020_treatment_aliases import up as up20

    up19(conn)
    up20(conn)  # 두 번째 실행도 OK


def test_audit_write_log_returns_id(conn):
    """write_log() 가 새 row INSERT 후 lastrowid 반환."""
    cmd_id = write_log(
        conn,
        user_id="user1",
        raw_text="박환자 4월30일 9시 도수30 예약",
        intent="create_appointment",
        status="received",
    )
    assert cmd_id > 0


def test_audit_write_log_with_json_fields(conn):
    """JSON 필드 (parsed_json / resolved_json 등) 가 dict / list 로 저장."""
    cmd_id = write_log(
        conn,
        user_id="user1",
        raw_text="test",
        parsed_json={"intent": "create_appointment", "patient_name": "박환자"},
        selected_treatment_items_json=[{"raw_text": "도수30", "status": "db_verified"}],
    )
    log = get_log(conn, cmd_id)
    assert log is not None
    assert log["parsed_json"] == {"intent": "create_appointment", "patient_name": "박환자"}
    assert log["selected_treatment_items_json"][0]["raw_text"] == "도수30"


def test_audit_update_log_partial_fields(conn):
    """update_log() 가 전달된 필드만 갱신."""
    cmd_id = write_log(conn, user_id="user1", raw_text="test", status="received")
    update_log(conn, cmd_id, status="needs_approval", validation_result={"ok": True})
    log = get_log(conn, cmd_id)
    assert log["status"] == "needs_approval"
    assert log["validation_result"] == {"ok": True}


def test_audit_update_log_executed_at_now(conn):
    """executed_at_now=True 시 executed_at 컬럼 채워짐."""
    cmd_id = write_log(conn, user_id="user1", raw_text="test")
    update_log(conn, cmd_id, status="executed", executed_at_now=True)
    log = get_log(conn, cmd_id)
    assert log["executed_at"] is not None
    assert log["status"] == "executed"


def test_audit_separate_logs_for_new_patient_and_appointment(conn):
    """신환 등록과 예약 등록은 별도 row 로 기록 (AI_FEATURE_MASTER_PLAN § 10.2)."""
    new_patient_id = write_log(
        conn,
        user_id="user1",
        raw_text="박환자 신환 등록",
        intent="create_appointment",  # 신환 흐름은 create_appointment 의 일부
        status="patient_registered",
    )
    appointment_id = write_log(
        conn,
        user_id="user1",
        raw_text="박환자 4월30일 9시 도수30 예약",
        intent="create_appointment",
        status="executed",
    )
    assert new_patient_id != appointment_id
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ai_command_logs")
    assert cur.fetchone()[0] == 2


def test_get_log_returns_none_for_nonexistent(conn):
    """없는 command_id 조회 시 None."""
    assert get_log(conn, 99999) is None


# ────────────────────────────── 보안 / 안전 ──────────────────────────────


def test_db_path_is_isolated():
    """conftest 가 임시 DB 경로 격리 — 운영 DB 사용 금지 (CLAUDE.md 안전 규칙)."""
    from app.database import DB_URL

    # 운영 DB 경로에 절대 사용되지 않아야 함
    assert "%APPDATA%" not in DB_URL
    db_str = str(DB_URL).lower()
    assert "tests/temp" in db_str or "tests\\temp" in db_str or ":memory:" in db_str


def test_app_ai_does_not_import_app_services_ai():
    """app.ai 패키지가 기존 app.services.ai 를 import 하지 않아야 함 (모듈 분리 원칙).

    docstring 등에 'app.services.ai' 가 텍스트로 언급되는 것은 OK (분리 명시 목적).
    실제 import 문 (from / import) 만 검사.
    """
    import re

    import app.ai

    # 정규식: "from app.services.ai" 또는 "import app.services.ai"
    pattern = re.compile(r"^\s*(from|import)\s+app\.services\.ai", re.MULTILINE)
    src_path = Path(app.ai.__file__).parent
    for py_file in src_path.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        match = pattern.search(content)
        assert match is None, (
            f"{py_file.name} 가 app.services.ai 를 import 함 (분리 원칙 위반): {match.group(0)!r}"
        )
