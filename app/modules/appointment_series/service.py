"""modules.appointment_series.service — 반복 예약 서비스 (post-19-P / 20-3-4 / F-2).

# NOTE: 본 v1 = (a) N회만, (i) 미래만 일괄 처리, (ii) 충돌 skip + 응답 안내.
# 충돌 검사는 기존 _check_lunch_block (점심창) 만 — 도수 중복 / 휴무 차단은
# 19-4 백엔드 검증이 자동 적용.

# SAFETY: 운영 DB 접근 / 외부 API / 실제 문자 발송 ⊥. 응답 dict 에 환자 PII
# 평문 부재 (시리즈 ID / 슬롯 ID / start_at 만).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any


def serialize_series(series: Any) -> dict[str, Any]:
    """AppointmentSeries ORM → 7키 응답 dict."""
    return {
        "id": series.id,
        "patient_id": series.patient_id,
        "therapist_id": series.therapist_id,
        "pattern": series.pattern,
        "pattern_data": series.pattern_data,
        "start_date": (
            series.start_date.isoformat() if series.start_date else None
        ),
        "treatment_codes": (
            json.loads(series.treatment_codes) if series.treatment_codes else []
        ),
    }


def compute_slot_starts(
    *,
    start_at: datetime,
    interval_days: int,
    count: int,
) -> list[datetime]:
    """N회 반복 패턴의 슬롯 시작 시각 리스트.

    NOTE: 사용자 §6-6 (a) — interval_days + count 만. (b) 요일 패턴은 후속.
    """
    return [start_at + timedelta(days=i * interval_days) for i in range(count)]


__all__ = ["compute_slot_starts", "serialize_series"]
