"""modules.appointment_series — 반복 예약 시리즈 (post-19-P / 20-3-4 / F-2).

사용자 §6-6 결정 정합:
  - (a) N회만 (interval_days + count)
  - (i) 미래만 일괄 처리
  - (ii) 충돌 슬롯 skip + 응답 안내
"""

from app.modules.appointment_series.router import router
from app.modules.appointment_series.schemas import (
    APPOINTMENT_SERIES_RESPONSE_KEYS,
    AppointmentSeriesIn,
)
from app.modules.appointment_series.service import serialize_series

__all__ = [
    "APPOINTMENT_SERIES_RESPONSE_KEYS",
    "AppointmentSeriesIn",
    "router",
    "serialize_series",
]
