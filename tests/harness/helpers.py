"""테스트 헬퍼 — 예약 생성/승인/취소를 한 줄로.

TestClient 를 받아 POST /api/appointments 등을 래핑.
응답 형식은 api.py 의 실제 반환을 따름:
    POST /api/appointments → {"id": "...", "status": "reserved"}
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


def build_appointment_payload(
    patient_id: str,
    start_at: datetime,
    treatment_codes: list,
    therapist_id: Optional[str] = None,
    duration_min: int = 30,
    memo: str = "",
):
    """POST /api/appointments 페이로드 빌더."""
    return {
        "patient_id": patient_id,
        "therapist_id": therapist_id,
        "treatment_codes": treatment_codes,
        "start_at": start_at.isoformat(),
        "duration_min": duration_min,
        "memo": memo,
        "assignments": [],
        "is_new_patient": False,
    }


def make_appointment(client, **kwargs):
    """예약 생성 후 Response 반환.

    검증은 호출 측에서 status_code 확인.
    """
    payload = build_appointment_payload(**kwargs)
    return client.post("/api/appointments", json=payload)


def approve_appointment(client, appointment_id: str, approved_by: str = "테스트원무과"):
    """예약 승인 (= status approved 처리)."""
    return client.post(
        f"/api/appointments/{appointment_id}/approve",
        json={"approved_by": approved_by},
    )


def cancel_appointment(client, appointment_id: str, memo: str = "테스트취소"):
    """예약 취소."""
    return client.post(
        f"/api/appointments/{appointment_id}/cancel",
        json={"memo": memo},
    )


def list_appointments(client, start: datetime, end: datetime):
    """기간 내 예약 목록."""
    return client.get(
        "/api/appointments",
        params={"start": start.isoformat(), "end": end.isoformat()},
    )
