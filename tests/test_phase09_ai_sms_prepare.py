"""Phase 9 — prepare_sms 단위 테스트.

검증 (AI_FEATURE_MASTER_PLAN § 5.3 prepare_sms):
- 자동 발송 ⊥ — 본 모듈은 발송 함수 미제공
- 외부 AI API 호출 0 (provider 미사용)
- 대상 날짜 예약자 N명 → 텍스트 출력
- canceled 예약 자동 제외
- 치료사 / 치료항목 필터
- 체크박스 토글
- DB 직접 수정 0
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.ai_sms_prepare import (
    build_sms_preview,
    prepare_sms_for_date,
    toggle_selection,
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
    # 5월 30일 예약 3건 (1건 canceled)
    sess.add(Appointment(
        id="a1", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 9, 0),
        end_at=datetime(2026, 5, 30, 9, 30),
        status="reserved", treatment_codes='["manual_30"]',
    ))
    sess.add(Appointment(
        id="a2", patient_id="p2", therapist_id="e2",
        start_at=datetime(2026, 5, 30, 10, 0),
        end_at=datetime(2026, 5, 30, 10, 30),
        status="reserved", treatment_codes='["eswt"]',
    ))
    sess.add(Appointment(
        id="a3-canceled", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 30, 14, 0),
        end_at=datetime(2026, 5, 30, 14, 30),
        status="canceled", treatment_codes='["manual_30"]',
    ))
    # 다른 날짜 1건
    sess.add(Appointment(
        id="a4", patient_id="p1", therapist_id="e1",
        start_at=datetime(2026, 5, 31, 9, 0),
        end_at=datetime(2026, 5, 31, 9, 30),
        status="reserved", treatment_codes='["manual_30"]',
    ))
    sess.commit()
    yield sess
    sess.close()


# ────────────────────────────── 1. 정상 ──────────────────────────────


def test_prepare_returns_appointments_for_date(db_session):
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    # canceled 제외 → 2건
    assert len(res.rows) == 2
    ids = [r.appointment_id for r in res.rows]
    assert "a1" in ids
    assert "a2" in ids
    assert "a3-canceled" not in ids


def test_prepare_excludes_other_dates(db_session):
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    assert "a4" not in [r.appointment_id for r in res.rows]


def test_prepare_filters_by_therapist(db_session):
    res = prepare_sms_for_date(
        db_session, target_date=date(2026, 5, 30), therapist_id_filter="e1"
    )
    assert len(res.rows) == 1
    assert res.rows[0].appointment_id == "a1"


def test_prepare_filters_by_treatment(db_session):
    res = prepare_sms_for_date(
        db_session, target_date=date(2026, 5, 30), treatment_code_filter="eswt"
    )
    assert len(res.rows) == 1
    assert res.rows[0].appointment_id == "a2"


def test_prepare_zero_appointments(db_session):
    """대상 날짜에 예약 0건 → note 안내 메시지 + 빈 rows."""
    res = prepare_sms_for_date(db_session, target_date=date(2026, 6, 15))
    assert res.rows == []
    assert "0명" in res.note


def test_prepare_default_template_includes_name_and_time(db_session):
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    sms = res.rows[0].sms_text
    assert "박환자" in sms or "김민수" in sms
    assert "09:00" in sms or "10:00" in sms


def test_prepare_custom_template(db_session):
    res = prepare_sms_for_date(
        db_session,
        target_date=date(2026, 5, 30),
        template="[{name}] {time}",
    )
    for r in res.rows:
        assert r.sms_text.startswith("[")


def test_prepare_output_paste_concatenates_selected(db_session):
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    assert res.output_paste
    # 두 줄 이상
    assert "\n\n" in res.output_paste


# ────────────────────────────── 2. 체크박스 토글 ──────────────────────────────


def test_toggle_selection_excludes_from_paste(db_session):
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    # a1 선택 해제
    res = toggle_selection(res, appointment_ids=["a1"])
    a1_text = next(r.sms_text for r in res.rows if r.appointment_id == "a1")
    a2_text = next(r.sms_text for r in res.rows if r.appointment_id == "a2")
    assert a1_text not in res.output_paste
    assert a2_text in res.output_paste


def test_toggle_back_includes_in_paste(db_session):
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    res = toggle_selection(res, appointment_ids=["a1"])
    res = toggle_selection(res, appointment_ids=["a1"])  # 다시 토글 → 원복
    a1_text = next(r.sms_text for r in res.rows if r.appointment_id == "a1")
    assert a1_text in res.output_paste


# ────────────────────────────── 3. preview ──────────────────────────────


def test_preview_marks_auto_send_disabled(db_session):
    """preview 의 auto_send_disabled=True / actions 에 '발송' 없음."""
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    preview = build_sms_preview(res)
    assert preview["auto_send_disabled"] is True
    assert "발송" not in preview["actions"]


def test_preview_rows_include_phone_for_internal_display(db_session):
    """내부 표시 — 환자 연락처 / 이름 포함 (외부 AI API 전송이 아니므로 OK)."""
    res = prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    preview = build_sms_preview(res)
    assert preview["rows"][0]["patient_phone"]
    assert preview["rows"][0]["patient_name"]


# ────────────────────────────── 4. 안전 — 자동 발송 ⊥ ──────────────────────────────


def test_module_does_not_expose_send_function():
    """본 모듈은 발송 함수 자체를 노출하지 않음 — 자동 발송 ⊥ 게이트."""
    import app.ai.ai_sms_prepare as mod

    forbidden_names = ("send", "send_sms", "dispatch", "send_now", "auto_send")
    public = [n for n in dir(mod) if not n.startswith("_")]
    for name in forbidden_names:
        assert name not in public, f"{name} 가 public API 에 있음 — 자동 발송 ⊥ 위반"


# ────────────────────────────── 5. 안전 — DB 직접 수정 0 ──────────────────────────────


def test_prepare_does_not_modify_db(db_session):
    before_a = db_session.query(Appointment).count()
    before_p = db_session.query(Patient).count()
    prepare_sms_for_date(db_session, target_date=date(2026, 5, 30))
    after_a = db_session.query(Appointment).count()
    after_p = db_session.query(Patient).count()
    assert before_a == after_a
    assert before_p == after_p
