"""modules.resources.schemas — Resource 응답 스키마 (post-19-P / 20-3-5)."""
from __future__ import annotations

from typing import Final

from pydantic import BaseModel, Field


class ResourceIn(BaseModel):
    """자원 생성 / 수정 입력.

    # NOTE: 사용자 §7-7 (a) 권장 = v1 type='room' 만. 'equipment' 후속 확장.
    """
    type: str = Field(default="room", pattern="^(room|equipment)$")
    name: str
    capacity: int = Field(default=1, ge=1, description="capacity > 1 은 후속 확장")
    active: bool = True
    sort_order: int = 0


# Resource 응답 dict 7키
RESOURCE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "type",
        "name",
        "capacity",
        "active",
        "sort_order",
        "created_at",
    }
)


__all__ = ["RESOURCE_RESPONSE_KEYS", "ResourceIn"]
