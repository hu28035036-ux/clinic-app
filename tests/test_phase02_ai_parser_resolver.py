"""Phase 2 — ai_parser / ai_resolver 단위 테스트.

검증 항목:
- Parser: 9 추출 필드 (intent / patient_name / chart_number / date_text / time_text /
  therapist_name / treatment_text / treatment_items / memo)
- Resolver: 환자 검색 우선순위 5단계 / 치료사 매칭 / 치료항목 alias / 날짜 / 시간
- 환자 후보 다수 시 차트번호/이름/생년월일/연락처 후보 목록
- 치료항목 alias 충돌 시 ALIAS_CONFLICT 상태
- 날짜 해석: 오늘/내일/이번주/다음주/M월D일/D일/과거날짜
- "도수30 주 충" 다중 약어 입력
- DB 직접 수정 0건 (resolver 는 read-only)
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.ai_command_schema import (
    AiIntent,
    DataSourceState,
    ParserContext,
    TreatmentItemStatus,
)
from app.ai.ai_parser import parse_command
from app.ai.ai_resolver import (
    resolve_date,
    resolve_patient,
    resolve_therapist,
    resolve_time,
    resolve_treatment_items,
)
from app.models.models import Base, Employee, Patient, Treatment

# ────────────────────────────── Parser 테스트 ──────────────────────────────


def _ctx(text: str = "", year: int = 2026, month: int = 5) -> ParserContext:
    return ParserContext(raw_text=text, current_calendar_year=year, current_calendar_month=month)


def test_parser_intent_create_appointment():
    cmd = parse_command("박환자 4월30일 9시 도수30 예약해줘", context=_ctx())
    assert cmd.intent == AiIntent.CREATE_APPOINTMENT


def test_parser_intent_update():
    cmd = parse_command("박환자 내일 9시 예약을 10시로 변경해줘", context=_ctx())
    assert cmd.intent == AiIntent.UPDATE_APPOINTMENT


def test_parser_intent_cancel():
    cmd = parse_command("박환자 내일 9시 예약 취소", context=_ctx())
    assert cmd.intent == AiIntent.CANCEL_APPOINTMENT


def test_parser_intent_create_leave():
    cmd = parse_command("박치료사 5월 5일 종일 휴무", context=_ctx())
    assert cmd.intent == AiIntent.CREATE_LEAVE


def test_parser_chart_number_explicit():
    cmd = parse_command("차트번호 12345 내일 10시 박치료사 도수30 예약", context=_ctx())
    assert cmd.chart_number == "12345"


def test_parser_chart_number_n_beon_hwanja():
    cmd = parse_command("12345번 환자 내일 오전 10시 박치료사 예약", context=_ctx())
    assert cmd.chart_number == "12345"


def test_parser_date_today():
    cmd = parse_command("박환자 오늘 10시 도수30 예약", context=_ctx())
    assert cmd.date_text == "오늘"


def test_parser_date_tomorrow():
    cmd = parse_command("박환자 내일 10시 도수30 예약", context=_ctx())
    assert cmd.date_text == "내일"


def test_parser_date_md():
    cmd = parse_command("박환자 4월30일 9시 도수30 예약", context=_ctx())
    assert cmd.date_text == "4월30일"


def test_parser_date_day_only():
    cmd = parse_command("박환자 30일 9시 도수30 예약", context=_ctx())
    assert cmd.date_text == "30일"


def test_parser_date_next_week():
    cmd = parse_command("박치료사 다음주 월요일 종일 휴무", context=_ctx())
    assert cmd.date_text and "다음주" in cmd.date_text and "월" in cmd.date_text


def test_parser_time_n_si():
    cmd = parse_command("박환자 4월30일 9시 도수30 예약", context=_ctx())
    assert cmd.time_text == "9시"


def test_parser_time_morning():
    cmd = parse_command("박환자 내일 오전 10시 도수30 예약", context=_ctx())
    assert cmd.time_text == "오전10시"


def test_parser_time_pm():
    cmd = parse_command("박환자 5월 10일 오후 2시 도수60 예약", context=_ctx())
    assert cmd.time_text == "오후2시"


def test_parser_time_colon():
    cmd = parse_command("박환자 내일 14:30 도수30 예약", context=_ctx())
    assert cmd.time_text == "14:30"


def test_parser_therapist_name():
    cmd = parse_command("박환자 내일 10시 박치료사 도수30 예약", context=_ctx())
    assert cmd.therapist_name == "박치료사"


def test_parser_treatment_single():
    cmd = parse_command("박환자 내일 10시 도수30 예약", context=_ctx())
    assert cmd.treatment_text and "도수30" in cmd.treatment_text


def test_parser_treatment_multi_with_short_aliases():
    """`도수30 주 충` 같이 다중 약어 입력 — 모두 추출."""
    cmd = parse_command("박환자 4월30일 9시 도수30 주 충 예약해줘", context=_ctx())
    assert cmd.treatment_text is not None
    raw_tokens = cmd.treatment_text.split()
    assert "도수30" in raw_tokens
    assert "주" in raw_tokens
    assert "충" in raw_tokens
    # treatment_items 도 3개 분리되어야 함
    assert len(cmd.treatment_items) == 3
    assert cmd.treatment_items[0].status == TreatmentItemStatus.NEEDS_CLARIFICATION
    assert cmd.treatment_items[0].source == DataSourceState.AI_EXTRACTED


def test_parser_treatment_eswt():
    cmd = parse_command("이영희 내일 15시 이치료사 ESWT 예약", context=_ctx())
    assert cmd.treatment_text and "ESWT" in cmd.treatment_text


def test_parser_patient_name_basic():
    cmd = parse_command("박환자 4월30일 9시 도수30 예약", context=_ctx())
    assert cmd.patient_name == "박환자"


def test_parser_memo_extraction():
    cmd = parse_command("박환자 내일 10시 도수30 예약 메모: 통증 심함", context=_ctx())
    assert cmd.memo == "통증 심함"


def test_parser_provider_failure_fallback():
    """provider 가 ProviderError 던져도 정규식 fallback 으로 결과 반환."""
    from app.ai.ai_provider import ProviderError

    class FailingProvider:
        name = "failing"

        def parse_command(self, raw_text, context):
            raise ProviderError("simulated failure")

    cmd = parse_command("박환자 내일 10시 도수30 예약", context=_ctx(), provider=FailingProvider())
    # fallback 으로 정규식이 동작
    assert cmd.intent == AiIntent.CREATE_APPOINTMENT
    assert cmd.date_text == "내일"


# ────────────────────────────── Resolver — 환자 ──────────────────────────────


@pytest.fixture
def db_session():
    """in-memory SQLite + SQLAlchemy ORM 세션. Patient / Employee / Treatment 시드."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    # 시드
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.add(Patient(id="p2", name="박환자", chart_no="22345", birth_date="1975-09-02", phone="010-3333-4444"))
    sess.add(Patient(id="p3", name="김민수", chart_no="33333", birth_date="1990-01-01", phone="010-5555-6666"))
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Employee(id="e2", name="김치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Treatment(id="t1", code="manual_30", name="도수치료 30분", short="도30", count_increment=1))
    sess.add(Treatment(id="t2", code="manual_60", name="도수치료 60분", short="도60", count_increment=1))
    sess.add(Treatment(id="t3", code="eswt", name="체외충격파", short="ESWT", count_increment=1))
    sess.add(Treatment(id="t4", code="injection", name="주사치료", short="주사", count_increment=1))

    # treatment_aliases (raw SQL)
    sess.execute(Base.metadata.tables["treatments"].insert().prefix_with("OR IGNORE"))  # noop, just to commit shape
    # alias 테이블이 ORM 모델에 없으므로 raw create + insert
    sess.execute(
        __import__("sqlalchemy").text(
            """
            CREATE TABLE IF NOT EXISTS treatment_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treatment_id TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(treatment_id, alias_name)
            )
            """
        )
    )
    aliases = [
        ("t1", "도30"), ("t1", "도수30"), ("t1", "도수치료30분"),
        ("t2", "도60"), ("t2", "도수60"),
        ("t3", "체외"), ("t3", "충격파"), ("t3", "ESWT"), ("t3", "충"),
        ("t4", "주사"), ("t4", "주"),
    ]
    text = __import__("sqlalchemy").text
    for tid, alias in aliases:
        sess.execute(
            text("INSERT INTO treatment_aliases (treatment_id, alias_name) VALUES (:tid, :alias)"),
            {"tid": tid, "alias": alias},
        )
    sess.commit()
    yield sess
    sess.close()


def test_resolve_patient_by_chart_number(db_session):
    res = resolve_patient(db_session, patient_name=None, chart_number="12345")
    assert len(res.candidates) == 1
    assert res.candidates[0].chart_no == "12345"
    assert res.candidates[0].name == "박환자"
    assert res.candidates[0].birth_date == "1980-04-15"
    assert res.candidates[0].phone == "010-1111-2222"
    assert res.match_rank == 1


def test_resolve_patient_by_name_homonym(db_session):
    """동명이인 — 박환자 2명 → 후보 2개."""
    res = resolve_patient(db_session, patient_name="박환자", chart_number=None)
    assert len(res.candidates) == 2
    assert {c.chart_no for c in res.candidates} == {"12345", "22345"}
    assert res.match_rank == 3


def test_resolve_patient_chart_name_mismatch(db_session):
    """차트번호 + 이름 불일치."""
    res = resolve_patient(db_session, patient_name="김민수", chart_number="12345")
    assert res.mismatch is True


def test_resolve_patient_chart_name_match(db_session):
    res = resolve_patient(db_session, patient_name="박환자", chart_number="12345")
    assert not res.mismatch
    assert len(res.candidates) == 1
    assert res.match_rank == 2


def test_resolve_patient_not_found(db_session):
    res = resolve_patient(db_session, patient_name="존재안함", chart_number="99999")
    assert res.not_found is True


# ────────────────────────────── Resolver — 치료사 ──────────────────────────────


def test_resolve_therapist_exact(db_session):
    res = resolve_therapist(db_session, therapist_name="박치료사")
    assert res.therapist_id == "e1"
    assert res.therapist_name == "박치료사"


def test_resolve_therapist_not_found(db_session):
    res = resolve_therapist(db_session, therapist_name="없는치료사")
    assert res.not_found is True


# ────────────────────────────── Resolver — 치료항목 ──────────────────────────────


def test_resolve_treatment_single_alias(db_session):
    items = resolve_treatment_items(db_session, treatment_text="도수30")
    assert len(items) == 1
    assert items[0].matched_treatment_id == "t1"
    assert items[0].matched_treatment_name == "도수치료 30분"
    assert items[0].status == TreatmentItemStatus.DB_VERIFIED


def test_resolve_treatment_multi_with_short(db_session):
    """도수30 주 충 — 3개 항목 매칭."""
    items = resolve_treatment_items(db_session, treatment_text="도수30 주 충")
    assert len(items) == 3
    raw_to_id = {i.raw_text: i.matched_treatment_id for i in items}
    assert raw_to_id["도수30"] == "t1"
    assert raw_to_id["주"] == "t4"
    assert raw_to_id["충"] == "t3"


def test_resolve_treatment_eswt(db_session):
    items = resolve_treatment_items(db_session, treatment_text="ESWT")
    assert items[0].matched_treatment_id == "t3"


def test_resolve_treatment_not_found(db_session):
    items = resolve_treatment_items(db_session, treatment_text="존재안함")
    assert items[0].status == TreatmentItemStatus.NOT_FOUND


def test_resolve_treatment_alias_conflict(db_session):
    """동일 alias 가 여러 치료항목과 매칭되면 ALIAS_CONFLICT."""
    text = __import__("sqlalchemy").text
    db_session.execute(
        text("INSERT INTO treatment_aliases (treatment_id, alias_name) VALUES ('t2', '주')"),
    )
    db_session.commit()
    items = resolve_treatment_items(db_session, treatment_text="주")
    assert items[0].status == TreatmentItemStatus.ALIAS_CONFLICT
    assert len(items[0].candidates) >= 2


# ────────────────────────────── Resolver — 날짜 ──────────────────────────────


def test_resolve_date_today():
    today = date(2026, 5, 4)
    res = resolve_date("오늘", current_calendar_year=2026, current_calendar_month=5, today=today)
    assert res.resolved_date == today


def test_resolve_date_tomorrow():
    today = date(2026, 5, 4)
    res = resolve_date("내일", current_calendar_year=2026, current_calendar_month=5, today=today)
    assert res.resolved_date == date(2026, 5, 5)


def test_resolve_date_md():
    today = date(2026, 5, 4)
    res = resolve_date("4월 30일", current_calendar_year=2026, current_calendar_month=5, today=today)
    assert res.resolved_date == date(2026, 4, 30)
    assert res.is_past is True


def test_resolve_date_day_only_uses_calendar_month():
    """30일 (월 누락) → 현재 캘린더 월 기준."""
    today = date(2026, 5, 4)
    res = resolve_date("30일", current_calendar_year=2026, current_calendar_month=5, today=today)
    assert res.resolved_date == date(2026, 5, 30)
    assert "5월" in res.note


def test_resolve_date_next_week_monday():
    today = date(2026, 5, 4)  # Monday
    res = resolve_date(
        "다음주 월요일", current_calendar_year=2026, current_calendar_month=5, today=today
    )
    assert res.resolved_date == date(2026, 5, 11)


def test_resolve_date_this_week_friday():
    today = date(2026, 5, 4)  # Mon
    res = resolve_date(
        "이번주 금요일", current_calendar_year=2026, current_calendar_month=5, today=today
    )
    assert res.resolved_date == date(2026, 5, 8)


def test_resolve_date_past_flagged():
    today = date(2026, 5, 4)
    res = resolve_date("4월 30일", current_calendar_year=2026, current_calendar_month=5, today=today)
    assert res.is_past is True


def test_resolve_date_ambiguous_invalid():
    res = resolve_date("내년 봄 어느날", current_calendar_year=2026, current_calendar_month=5)
    assert res.is_ambiguous is True


# ────────────────────────────── Resolver — 시간 ──────────────────────────────


def test_resolve_time_n_si():
    res = resolve_time("9시")
    assert res.hour == 9
    assert res.minute == 0


def test_resolve_time_morning():
    res = resolve_time("오전 10시")
    assert res.hour == 10


def test_resolve_time_pm():
    res = resolve_time("오후 2시")
    assert res.hour == 14


def test_resolve_time_colon():
    res = resolve_time("14:30")
    assert res.hour == 14
    assert res.minute == 30


def test_resolve_time_n_si_m_bun():
    res = resolve_time("9시 30분")
    assert res.hour == 9
    assert res.minute == 30


# ────────────────────────────── 안전 / 단위화 ──────────────────────────────


def test_resolver_does_not_modify_db(db_session):
    """resolver 호출 후 DB row 개수 변화 0."""
    before = db_session.query(Patient).count()
    resolve_patient(db_session, patient_name="박환자", chart_number=None)
    resolve_therapist(db_session, therapist_name="박치료사")
    resolve_treatment_items(db_session, treatment_text="도수30 주")
    after = db_session.query(Patient).count()
    assert before == after


def test_parser_no_external_api_call_in_phase2():
    """Phase 2 의 parse_command() 는 provider 없으면 외부 호출 0."""
    cmd = parse_command("박환자 내일 10시 도수30 예약", context=_ctx())
    # 정규식 fallback 만으로 동작 — ProviderError / network error 없음
    assert cmd.intent == AiIntent.CREATE_APPOINTMENT
