from __future__ import annotations

from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.models import models


def serialize_category(c: models.EmployeeCategory) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "color": c.color or "#9CA3AF",
        "active": bool(c.active),
        "sort_order": c.sort_order or 0,
    }


def serialize_state(state: models.InventoryCategoryState | None, category_id: str) -> dict:
    return {
        "id": state.id if state else category_id,
        "category_id": category_id,
        "last_author": state.last_author if state else "",
        "last_written_at": state.last_written_at.isoformat() if state and state.last_written_at else None,
        "updated_at": state.updated_at.isoformat() if state and state.updated_at else None,
    }


def serialize_field(field: models.InventoryField) -> dict:
    return {
        "id": field.id,
        "category_id": field.category_id,
        "name": field.name,
        "field_type": field.field_type or "text",
        "sort_order": field.sort_order or 0,
        "active": bool(field.active),
        "created_at": field.created_at.isoformat() if field.created_at else None,
        "updated_at": field.updated_at.isoformat() if field.updated_at else None,
    }


def serialize_item(item: models.InventoryItem, values_by_item: dict[str, dict[str, str]] | None = None) -> dict:
    return {
        "id": item.id,
        "category_id": item.category_id,
        "name": item.name,
        "unit": item.unit or "",
        "active": bool(item.active),
        "sort_order": item.sort_order or 0,
        "values": (values_by_item or {}).get(item.id, {}),
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def category_exists(db: Session, category_id: str) -> bool:
    return bool(db.get(models.EmployeeCategory, category_id))


def touch_category_state(
    db: Session,
    category_id: str,
    author: str = "",
    *,
    log_callback: Callable | None = None,
) -> models.InventoryCategoryState:
    state = (
        db.query(models.InventoryCategoryState)
        .filter(models.InventoryCategoryState.category_id == category_id)
        .first()
    )
    if not state:
        state = models.InventoryCategoryState(
            id=category_id,
            category_id=category_id,
        )
        db.add(state)
    author = (author or "").strip()
    if author:
        state.last_author = author[:50]
    state.last_written_at = datetime.utcnow()
    state.updated_at = datetime.utcnow()
    db.flush()
    if log_callback:
        log_callback(db, "inventory_category_state", state.id, "upsert", state)
    return state


def list_inventory(db: Session, active_categories: bool = True) -> dict:
    q = db.query(models.EmployeeCategory)
    if active_categories:
        q = q.filter(models.EmployeeCategory.active == True)  # noqa: E712
    categories = q.order_by(
        models.EmployeeCategory.sort_order,
        models.EmployeeCategory.name,
    ).all()
    category_ids = [c.id for c in categories]

    states = {
        s.category_id: s
        for s in db.query(models.InventoryCategoryState)
        .filter(models.InventoryCategoryState.category_id.in_(category_ids))
        .all()
    } if category_ids else {}
    fields_by_category = {cid: [] for cid in category_ids}
    items_by_category = {cid: [] for cid in category_ids}

    if category_ids:
        fields = (
            db.query(models.InventoryField)
            .filter(
                models.InventoryField.category_id.in_(category_ids),
                models.InventoryField.active == True,  # noqa: E712
            )
            .order_by(models.InventoryField.sort_order, models.InventoryField.name)
            .all()
        )
        for field in fields:
            fields_by_category.setdefault(field.category_id, []).append(field)

        items = (
            db.query(models.InventoryItem)
            .filter(models.InventoryItem.category_id.in_(category_ids))
            .order_by(
                models.InventoryItem.active.desc(),
                models.InventoryItem.sort_order,
                models.InventoryItem.name,
            )
            .all()
        )
        item_ids = [item.id for item in items]
        values_by_item: dict[str, dict[str, str]] = {}
        if item_ids:
            values = (
                db.query(models.InventoryValue)
                .filter(models.InventoryValue.item_id.in_(item_ids))
                .all()
            )
            for val in values:
                values_by_item.setdefault(val.item_id, {})[val.field_id] = val.value or ""
        for item in items:
            items_by_category.setdefault(item.category_id, []).append(
                serialize_item(item, values_by_item)
            )

    return {
        "categories": [
            {
                "category": serialize_category(c),
                "state": serialize_state(states.get(c.id), c.id),
                "fields": [serialize_field(f) for f in fields_by_category.get(c.id, [])],
                "items": items_by_category.get(c.id, []),
            }
            for c in categories
        ],
    }
