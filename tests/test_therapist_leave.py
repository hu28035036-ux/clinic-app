"""치료사 휴무 예약 차단 규칙 테스트 — docs/specs/02_치료사_휴무_규칙.md 참조.

- [정방향] 휴무 시간대를 피한 예약 → 200 (현재 백엔드는 어차피 차단 안 하므로 통과)
- [xfail]  휴무 시간대 예약 차단 → 400 (백엔드 미구현)
"""
from __future__ import annotations

from datetime import datetime

import pytest

from tests.harness.helpers import make_appointment
from tests.harness.seed_data import (
    FIXED_LEAVE_DATE,
    get_test_patient_id,
    get_test_therapist_id,
)


def _start(hour: int = 10, minute: int = 0, date_str: str = FIXED_LEAVE_DATE) -> datetime:
    return datetime.fromisoformat(f"{date_str}T{hour:02d}:{minute:02d}:00")


# ──────────────────────── xfail — 휴무 차단 (백엔드 미구현) ────────────────────────


@pytest.mark.xfail(
    reason="백엔드 차단 미구현 (spec 02) — 종일 휴무 치료사 예약은 차단되어야 함",
    strict=False,
)
def test_full_day_leave_blocks_morning(client):
    """김테스트치료사 (full 종일) 의 휴무일 오전 예약 → 400."""
    patient = get_test_patient_id("홍길동테스트")
    therapist = get_test_therapist_id("김테스트치료사")
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"], start_at=_start(10, 0),
    )
    assert resp.status_code == 400, f"종일 휴무 차단 안 됨: {resp.status_code}"


@pytest.mark.xfail(
    reason="백엔드 차단 미구현 (spec 02) — 종일 휴무 치료사 예약 (오후)",
    strict=False,
)
def test_full_day_leave_blocks_afternoon(client):
    """김테스트치료사 (full 종일) 의 휴무일 오후 예약 → 400."""
    patient = get_test_patient_id("김영희테스트")
    therapist = get_test_therapist_id("김테스트치료사")
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"], start_at=_start(14, 0),
    )
    assert resp.status_code == 400


@pytest.mark.xfail(
    reason="백엔드 차단 미구현 (spec 02) — 오전반차 < 12:00 차단",
    strict=False,
)
def test_morning_leave_blocks_before_noon(client):
    """이테스트치료사 (morning 오전반차) 의 휴무일 11:00 → 400."""
    patient = get_test_patient_id("홍길동테스트")
    therapist = get_test_therapist_id("이테스트치료사")
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"], start_at=_start(11, 0),
    )
    assert resp.status_code == 400


@pytest.mark.xfail(
    reason="백엔드 차단 미구현 (spec 02) — 오후반차 >= 12:00 차단",
    strict=False,
)
def test_afternoon_leave_blocks_after_noon(client):
    """박테스트치료사 (afternoon 오후반차) 의 휴무일 14:00 → 400."""
    patient = get_test_patient_id("박철수테스트")
    therapist = get_test_therapist_id("박테스트치료사")
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"], start_at=_start(14, 0),
    )
    assert resp.status_code == 400


# ──────────────────────── 정방향 — 반차 허용 시간대 ────────────────────────


def test_morning_leave_allows_after_noon(client):
    """이테스트치료사 (morning 오전반차) 의 휴무일 14:00 → 200 허용."""
    patient = get_test_patient_id("홍길동테스트")
    therapist = get_test_therapist_id("이테스트치료사")
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"], start_at=_start(14, 30),
    )
    assert resp.status_code == 200, resp.text


def test_afternoon_leave_allows_before_noon(client):
    """박테스트치료사 (afternoon 오후반차) 의 휴무일 10:00 → 200 허용."""
    patient = get_test_patient_id("박철수테스트")
    therapist = get_test_therapist_id("박테스트치료사")
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"], start_at=_start(10, 30),
    )
    assert resp.status_code == 200, resp.text


def test_normal_day_for_full_day_leave_therapist_works(client):
    """김테스트치료사 (휴무일 외) 다른 날짜 예약 → 200."""
    patient = get_test_patient_id("홍길동테스트")
    therapist = get_test_therapist_id("김테스트치료사")
    other_date = "2099-07-01"  # 시드 휴무 없음
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"],
        start_at=datetime.fromisoformat(f"{other_date}T10:00:00"),
    )
    assert resp.status_code == 200, resp.text
