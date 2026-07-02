from __future__ import annotations

from pydantic import BaseModel, Field


class InventoryItemIn(BaseModel):
    category_id: str
    name: str
    unit: str = ""
    active: bool = True
    sort_order: int = 0
    author: str = ""


class InventoryFieldIn(BaseModel):
    category_id: str
    name: str
    field_type: str = Field(default="text", pattern="^(text|number|date)$")
    admin_only: bool = False
    sort_order: int = 0
    active: bool = True
    author: str = ""


class InventoryValueIn(BaseModel):
    item_id: str
    field_id: str
    value: str = ""
    author: str = ""


class InventoryCategoryStateIn(BaseModel):
    category_id: str
    last_author: str = ""
