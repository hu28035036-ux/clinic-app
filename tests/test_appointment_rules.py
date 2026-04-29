"""예약 생성 핵심 규칙 테스트 — docs/specs/01_예약_규칙.md 참조.

분류:
- [정방향] 현재 백엔드가 검증하는 규칙 → PASS
- [정방향] 백엔드가 일부러 허용하는 동작 (비도수 같은 시간 중복) → PASS
- [xfail]  spec 에 정의되었지만 백엔드 미구현 (도수치료 중복 차단) → XFAIL
"""
from __future__ import annotations

from datetime import datetime

import pytest

from tests.harness.helpers import build_appointment_payload, make_appointment
from tests.harness.seed_data import (
    get_test_patient_id,
    get_test_therapist_id,
)

NORMAL_DATE = "2099-06-10"  # 시드 휴무와 겹치지 않는 미래 날짜


def _start(hour: int = 10, minute: int = 0, date_str: str = NORMAL_DATE) -> datetime:
    return datetime.fromisoformat(f"{date_str}T{hour:02d}:{minute:02d}:00")


# ──────────────────────── 정방향 — 필수값 / 외래키 ────────────────────────


def test_empty_treatment_codes_rejected(client):
    """치료항목 비어 있으면 400."""
    patient_id = get_test_patient_id("홍길동테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")  # 오전반차 — 13:00 OK 시간대
    resp = make_appointment(
        client,
        patient_id=patient_id,
        therapist_id=therapist_id,
        treatment_codes=[],
        start_at=_start(13, 0),
    )
    assert resp.status_code == 400
    assert "치료항목" in resp.json().get("detail", "")


def test_invalid_treatment_code_filtered_out(client):
    """존재하지 않는 코드는 무시되고 결국 빈 리스트 → 400.

    현재 구현: valid_codes 와 교집합 후 비어 있으면 400.
    """
    patient_id = get_test_patient_id("홍길동테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")
    resp = make_appointment(
        client,
        patient_id=patient_id,
        therapist_id=therapist_id,
        treatment_codes=["nonexistent_code_xyz"],
        start_at=_start(13, 30),
    )
    assert resp.status_code == 400


def test_missing_required_fields_rejected(client):
    """patient_id 누락 → Pydantic 422."""
    payload = build_appointment_payload(
        patient_id="dummy",
        start_at=_start(14, 0),
        treatment_codes=["manual30"],
    )
    payload.pop("patient_id")
    resp = client.post("/api/appointments", json=payload)
    assert resp.status_code == 422


def test_list_appointments_requires_range(client):
    """GET /api/appointments 는 start, end 필수 → 누락 시 422."""
    resp = client.get("/api/appointments")
    assert resp.status_code == 422


# ──────────────────────── 정방향 — 비도수 중복 허용 ────────────────────────


def test_two_eswt_same_slot_allowed(client):
    """eswt 만 있는 두 예약을 같은 치료사·같은 시간에 → 둘 다 200.

    spec 01: 도수치료가 포함되지 않은 예약은 같은 슬롯에 여럿 허용.
    """
    patient_a = get_test_patient_id("홍길동테스트")
    patient_b = get_test_patient_id("김영희테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")
    slot = _start(15, 0)

    r1 = make_appointment(
        client, patient_id=patient_a, therapist_id=therapist_id,
        treatment_codes=["eswt"], start_at=slot,
    )
    r2 = make_appointment(
        client, patient_id=patient_b, therapist_id=therapist_id,
        treatment_codes=["eswt"], start_at=slot,
    )
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text


def test_injection_and_eswt_same_slot_allowed(client):
    """injection 과 eswt 만 있는 두 예약 같은 슬롯 → 허용."""
    patient_a = get_test_patient_id("홍길동테스트")
    patient_b = get_test_patient_id("박철수테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")
    slot = _start(15, 30)

    r1 = make_appointment(
        client, patient_id=patient_a, therapist_id=therapist_id,
        treatment_codes=["injection"], start_at=slot,
    )
    r2 = make_appointment(
        client, patient_id=patient_b, therapist_id=therapist_id,
        treatment_codes=["eswt"], start_at=slot,
    )
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text


# ──────────────────────── xfail — 도수치료 중복 차단 (백엔드 미구현) ────────────────────────


