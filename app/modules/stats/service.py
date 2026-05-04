"""modules.stats.service — 통계 응답 dict 빌더 + 기간 해석기 (19-11 신규).

본 모듈은 ``api.py`` 의 통계 핸들러 응답 dict 의 *byte-equivalent* 빌더와
공용 기간 해석기 (``_resolve_stats_range`` / ``_date_list``) 를 제공한다.
라우터 무수정.

19-11 본 세션 범위:
  - ``resolve_stats_range`` (== ``_resolve_stats_range``).
  - ``date_list`` (== ``_date_list``).
  - 응답 dict 빌더 (summary / by-hour / by-weekday / by-treatment / daily).
  - 라우터 미채택 (라우터 본체 무수정).

# COMPAT: ``api.py:_resolve_stats_range`` (line 3944~3968) / ``_date_list``
#         (line 3971~3978) / ``stats_summary`` 응답 (line 4038~4053) /
#         ``stats_by_hour`` 응답 (line 4100~4102) / ``stats_by_weekday`` 응답
#         (line 4150~4155) / ``stats_by_treatment`` 응답 (line 4202~4210) /
#         ``stats_daily`` 응답 (line 4286~4310) 과 byte-equivalent.

# SAFETY: 본 helper 는 *기존 응답 그대로* — UI / 차트 / 표 모두 의존. 본 19-11
#         이 응답 키 / 타입 변경 ⊥.

# RISK: 응답 dict 키 변경 ⊥ — UI / SMS / AI 의존. ``schemas.py`` contract +
#       19-11 contract 테스트가 회귀 검출.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


# ─── 공용 기간 해석기 (api.py:_resolve_stats_range 정합) ─────────────────────


class StatsRangeError(ValueError):
    """기간 입력이 잘못된 경우 — 라우터가 ``HTTPException(400)`` 으로 변환.

    NOTE: 본 helper 는 ``HTTPException`` 미참조 (FastAPI 미사용). 라우터 채택
    시점에 변환 책임. 19-11 시점에는 라우터 본체가 그대로 ``HTTPException`` 사용.
    """


def resolve_stats_range(
    *,
    year: int | None,
    month: int | None,
    date_from: str | None,
    date_to: str | None,
) -> tuple[datetime, datetime, str]:
    """입력을 ``(ts, te, label)`` 로 변환.

    COMPAT: ``api.py:_resolve_stats_range`` (line 3944~3968) 와 byte-equivalent.

    우선순위:
      1) ``date_from`` / ``date_to`` 둘 다 있으면 사용 (label = ``"YYYY-MM-DD~YYYY-MM-DD"``).
      2) ``year`` / ``month`` (label = ``"YYYY-MM"``).
      3) 현재 월 (label = ``"YYYY-MM"``).

    raise:
      ``StatsRangeError`` — 형식 오류 / ``date_to < date_from``.
    """
    if date_from and date_to:
        try:
            ts = datetime.strptime(date_from, "%Y-%m-%d")
            te_inc = datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError as exc:
            raise StatsRangeError(
                "date_from / date_to 는 'YYYY-MM-DD' 형식이어야 합니다."
            ) from exc
        if te_inc < ts:
            raise StatsRangeError("date_to 는 date_from 이후여야 합니다.")
        return ts, te_inc + timedelta(days=1), f"{date_from}~{date_to}"

    if year and month:
        ts = datetime(year, month, 1)
        te = datetime(
            year + (1 if month == 12 else 0),
            (1 if month == 12 else month + 1),
            1,
        )
        return ts, te, f"{year:04d}-{month:02d}"

    now = datetime.now()
    ts = datetime(now.year, now.month, 1)
    te = datetime(
        now.year + (1 if now.month == 12 else 0),
        (1 if now.month == 12 else now.month + 1),
        1,
    )
    return ts, te, f"{now.year:04d}-{now.month:02d}"


def date_list(start: datetime, end: datetime) -> list[str]:
    """``[start, end)`` 기간의 ``"YYYY-MM-DD"`` 문자열 리스트.

    COMPAT: ``api.py:_date_list`` (line 3971~3978) 와 byte-equivalent.
    """
    out: list[str] = []
    cur = start
    while cur < end:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out


# ─── summary 응답 빌더 (api.py:stats_summary line 4038~4053 정합) ────────────


def build_summary_response(
    *,
    ts: datetime,
    te: datetime,
    range_label: str,
    counts: dict[str, int],
    treatment_code: str | None,
) -> dict[str, Any]:
    """``stats_summary`` 응답 dict — 12키.

    COMPAT: ``api.py:stats_summary`` (line 4038~4053) 와 byte-equivalent.

    NOTE: ``year`` / ``month`` 는 ``ts.year`` / ``ts.month`` (구 필드 호환).
    ``date_from`` / ``date_to`` / ``range_label`` 는 v1.2.9+ 신 필드.

    RISK: 12키 변경 ⊥ — UI 가 의존.
    """
    days = (te - ts).days
    return {
        "year": ts.year,
        "month": ts.month,
        "date_from": ts.strftime("%Y-%m-%d"),
        "date_to": (te - timedelta(days=1)).strftime("%Y-%m-%d"),
        "range_label": range_label,
        "days": days,
        "total": counts.get("total", 0),
        "manual": counts.get("manual", 0),
        "approved": counts.get("approved", 0),
        "manual_approved": counts.get("manual_approved", 0),
        "canceled": counts.get("canceled", 0),
        "treatment_code": treatment_code or "",
    }


# ─── by-hour 응답 빌더 (api.py:stats_by_hour line 4100~4102 정합) ───────────


def build_by_hour_response(
    *,
    year: int,
    month: int,
    counts: dict[int, int],
) -> dict[str, Any]:
    """``stats_by_hour`` 응답 dict — 3키 (year / month / items).

    COMPAT: ``api.py:stats_by_hour`` (line 4100~4102) 와 byte-equivalent.
    items = 24개 항목 (hour / label / count).
    """
    items = [
        {"hour": h, "label": f"{h:02d}시", "count": counts.get(h, 0)}
        for h in range(24)
    ]
    return {"year": year, "month": month, "items": items}


# ─── by-weekday 응답 빌더 (api.py:stats_by_weekday line 4150~4155 정합) ─────


def build_by_weekday_response(
    *,
    year: int,
    month: int,
    counts: dict[int, int],
) -> dict[str, Any]:
    """``stats_by_weekday`` 응답 dict — 3키. items = 7 요일 (월~일).

    COMPAT: ``api.py:stats_by_weekday`` (line 4150~4155) 와 byte-equivalent.
    """
    from app.modules.stats import rules as _rules

    items = [
        {
            "weekday": i,
            "label": _rules.weekday_label(i),
            "count": counts.get(i, 0),
        }
        for i in range(7)
    ]
    return {"year": year, "month": month, "items": items}


# ─── by-treatment 응답 빌더 (api.py:stats_by_treatment line 4202~4210 정합) ─


def build_by_treatment_response(
    *,
    year: int,
    month: int,
    counts: dict[str, int],
    tx_name_map: dict[str, str],
) -> dict[str, Any]:
    """``stats_by_treatment`` 응답 dict — 3키.

    COMPAT: ``api.py:stats_by_treatment`` (line 4202~4210) 와 byte-equivalent.
    items = 코드별 항목, ``-count`` (내림차순) 정렬.
    """
    items = sorted(
        [
            {"code": code, "label": tx_name_map.get(code, code), "count": cnt}
            for code, cnt in counts.items()
        ],
        key=lambda x: -x["count"],
    )
    return {"year": year, "month": month, "items": items}


# ─── daily 응답 빌더 (api.py:stats_daily line 4286~4310 정합) ───────────────


def build_daily_response(
    *,
    ts: datetime,
    te: datetime,
    range_label: str,
    date_keys: list[str],
    daily_counts: dict[str, dict[str, Any]],
    manual_codes: list[str],
    manual_names: dict[str, str],
    treatment_code: str | None,
) -> dict[str, Any]:
    """``stats_daily`` 응답 dict.

    COMPAT: ``api.py:stats_daily`` (line 4286~4310) 와 byte-equivalent.
    items = 날짜별 항목 (10키).
    """
    items = [
        {
            "date": dk,
            "day": int(dk[8:10]),
            "total": daily_counts[dk]["total"],
            "approved": daily_counts[dk]["approved"],
            "manual": daily_counts[dk]["manual"],
            "manual_approved": daily_counts[dk]["manual_approved"],
            "eswt": daily_counts[dk]["eswt"],
            "canceled": daily_counts[dk]["canceled"],
            "manual_by_code": daily_counts[dk]["manual_by_code"],
            "manual_approved_by_code": daily_counts[dk]["manual_approved_by_code"],
        }
        for dk in date_keys
    ]

    return {
        "year": ts.year,
        "month": ts.month,
        "date_from": ts.strftime("%Y-%m-%d"),
        "date_to": (te - timedelta(days=1)).strftime("%Y-%m-%d"),
        "range_label": range_label,
        "days": len(date_keys),
        "items": items,
        "manual_codes": manual_codes,
        "manual_names": manual_names,
        "treatment_code": treatment_code or "",
    }


__all__ = [
    "StatsRangeError",
    "resolve_stats_range",
    "date_list",
    "build_summary_response",
    "build_by_hour_response",
    "build_by_weekday_response",
    "build_by_treatment_response",
    "build_daily_response",
]
