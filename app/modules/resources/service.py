"""modules.resources.service — Resource read/write + 충돌 검사 (post-19-P / 20-3-5).

# SAFETY: 자원 충돌 검사 = 같은 resource_id + 시간 겹침 + status != canceled.
# capacity=1 정책 (사용자 §7-7 (i)) — 시간 겹침 1건이라도 발견되면 충돌.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import models


def serialize_resource(resource: Any) -> dict[str, Any]:
    """Resource ORM → 7키 응답 dict."""
    return {
        "id": resource.id,
        "type": resource.type,
        "name": resource.name,
        "capacity": resource.capacity,
        "active": bool(resource.active),
        "sort_order": resource.sort_order or 0,
        "created_at": (
            resource.created_at.isoformat() if resource.created_at else None
        ),
    }


def serialize_resources(resources: list[Any]) -> list[dict[str, Any]]:
    return [serialize_resource(r) for r in resources]


def check_resource_conflict(
    db: Session,
    *,
    resource_id: Optional[str],
    start_at: datetime,
    end_at: datetime,
    exclude_appt_id: Optional[str] = None,
) -> Optional[Any]:
    """자원 + 시간 겹침 충돌 검사. 충돌 발견 시 첫 Appointment 반환, 없으면 None.

    # NOTE: capacity=1 정책 (사용자 §7-7 (i)) — 시간 겹침 1건이라도 발견되면 충돌.
    # NOTE: status='canceled' 는 제외. 자기 자신 (exclude_appt_id) 도 제외 (PUT 흐름).
    """
    if not resource_id:
        return None
    q = (
        db.query(models.Appointment)
        .filter(models.Appointment.resource_id == resource_id)
        .filter(models.Appointment.status != "canceled")
        .filter(models.Appointment.start_at < end_at)
        .filter(models.Appointment.end_at > start_at)
    )
    if exclude_appt_id:
        q = q.filter(models.Appointment.id != exclude_appt_id)
    return q.first()


__all__ = [
    "check_resource_conflict",
    "serialize_resource",
    "serialize_resources",
]