@pytest.mark.xfail(
    reason="백엔드 차단 미구현 (spec 01 §1) — 도수치료 같은 슬롯 차단 코드가 추가되면 GREEN 으로 전환",
    strict=False,
)
def test_two_manual30_same_slot_blocked(client):
    """manual30 두 예약을 같은 치료사·같은 시간에 → 두 번째 차단되어야 함."""
    patient_a = get_test_patient_id("홍길동테스트")
    patient_b = get_test_patient_id("김영희테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")
    slot = _start(16, 0)

    r1 = make_appointment(
        client, patient_id=patient_a, therapist_id=therapist_id,
        treatment_codes=["manual30"], start_at=slot,
    )
    assert r1.status_code == 200, r1.text

    r2 = make_appointment(
        client, patient_id=patient_b, therapist_id=therapist_id,
        treatment_codes=["manual30"], start_at=slot,
    )
    assert r2.status_code == 400, f"중복 차단 안 됨 (응답: {r2.status_code})"


@pytest.mark.xfail(
    reason="백엔드 차단 미구현 (spec 01 §1) — manual60 도수치료 중복",
    strict=False,
)
def test_two_manual60_same_slot_blocked(client):
    """manual60 두 예약을 같은 치료사·같은 시간 → 차단."""
    patient_a = get_test_patient_id("홍길동테스트")
    patient_b = get_test_patient_id("박철수테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")
    slot = _start(16, 30)

    r1 = make_appointment(
        client, patient_id=patient_a, therapist_id=therapist_id,
        treatment_codes=["manual60"], start_at=slot, duration_min=60,
    )
    assert r1.status_code == 200, r1.text

    r2 = make_appointment(
        client, patient_id=patient_b, therapist_id=therapist_id,
        treatment_codes=["manual60"], start_at=slot, duration_min=60,
    )
    assert r2.status_code == 400


@pytest.mark.xfail(
    reason="백엔드 차단 미구현 (spec 01 §1) — 신규 또는 기존 중 하나라도 도수 포함이면 차단",
    strict=False,
)
def test_eswt_then_manual30_same_slot_blocked(client):
    """기존 eswt + 신규 manual30 같은 슬롯 → 신규에 도수 포함이므로 차단."""
    patient_a = get_test_patient_id("홍길동테스트")
    patient_b = get_test_patient_id("김영희테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")
    slot = _start(17, 0)

    r1 = make_appointment(
        client, patient_id=patient_a, therapist_id=therapist_id,
        treatment_codes=["eswt"], start_at=slot,
    )
    assert r1.status_code == 200

    r2 = make_appointment(
        client, patient_id=patient_b, therapist_id=therapist_id,
        treatment_codes=["manual30"], start_at=slot,
    )
    assert r2.status_code == 400


@pytest.mark.skip(
    reason=(
        "이 테스트는 도수치료 중복 차단 로직이 백엔드에 추가된 후에만 의미가 있음. "
        "현재는 차단 자체가 없어서 두 번째 예약도 어차피 통과 → 검증력 없음. "
        "차단 코드 추가 시점에 이 marker 를 제거하고 정방향 테스트로 활성화할 것."
    )
)
def test_canceled_manual_excluded_from_duplicate_check(client):
    """기존 manual30 을 취소 후 같은 슬롯에 새 manual30 → 허용되어야 함.

    [상태] 백엔드 차단 도입 후 활성화. spec 01 §1 (취소된 예약은 중복 판단에서 제외).
    """
    patient_a = get_test_patient_id("홍길동테스트")
    patient_b = get_test_patient_id("김영희테스트")
    therapist_id = get_test_therapist_id("이테스트치료사")
    slot = _start(17, 30)

    r1 = make_appointment(
        client, patient_id=patient_a, therapist_id=therapist_id,
        treatment_codes=["manual30"], start_at=slot,
    )
    assert r1.status_code == 200
    aid = r1.json()["id"]

    # 첫 예약 취소
    cancel = client.post(f"/api/appointments/{aid}/cancel", json={"memo": "테스트"})
    assert cancel.status_code == 200, cancel.text

    # 같은 슬롯에 새 manual30 — 취소된 예약은 무시되어야 하므로 허용
    r2 = make_appointment(
        client, patient_id=patient_b, therapist_id=therapist_id,
        treatment_codes=["manual30"], start_at=slot,
    )
    assert r2.status_code == 200, f"취소된 예약이 중복으로 잡힘 (응답: {r2.status_code})"
