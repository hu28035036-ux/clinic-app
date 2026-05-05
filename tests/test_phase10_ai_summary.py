"""Phase 10 — summarize_today / summarize_tomorrow / analyze_stats 단위 테스트.

검증 (AI_FEATURE_MASTER_PLAN § 5.4):
- 읽기 전용 (DB 변경 0)
- 모든 수치 = DB 쿼리 결과 (AI 임의 생성 ⊥)
- canceled 제외
- 치료사별 / 시간대별 / 치료항목별 카운트
- 0건 처리
- manual30=1 / manual60=1 정책 (가중치 합산 ⊥) — 본 모듈은 단순 row 카운팅
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.ai_summary import (
    analyze_stats_period,
    build_analysis_preview,
    build_daily_summary_text,
    build_stats_analysis_text,
    build_summary_preview,
    summarize_for_date,
    summarize_today,
    summarize_tomorrow,
)
from app.models.models import (
    Appointment,
    Base,
    Employee,
    Patient,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = Session(engine)
    sess.add(Patient(id="p1", name="박환자", chart_no="12345", birth_date="1980-04-15", phone="010-1111-2222"))
    sess.add(Patient(id="p2", name="김민수", chart_no="33333", birth_date="1990-01-01", phone="010-5555-6666"))
    sess.add(Employee(id="e1", name="박치료사", role="therapist", color="#9CA3AF", active=True))
    sess.add(Employee(id="e2", name="김치료사", role="therapist", color="#9CA3AF", active=True))
    # 5월 30일: 박치료사 (9시 manual_30 / 10시 manual_60), 김치료사 (11시 eswt), 14시 canceled
    sess.add(Appointment(
        id="a1", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 9, 0),
        end_at=datetime(2026, 5, 30, 9, 30),
        status="reserved", treatment_codes='["manual_30"]',
    ))
    sess.add(Appointment(
        id="a2", patient_id="p2", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 10, 0),
        end_at=datetime(2026, 5, 30, 11, 0),
        status="reserved", treatment_codes='["manual_60"]',
    ))
    sess.add(Appointment(
        id="a3", patient_id="p1", therapist_id="e2",
        start_at=datetime(2026, 5, 30, 11, 0),
        end_at=datetime(2026, 5, 30, 11, 30),
        status="reserved", treatment_codes='["eswt"]',
    ))
    sess.add(Appointment(
        id="a4-canceled", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 14, 0),
        end_at=datetime(2026, 5, 30, 14, 30),
        status="canceled", treatment_codes='["manual_30"]',
    ))
    # 5월 31일 (내일 시뮬레이션)
    sess.add(Appointment(
        id="a5", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 31, 9, 0),
        end_at=datetime(2026, 5, 31, 9, 30),
        status="reserved", treatment_codes='["manual_30"]',
    ))
    # 6월 1일 (기간 분석용)
    sess.add(Appointment(
        id="a6", patient_id="p2", therapist_id="e2",
        start_at=datetime(2026, 6, 1, 15, 0),
        end_at=datetime(2026, 6, 1, 15, 30),
        status="reserved", treatment_codes='["eswt"]',
    ))
    sess.commit()
    yield sess
    sess.close()


# ────────────────────────────── 1. 일일 요약 ──────────────────────────────


def test_summarize_for_date_total_count(db_session):
    s = summarize_for_date(db_session, date(2026, 5, 30))
    # canceled 제외 → 3건
    assert s.total_count == 3
    assert s.canceled_count == 1


def test_summarize_for_date_by_therapist(db_session):
    s = summarize_for_date(db_session, date(2026, 5, 30))
    assert s.by_therapist == {"박치료사": 2, "김치료사": 1}


def test_summarize_for_date_by_hour(db_session):
    s = summarize_for_date(db_session, date(2026, 5, 30))
    assert s.by_hour == {9: 1, 10: 1, 11: 1}


def test_summarize_for_date_by_treatment(db_session):
    s = summarize_for_date(db_session, date(2026, 5, 30))
    assert s.by_treatment == {"manual_30": 1, "manual_60": 1, "eswt": 1}


def test_summarize_for_date_empty(db_session):
    s = summarize_for_date(db_session, date(2026, 7, 15))
    assert s.total_count == 0
    assert s.by_therapist == {}


def test_summarize_today_uses_today_param(db_session):
    s = summarize_today(db_session, today=date(2026, 5, 30))
    assert s.target_date == date(2026, 5, 30)
    assert s.total_count == 3


def test_summarize_tomorrow_uses_today_plus_one(db_session):
    s = summarize_tomorrow(db_session, today=date(2026, 5, 30))
    assert s.target_date == date(2026, 5, 31)
    assert s.total_count == 1


# ────────────────────────────── 2. 기간 통계 ──────────────────────────────


def test_analyze_period_total(db_session):
    a = analyze_stats_period(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 6, 1)
    )
    # 5/30 (3) + 5/31 (1) + 6/1 (1) = 5
    assert a.total_count == 5


def test_analyze_period_by_day(db_session):
    a = analyze_stats_period(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 6, 1)
    )
    assert a.by_day == {"2026-05-30": 3, "2026-05-31": 1, "2026-06-01": 1}


def test_analyze_period_filter_by_therapist(db_session):
    a = analyze_stats_period(
        db_session,
        period_start=date(2026, 5, 30),
        period_end=date(2026, 6, 1),
        therapist_id_filter="e1",
    )
    # e1: 5/30 두 건 + 5/31 한 건 = 3
    assert a.total_count == 3


def test_analyze_period_filter_by_treatment(db_session):
    a = analyze_stats_period(
        db_session,
        period_start=date(2026, 5, 30),
        period_end=date(2026, 6, 1),
        treatment_code_filter="eswt",
    )
    # eswt: 5/30 1건 + 6/1 1건 = 2
    assert a.total_count == 2


def test_analyze_period_invalid_range_raises(db_session):
    with pytest.raises(ValueError):
        analyze_stats_period(
            db_session,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 5, 30),
        )


# ────────────────────────────── 3. 한국어 요약 텍스트 ──────────────────────────────


def test_summary_text_includes_total_and_breakdowns(db_session):
    s = summarize_for_date(db_session, date(2026, 5, 30))
    text = build_daily_summary_text(s)
    assert "총 예약: 3건" in text
    assert "박치료사" in text
    assert "manual_30" in text
    # canceled 표시
    assert "취소: 1건" in text


def test_analysis_text_includes_period_and_peak(db_session):
    a = analyze_stats_period(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 6, 1)
    )
    text = build_stats_analysis_text(a)
    assert "2026-05-30 ~ 2026-06-01" in text
    assert "총 예약: 5건" in text
    assert "가장 바쁜 시간" in text


# ────────────────────────────── 4. preview ──────────────────────────────


def test_summary_preview_marked_read_only(db_session):
    s = summarize_for_date(db_session, date(2026, 5, 30))
    preview = build_summary_preview(s)
    assert preview["read_only"] is True
    assert preview["total_count"] == 3


def test_analysis_preview_marked_read_only(db_session):
    a = analyze_stats_period(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 6, 1)
    )
    preview = build_analysis_preview(a)
    assert preview["read_only"] is True


# ────────────────────────────── 5. 안전 — DB 직접 수정 0 ──────────────────────────────


def test_summary_does_not_modify_db(db_session):
    before = db_session.query(Appointment).count()
    summarize_for_date(db_session, date(2026, 5, 30))
    analyze_stats_period(
        db_session, period_start=date(2026, 5, 30), period_end=date(2026, 6, 1)
    )
    assert db_session.query(Appointment).count() == before


def test_summary_no_external_api_call(db_session):
    """본 모듈은 provider 미사용 — 외부 호출 ⊥. 호출 가능 여부만 검증 (응답이 결정적)."""
    s = summarize_for_date(db_session, date(2026, 5, 30))
    text1 = build_daily_summary_text(s)
    text2 = build_daily_summary_text(s)
    # 결정적 — 동일 입력 → 동일 출력 (AI 임의 생성 ⊥)
    assert text1 == text2


# ────────────────────────────── 6. manual_60 = 1 카운트 정책 ──────────────────────────────


def test_treatment_count_uses_simple_row_count(db_session):
    """manual_60 도 1건으로 카운트 — 가중치 합산 (count_increment 곱셈) ⊥."""
    s = summarize_for_date(db_session, date(2026, 5, 30))
    # manual_60 1건 (a2), manual_30 1건 (a1), eswt 1건 (a3) — 모두 1
    assert s.by_treatment["manual_60"] == 1
    assert s.by_treatment["manual_30"] == 1
