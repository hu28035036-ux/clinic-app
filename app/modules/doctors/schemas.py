"""modules.doctors.schemas — Doctor 응답 스키마 (post-19-P / 20-3-3)."""
from __future__ import annotations

from typing import Final, Optional

from pydantic import BaseModel


class DoctorIn(BaseModel):
    """의사 생성 / 수정 입력."""
    name: str
    specialty: Optional[str] = None
    license_no: Optional[str] = None
    color: str = "#9CA3AF"
    active: bool = True
    sort_order: int = 0


# 응답 dict 8키 (id / name / specialty / license_no / color / active / sort_order /
# created_at) — UI 가 의존. 키 추가 시 contract 테스트 갱신 필요.
DOCTOR_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "name",
        "specialty",
        "license_no",
        "color",
        "active",
        "sort_order",
        "created_at",
    }
)


__all__ = ["DOCTOR_RESPONSE_KEYS", "DoctorIn"]
