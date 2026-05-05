"""Phase 6 — ai_safety 모듈 단위 테스트 (SSOT § 9 정합 보강).

검증 항목:
- check_privacy_payload — 12 금지 키 (재귀 검사)
- check_hallucination — 단정 표현 / 치료항목 status-id 정합
- 정책 상수 (PRIVACY_FORBIDDEN_KEYS / FORBIDDEN_PHRASES) 노출
- DB 의존 0 (순수 함수)
"""
from __future__ import annotations

from app.ai.ai_command_schema import (
    DataSourceState,
    ParsedCommand,
    ParserContext,
    TreatmentItem,
    TreatmentItemStatus,
)
from app.ai.ai_safety import (
    FORBIDDEN_PHRASES,
    PRIVACY_FORBIDDEN_KEYS,
    check_hallucination,
    check_privacy_payload,
)

# ────────────────────────────── 상수 노출 ──────────────────────────────


def test_privacy_forbidden_keys_present():
    """AI_SAFETY_POLICY § 3.2 의 7 항목이 키로 매핑되어야 함."""
    expected = {
        "patient_list",
        "all_phones",
        "all_birth_dates",
        "patient_memo",
        "appointment_memo",
        "all_appointments",
        "all_stats",
    }
    assert expected.issubset(set(PRIVACY_FORBIDDEN_KEYS))


def test_forbidden_phrases_include_yeyak_wallyo():
    """AI_SAFETY_POLICY § 2.2 의 "예약 완료" 표현 포함."""
    assert "예약 완료" in FORBIDDEN_PHRASES


# ────────────────────────────── Privacy ──────────────────────────────


def test_privacy_clean_payload():
    payload = {
        "raw_text": "박환자 내일 9시 도수30 예약",
        "current_calendar_year": 2026,
        "current_calendar_month": 5,
    }
    result = check_privacy_payload(payload)
    assert result.ok is True
    assert result.violations == []


def test_privacy_detects_patient_list():
    payload = {"patient_list": [{"name": "박환자"}]}
    result = check_privacy_payload(payload)
    assert result.ok is False
    assert any("patient_list" in v for v in result.violations)


def test_privacy_detects_nested_appointment_memo():
    payload = {"outer": {"inner": {"appointment_memo": "민감 내용"}}}
    result = check_privacy_payload(payload)
    assert result.ok is False


def test_privacy_dataclass_input():
    """ParserContext (dataclass) 도 dict 변환 후 검사 — PII 없으므로 ok."""
    ctx = ParserContext(
        raw_text="박환자 내일 9시 도수30 예약",
        current_calendar_year=2026,
        current_calendar_month=5,
    )
    result = check_privacy_payload(ctx)
    assert result.ok is True


def test_privacy_none_passes():
    result = check_privacy_payload(None)
    assert result.ok is True


# ────────────────────────────── Hallucination ──────────────────────────────


def test_hallucination_detects_completion_phrase():
    parsed = ParsedCommand(raw_text="박환자 내일 9시 도수30 예약")
    result = check_hallucination(parsed, response_text="예약 완료했습니다.")
    assert result.ok is False


def test_hallucination_clean_response():
    parsed = ParsedCommand(raw_text="박환자 내일 9시 도수30 예약")
    result = check_hallucination(
        parsed, response_text="예약 후보를 만들었습니다. 승인하면 예약이 등록됩니다."
    )
    assert result.ok is True


def test_hallucination_db_verified_without_id():
    """status=db_verified 이지만 matched_id 없으면 위반."""
    parsed = ParsedCommand(raw_text="도수30 예약")
    bad = TreatmentItem(
        raw_text="도수30",
        matched_treatment_id=None,
        status=TreatmentItemStatus.DB_VERIFIED,
    )
    result = check_hallucination(parsed, treatment_items=[bad])
    assert result.ok is False


def test_hallucination_unverified_with_id():
    """status=needs_clarification 인데 matched_id 채워지면 위반."""
    parsed = ParsedCommand(raw_text="주 예약")
    bad = TreatmentItem(
        raw_text="주",
        matched_treatment_id="t1",  # 채워짐
        status=TreatmentItemStatus.NEEDS_CLARIFICATION,
    )
    result = check_hallucination(parsed, treatment_items=[bad])
    assert result.ok is False


def test_hallucination_unverified_with_db_source():
    """status=needs_clarification 인데 source=db_verified 이면 위반."""
    parsed = ParsedCommand(raw_text="주 예약")
    bad = TreatmentItem(
        raw_text="주",
        source=DataSourceState.DB_VERIFIED,  # 위반
        status=TreatmentItemStatus.NEEDS_CLARIFICATION,
    )
    result = check_hallucination(parsed, treatment_items=[bad])
    assert result.ok is False


def test_hallucination_empty_raw_with_filled_fields():
    parsed = ParsedCommand(raw_text="", patient_name="박환자")
    result = check_hallucination(parsed)
    assert result.ok is False


def test_hallucination_clean_consistent_treatment():
    """status=db_verified + matched_id 채움 → 정합."""
    parsed = ParsedCommand(raw_text="도수30 예약")
    good = TreatmentItem(
        raw_text="도수30",
        matched_treatment_id="t1",
        matched_treatment_name="도수치료 30분",
        source=DataSourceState.DB_VERIFIED,
        status=TreatmentItemStatus.DB_VERIFIED,
    )
    result = check_hallucination(parsed, treatment_items=[good])
    assert result.ok is True
