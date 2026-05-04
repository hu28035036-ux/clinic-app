"""modules.appointment_series.schemas — 반복 예약 응답 스키마 (post-19-P / 20-3-4)."""
from __future__ import annotations

from datetime import datetime
from typing import Final, Optional

from pydantic import BaseModel, Field


class AppointmentSeriesIn(BaseModel):
    """반복 예약 등록 입력 (사용자 §6-6 (a) N회만 패턴).

    NOTE: 본 v1 = N회 단순 반복. (b) 주간/격주/월간 / (c) 모두 후속.
    """
    patient_id: str
    therapist_id: Optional[str] = None
    start_at: datetime
    duration_min: int = 30
    interval_days: int = Field(ge=1, description="반복 간격 (일 단위, 최소 1)")
    count: int = Field(ge=2, le=52, description="총 회차 (2~52, 가용 범위 제한)")
    treatment_codes: list[str]
    memo: str = ""
    # 20-3-5 (post-19-P / F-3): 자원 (치료실) — 시리즈 전체에 같은 자원 사용
    resource_id: Optional[str] = None


# 시리즈 응답 dict 7키 (id / patient_id / therapist_id / pattern / pattern_data /
# start_date / treatment_codes).
APPOINTMENT_SERIES_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "patient_id",
        "therapist_id",
        "pattern",
        "pattern_data",
        "start_date",
        "treatment_codes",
    }
)

# POST /api/appointment-series 응답 = 시리즈 dict + created (성공 슬롯 ID 리스트)
# + conflicts (skip 된 슬롯 정보).
SERIES_CREATE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"series", "created", "conflicts"}
)

# 충돌 정보 dict 키.
CONFLICT_INFO_KEYS: Final[frozenset[str]] = frozenset(
    {"start_at", "reason"}
)


__all__ = [
    "APPOINTMENT_SERIES_RESPONSE_KEYS",
    "AppointmentSeriesIn",
    "CONFLICT_INFO_KEYS",
    "SERIES_CREATE_RESPONSE_KEYS",
]
