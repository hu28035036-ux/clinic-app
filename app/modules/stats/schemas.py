"""modules.stats.schemas — 통계 API 응답 키 contract 상수 (19-11 신규).

본 모듈은 ``api.py`` 의 모든 통계 핸들러 응답 dict 의 *키 셋* 을 contract 상수로
명시한다. UI / 차트 / 표 / SMS / AI 가 의존하는 응답 키를 *임의 변경 ⊥* —
contract 테스트가 회귀 검출.

19-11 본 세션 범위:
  - 응답 키 셋 상수 (frozenset).
  - Pydantic 모델 정의 ⊥.
  - 라우터 무수정.

# COMPAT: 본 contract 상수와 ``api.py`` 응답 dict 의 키 셋이 *byte-equivalent*.
#         contract 변경 ⊥.

# SAFETY: 본 모듈은 *상수 정의* 만 — 동작 변경 ⊥.

# RISK: 응답 키 *제거* / *이름 변경* 은 ``AI_WORKING_RULES.md`` §1.7 정합 — 별도
#       합의 필수. 시간 가중치 회귀 방지를 위해 ``MANUAL_COUNT_INCREMENT_PER_APPT``
#       정책은 ``rules.py`` 에 별도 명시.
"""
from __future__ import annotations

from typing import Final


# ─── /stats/summary 응답 (api.py line 4038~4053) ─────────────────────────────


SUMMARY_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "year",
        "month",
        "date_from",
        "date_to",
        "range_label",
        "days",
        "total",
        "manual",
        "approved",
        "manual_approved",
        "canceled",
        # 20-3-1 (post-19-P / F-10): 노쇼 별도 카운트
        "no_show_count",
        "treatment_code",
    }
)


# ─── /stats/by-hour 응답 (api.py line 4100~4102) ─────────────────────────────


BY_HOUR_RESPONSE_KEYS: Final[frozenset[str]] = frozenset({"year", "month", "items"})

BY_HOUR_ITEM_KEYS: Final[frozenset[str]] = frozenset({"hour", "label", "count"})


# ─── /stats/by-weekday 응답 (api.py line 4150~4155) ──────────────────────────


BY_WEEKDAY_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"year", "month", "items"}
)

BY_WEEKDAY_ITEM_KEYS: Final[frozenset[str]] = frozenset({"weekday", "label", "count"})


# ─── /stats/by-treatment 응답 (api.py line 4202~4210) ────────────────────────


BY_TREATMENT_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"year", "month", "items"}
)

BY_TREATMENT_ITEM_KEYS: Final[frozenset[str]] = frozenset({"code", "label", "count"})


# ─── /stats/daily 응답 (api.py line 4302~4310) ───────────────────────────────


DAILY_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "year",
        "month",
        "date_from",
        "date_to",
        "range_label",
        "days",
        "items",
        "manual_codes",
        "manual_names",
        "treatment_code",
    }
)

DAILY_ITEM_KEYS: Final[frozenset[str]] = frozenset(
    {
        "date",
        "day",
        "total",
        "approved",
        "manual",
        "manual_approved",
        "eswt",
        "canceled",
        "manual_by_code",
        "manual_approved_by_code",
    }
)


# ─── /stats/aggregate 응답 (api.py line 3723~3729) ───────────────────────────


AGGREGATE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"year", "month", "manual_codes", "manual_names", "eswt_name", "items"}
)

AGGREGATE_ITEM_KEYS: Final[frozenset[str]] = frozenset(
    {
        "therapist_id",
        "therapist_name",
        "manual_breakdown",
        "new_patient_count",
        "eswt_count",
    }
)


# ─── /stats/by-therapist 응답 (api.py line 3553~3556) ────────────────────────


BY_THERAPIST_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"year", "month", "days", "items", "manual_codes", "manual_names"}
)

BY_THERAPIST_ITEM_KEYS: Final[frozenset[str]] = frozenset(
    {
        "therapist_id",
        "therapist_name",
        "total",
        "avg_per_day",
        "max_per_day",
        "min_per_day",
        "canceled",
        "daily",
        "manual_breakdown",
    }
)


# ─── /stats/manual-by-therapist 응답 (api.py line 3623~3640) ─────────────────


# (라우터 본체 미상세 검증 — 본 19-11 시점에는 시그니처 무수정만 검증.
#  contract 상수는 19-12+ 채택 시점에 추가 후보.)


__all__ = [
    "SUMMARY_RESPONSE_KEYS",
    "BY_HOUR_RESPONSE_KEYS",
    "BY_HOUR_ITEM_KEYS",
    "BY_WEEKDAY_RESPONSE_KEYS",
    "BY_WEEKDAY_ITEM_KEYS",
    "BY_TREATMENT_RESPONSE_KEYS",
    "BY_TREATMENT_ITEM_KEYS",
    "DAILY_RESPONSE_KEYS",
    "DAILY_ITEM_KEYS",
    "AGGREGATE_RESPONSE_KEYS",
    "AGGREGATE_ITEM_KEYS",
    "BY_THERAPIST_RESPONSE_KEYS",
    "BY_THERAPIST_ITEM_KEYS",
]
