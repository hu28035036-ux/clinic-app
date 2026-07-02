from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.services import auth
from . import service
from .schemas import (
    InventoryCategoryStateIn,
    InventoryFieldIn,
    InventoryItemIn,
    InventoryValueIn,
)
from app.routers.api import _log, audit, require_admin

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _require_category(db: Session, category_id: str) -> models.EmployeeCategory:
    category = db.get(models.EmployeeCategory, category_id)
    if not category:
        raise HTTPException(404, "과를 찾을 수 없습니다.")
    return category


@router.get("")
def get_inventory(
    active_categories: bool = True,
    x_admin_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    return service.list_inventory(
        db,
        active_categories=active_categories,
        include_admin=auth.is_valid(x_admin_token),
    )


@router.post("/category-state")
def save_category_state(
    p: InventoryCategoryStateIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    _require_category(db, p.category_id)
    state = service.touch_category_state(
        db,
        p.category_id,
        p.last_author,
        log_callback=_log,
    )
    # Explicit author save may intentionally clear the displayed author.
    state.last_author = (p.last_author or "").strip()[:50]
    db.flush()
    _log(db, "inventory_category_state", state.id, "upsert", state)
    audit(db, "inventory.category_state.update", state.id, f"category_id={p.category_id}")
    db.commit()
    db.refresh(state)
    return service.serialize_state(state, p.category_id)


@router.post("/items")
def create_item(
    p: InventoryItemIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    _require_category(db, p.category_id)
    name = (p.name or "").strip()
    if not name:
        raise HTTPException(400, "품목명을 입력하세요.")
    item = models.InventoryItem(
        category_id=p.category_id,
        name=name,
        unit=(p.unit or "").strip()[:30],
        active=bool(p.active),
        sort_order=p.sort_order or (
            db.query(models.InventoryItem)
            .filter(models.InventoryItem.category_id == p.category_id)
            .count() + 1
        ),
    )
    db.add(item)
    db.flush()
    _log(db, "inventory_item", item.id, "upsert", item)
    service.touch_category_state(db, p.category_id, p.author, log_callback=_log)
    audit(db, "inventory.item.create", item.id, f"name={item.name}")
    db.commit()
    db.refresh(item)
    return service.serialize_item(item, {})


@router.put("/items/{item_id}")
def update_item(
    item_id: str,
    p: InventoryItemIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    item = db.get(models.InventoryItem, item_id)
    if not item:
        raise HTTPException(404, "품목을 찾을 수 없습니다.")
    _require_category(db, p.category_id)
    name = (p.name or "").strip()
    if not name:
        raise HTTPException(400, "품목명을 입력하세요.")
    item.category_id = p.category_id
    item.name = name
    item.unit = (p.unit or "").strip()[:30]
    item.active = bool(p.active)
    item.sort_order = p.sort_order or item.sort_order or 0
    db.flush()
    _log(db, "inventory_item", item.id, "upsert", item)
    service.touch_category_state(db, item.category_id, p.author, log_callback=_log)
    audit(db, "inventory.item.update", item.id, f"name={item.name}")
    db.commit()
    db.refresh(item)
    return service.serialize_item(item, {})


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    author: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    item = db.get(models.InventoryItem, item_id)
    if not item:
        raise HTTPException(404, "품목을 찾을 수 없습니다.")
    category_id = item.category_id
    name = item.name
    db.query(models.InventoryValue).filter(models.InventoryValue.item_id == item_id).delete()
    db.delete(item)
    _log(db, "inventory_item", item_id, "delete", None)
    service.touch_category_state(db, category_id, author, log_callback=_log)
    audit(db, "inventory.item.delete", item_id, f"name={name}")
    db.commit()
    return {"ok": True}


@router.post("/fields")
def create_field(
    p: InventoryFieldIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    _require_category(db, p.category_id)
    name = (p.name or "").strip()
    if not name:
        raise HTTPException(400, "관리 열 이름을 입력하세요.")
    field = models.InventoryField(
        category_id=p.category_id,
        name=name,
        field_type=p.field_type or "text",
        admin_only=bool(p.admin_only),
        active=bool(p.active),
        sort_order=p.sort_order or (
            db.query(models.InventoryField)
            .filter(models.InventoryField.category_id == p.category_id)
            .count() + 1
        ),
    )
    db.add(field)
    db.flush()
    _log(db, "inventory_field", field.id, "upsert", field)
    service.touch_category_state(db, p.category_id, p.author, log_callback=_log)
    audit(db, "inventory.field.create", field.id, f"name={field.name}")
    db.commit()
    db.refresh(field)
    return service.serialize_field(field)


@router.put("/fields/{field_id}")
def update_field(
    field_id: str,
    p: InventoryFieldIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    field = db.get(models.InventoryField, field_id)
    if not field:
        raise HTTPException(404, "관리 열을 찾을 수 없습니다.")
    _require_category(db, p.category_id)
    name = (p.name or "").strip()
    if not name:
        raise HTTPException(400, "관리 열 이름을 입력하세요.")
    field.category_id = p.category_id
    field.name = name
    field.field_type = p.field_type or "text"
    field.admin_only = bool(p.admin_only)
    field.active = bool(p.active)
    field.sort_order = p.sort_order or field.sort_order or 0
    db.flush()
    _log(db, "inventory_field", field.id, "upsert", field)
    service.touch_category_state(db, field.category_id, p.author, log_callback=_log)
    audit(db, "inventory.field.update", field.id, f"name={field.name}")
    db.commit()
    db.refresh(field)
    return service.serialize_field(field)


@router.delete("/fields/{field_id}")
def delete_field(
    field_id: str,
    author: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    field = db.get(models.InventoryField, field_id)
    if not field:
        raise HTTPException(404, "관리 열을 찾을 수 없습니다.")
    category_id = field.category_id
    name = field.name
    db.query(models.InventoryValue).filter(models.InventoryValue.field_id == field_id).delete()
    db.delete(field)
    _log(db, "inventory_field", field_id, "delete", None)
    service.touch_category_state(db, category_id, author, log_callback=_log)
    audit(db, "inventory.field.delete", field_id, f"name={name}")
    db.commit()
    return {"ok": True}


@router.post("/values")
def upsert_value(
    p: InventoryValueIn,
    x_admin_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    item = db.get(models.InventoryItem, p.item_id)
    if not item:
        raise HTTPException(404, "품목을 찾을 수 없습니다.")
    field = db.get(models.InventoryField, p.field_id)
    if not field:
        raise HTTPException(404, "관리 열을 찾을 수 없습니다.")
    if item.category_id != field.category_id:
        raise HTTPException(400, "품목과 관리 열의 과가 다릅니다.")
    # 관리자 전용 칸은 관리자 인증 시에만 입력 가능 (일반 칸은 직원도 입력).
    if bool(field.admin_only) and not auth.is_valid(x_admin_token):
        raise HTTPException(401, "관리자 전용 칸은 관리자만 입력할 수 있습니다.")
    value = (
        db.query(models.InventoryValue)
        .filter(
            models.InventoryValue.item_id == item.id,
            models.InventoryValue.field_id == field.id,
        )
        .first()
    )
    if not value:
        value = models.InventoryValue(item_id=item.id, field_id=field.id)
        db.add(value)
    value.value = p.value or ""
    db.flush()
    _log(db, "inventory_value", value.id, "upsert", value)
    service.touch_category_state(db, item.category_id, p.author, log_callback=_log)
    audit(db, "inventory.value.upsert", value.id, f"item={item.name} field={field.name}")
    db.commit()
    db.refresh(value)
    return {
        "id": value.id,
        "item_id": value.item_id,
        "field_id": value.field_id,
        "value": value.value,
    }
