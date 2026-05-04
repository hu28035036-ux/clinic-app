"""modules.doctors.service — Doctor read/write 헬퍼 (post-19-P / 20-3-3)."""
from __future__ import annotations

from typing import Any


def serialize_doctor(doctor: Any) -> dict[str, Any]:
    """Doctor ORM → 8키 응답 dict (DOCTOR_RESPONSE_KEYS 정합).

    # NOTE: created_at 은 ISO 문자열 (None safe).
    """
    return {
        "id": doctor.id,
        "name": doctor.name,
        "specialty": doctor.specialty,
        "license_no": doctor.license_no,
        "color": doctor.color,
        "active": bool(doctor.active),
        "sort_order": doctor.sort_order or 0,
        "created_at": (
            doctor.created_at.isoformat() if doctor.created_at else None
        ),
    }


def serialize_doctors(doctors: list[Any]) -> list[dict[str, Any]]:
    """list[Doctor] → list[dict]."""
    return [serialize_doctor(d) for d in doctors]


__all__ = ["serialize_doctor", "serialize_doctors"]
