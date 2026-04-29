"""완료 카운트 / 통계 규칙 테스트 — docs/specs/03_완료카운트_통계_규칙.md 참조.

검증 대상: 예약 승인(approve) 시 PatientTreatmentCount.done_count 가
- 항목별로 정확히 +1 만 증가하는지 (manual60 도 +1, +2 가 아님)
- 도수치료와 eswt 가 별도 항목으로 집계되는지
- 새로 추가된 manual90 도 별도 항목으로 집계되는지
- 취소된 예약은 카운트에 포함되지 않는지
"""
from __future__ import annotations

from datetime import datetime

import pytest

from tests.harness.helpers import approve_appointment, make_appointment
from tests.harness.seed_data import (
    get_test_therapist_id,
)

# 통계 테스트용 고정 미래 날짜 — 다른 테스트와 슬롯 겹치지 않도록 새 날짜 사용
STATS_DATE = "2098-08-10"


def _start(hour: int) -> datetime:
    return datetime.fromisoformat(f"{STATS_DATE}T{hour:02d}:00:00")


def _get_done_count(patient_id: str, treatment_code: str) -> int:
    """PatientTreatmentCount.done_count 직접 조회. 행 없으면 0."""
    from app.database import SessionLocal
    from app.models import models

    db = SessionLocal()
    try:
        t = db.query(models.Treatment).filter_by(code=treatment_code).first()
        if not t:
            return 0
        row = db.query(models.PatientTreatmentCount).filter_by(
            patient_id=patient_id, treatment_id=t.id,
        ).first()
        return int(row.done_count) if row else 0
    finally:
        db.close()


@pytest.fixture
def fresh_patient(client):
    """이 테스트 모듈 전용 환자 — 다른 테스트의 카운트 누적과 격리.

    각 테스트가 독립적으로 카운트를 검증할 수 있도록 매번 새 환자 생성.
    """
    import uuid as _uuid

    from app.database import SessionLocal
    from app.models import models

    name = f"통계테스트환자_{_uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        p = models.Patient(name=name)
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
    finally:
        db.close()


def _make_and_approve(client, patient_id, therapist_id, codes, hour, duration=30):
    """예약 생성 → 승인. (appointment_id, approve_status) 반환."""
    r = make_appointment(
        client, patient_id=patient_id, therapist_id=therapist_id,
        treatment_codes=codes, start_at=_start(hour), duration_min=duration,
    )
    assert r.status_code == 200, f"예약 생성 실패: {r.text}"
    aid = r.json()["id"]
    a = approve_appointment(client, aid)
    assert a.status_code == 200, f"승인 실패: {a.text}"
    return aid


# ──────────────────────── 항목별 1카운트 ────────────────────────


def test_manual30_approve_counts_one(client, fresh_patient):
    """manual30 1건 승인 → manual30 done_count == 1."""
    therapist = get_test_therapist_id("이테스트치료사")
    _make_and_approve(client, fresh_patient, therapist, ["manual30"], hour=9)
    assert _get_done_count(fresh_patient, "manual30") == 1
    assert _get_done_count(fresh_patient, "manual60") == 0


def test_manual60_approve_counts_one_not_two(client, fresh_patient):
    """⚠ manual60 1건 승인 → manual60 done_count == 1 (NOT 2).

    과거에 manual60 = 2 카운트로 집계하던 시기가 있었으나 현 정책은 1카운트.
    """
    therapist = get_test_therapist_id("이테스트치료사")
    _make_and_approve(client, fresh_patient, therapist, ["manual60"],
                      hour=10, duration=60)
    cnt = _get_done_count(fresh_patient, "manual60")
    assert cnt == 1, f"manual60 카운트가 {cnt} (1이어야 함). manual60=2 정책으로 회귀하지 말 것."


def test_manual30_and_manual60_each_count_one(client, fresh_patient):
    """한 예약에 manual30 + manual60 함께 → 각각 +1."""
    therapist = get_test_therapist_id("이테스트치료사")
    _make_and_approve(
        client, fresh_patient, therapist, ["manual30", "manual60"],
        hour=11, duration=90,
    )
    assert _get_done_count(fresh_patient, "manual30") == 1
    assert _get_done_count(fresh_patient, "manual60") == 1


# ──────────────────────── 새 항목 (manual90) 별도 집계 ────────────────────────


def test_manual90_counted_separately(client, fresh_patient):
    """시드된 manual90 1건 승인 → manual90 별도 +1, 기존 manual30/60 영향 없음."""
    therapist = get_test_therapist_id("이테스트치료사")
    _make_and_approve(
        client, fresh_patient, therapist, ["manual90"],
        hour=13, duration=90,
    )
    assert _get_done_count(fresh_patient, "manual90") == 1
    assert _get_done_count(fresh_patient, "manual30") == 0
    assert _get_done_count(fresh_patient, "manual60") == 0


# ──────────────────────── eswt 별도 집계 ────────────────────────


def test_eswt_counted_separately_from_manual(client, fresh_patient):
    """eswt 1건 승인 → eswt 카운트만 +1, 도수치료 카운트는 영향 없음."""
    therapist = get_test_therapist_id("이테스트치료사")
    _make_and_approve(
        client, fresh_patient, therapist, ["eswt"], hour=15,
    )
    assert _get_done_count(fresh_patient, "eswt") == 1
    assert _get_done_count(fresh_patient, "manual30") == 0
    assert _get_done_count(fresh_patient, "manual60") == 0


# ──────────────────────── 취소된 예약 제외 ────────────────────────


def test_canceled_reservation_does_not_count(client, fresh_patient):
    """예약 → 취소 (승인 전) → 카운트 변화 없음."""
    therapist = get_test_therapist_id("이테스트치료사")
    r = make_appointment(
        client, patient_id=fresh_patient, therapist_id=therapist,
        treatment_codes=["manual30"], start_at=_start(16),
    )
    assert r.status_code == 200, r.text
    aid = r.json()["id"]

    cancel = client.post(f"/api/appointments/{aid}/cancel", json={"memo": "테스트"})
    assert cancel.status_code == 200, cancel.text

    # 승인 안 된 예약 취소 → done_count 그대로 0
    assert _get_done_count(fresh_patient, "manual30") == 0
