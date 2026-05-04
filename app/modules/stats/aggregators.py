"""modules.stats.aggregators — 순수 통계 집계 함수 (19-11 신규).

본 모듈은 ``api.py`` 의 통계 핸들러에 인라인 분산된 *집계 loop* 를 *순수 함수* 로
추출한다. 인자는 *읽기 전용 row 리스트* + manual code 셋 + 옵션. DB / ORM 미참조 —
caller 가 사전 조회 후 주입.

19-11 본 세션 범위:
  - summary 집계 (total / manual / approved / manual_approved / canceled).
  - by-hour 집계 (24 시간대).
  - by-weekday 집계 (7 요일).
  - by-treatment 집계 (코드별).
  - daily 집계 (날짜별 + manual_by_code / manual_approved_by_code).
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:stats_summary`` (line 4019~4033) / ``stats_by_hour`` (line
#         4087~4098) / ``stats_by_weekday`` (line 4136~4147) / ``stats_by_treatment``
#         (line 4190~4200) / ``stats_daily`` (line 4256~4282) loop 와 byte-equivalent.

# SAFETY: 본 모듈 함수는 *순수* — 입력 row 변경 ⊥, DB 변경 ⊥, 외부 호출 ⊥.

# NOTE: caller 가 ``treatment_code`` 매칭 / mode 분류는 ``rules.py`` helper 사용.
#       본 aggregators 는 *집계 loop* 만 담당.

# RISK: 예약 1건 = count 1 정책 *변경 ⊥*. ``MANUAL_COUNT_INCREMENT_PER_APPT`` (1)
#       을 곱셈 가중치 (manual30=1, manual60=2) 로 변경하면 시간 가중치 회귀 — 모든
#       aggregator 가 ``+= 1`` 만 사용 (가드).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.modules.stats import rules as _rules


# ─── summary 집계 (api.py:stats_summary line 4013~4033 정합) ─────────────────


def aggregate_summary(
    *,
    rows: list[Any],
    manual_codes_set: set[str],
    treatment_code: str | None,
    parse_codes: Any,
) -> dict[str, int]:
    """요약 카운트 5종 — total / manual / approved / manual_approved / canceled.

    COMPAT: ``api.py:stats_summary`` (line 4013~4033) 와 byte-equivalent.

    NOTE: ``parse_codes`` 는 ``api.py:_parse_codes`` 정합 — caller 주입 (str → list).

    RISK: 예약 1건 = count 1 정책 — ``+= 1`` 만 사용. 시간 가중치 회귀 ⊥.
    """
    total = 0
    manual = 0
    approved = 0
    manual_approved = 0
    canceled = 0
    # 20-3-1 (post-19-P / F-10): 노쇼 별도 카운트 (cancel 과 분리 — 사용자 §3-7 (ii))
    no_show_count = 0

    for a in rows:
        codes = parse_codes(a.treatment_codes)
        if not _rules.treatment_code_matches(
            codes=codes,
            treatment_code=treatment_code,
            manual_codes_set=manual_codes_set,
        ):
            continue
        total += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
        if a.status == "canceled":
            canceled += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
            # NOTE: 노쇼는 cancel 의 부분집합 (둘 다 카운트)
            if getattr(a, "no_show", False):
                no_show_count += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
        else:
            is_manual = any(c in manual_codes_set for c in codes)
            if is_manual:
                manual += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
            if a.status == "approved":
                approved += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
                if is_manual:
                    manual_approved += _rules.MANUAL_COUNT_INCREMENT_PER_APPT

    return {
        "total": total,
        "manual": manual,
        "approved": approved,
        "manual_approved": manual_approved,
        "canceled": canceled,
        "no_show_count": no_show_count,
    }


# ─── by-hour 집계 (api.py:stats_by_hour line 4087~4098 정합) ─────────────────


def aggregate_by_hour(
    *,
    rows: list[Any],
    manual_codes_set: set[str],
    treatment_code: str | None,
    mode: str | None,
    parse_codes: Any,
) -> dict[int, int]:
    """0~23시 별 카운트.

    COMPAT: ``api.py:stats_by_hour`` (line 4087~4098) 와 byte-equivalent.

    RISK: 예약 1건 = count 1 — 시간 가중치 ⊥.
    """
    counts: dict[int, int] = defaultdict(int)
    for a in rows:
        codes = parse_codes(a.treatment_codes)
        if not _rules.treatment_code_matches(
            codes=codes,
            treatment_code=treatment_code,
            manual_codes_set=manual_codes_set,
        ):
            continue
        if not _rules.is_counted_for_mode(status=a.status, mode=mode):
            continue
        counts[a.start_at.hour] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
    return dict(counts)


# ─── by-weekday 집계 (api.py:stats_by_weekday line 4136~4147 정합) ───────────


def aggregate_by_weekday(
    *,
    rows: list[Any],
    manual_codes_set: set[str],
    treatment_code: str | None,
    mode: str | None,
    parse_codes: Any,
) -> dict[int, int]:
    """0~6 weekday 별 카운트.

    COMPAT: ``api.py:stats_by_weekday`` (line 4136~4147) 와 byte-equivalent.

    RISK: 예약 1건 = count 1.
    """
    counts: dict[int, int] = defaultdict(int)
    for a in rows:
        codes = parse_codes(a.treatment_codes)
        if not _rules.treatment_code_matches(
            codes=codes,
            treatment_code=treatment_code,
            manual_codes_set=manual_codes_set,
        ):
            continue
        if not _rules.is_counted_for_mode(status=a.status, mode=mode):
            continue
        counts[a.start_at.weekday()] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
    return dict(counts)


# ─── by-treatment 집계 (api.py:stats_by_treatment line 4190~4200 정합) ──────


def aggregate_by_treatment(
    *,
    rows: list[Any],
    manual_codes_set: set[str],
    treatment_code: str | None,
    mode: str | None,
    parse_codes: Any,
) -> dict[str, int]:
    """치료항목 코드별 카운트.

    COMPAT: ``api.py:stats_by_treatment`` (line 4190~4200) 와 byte-equivalent.

    NOTE: by-treatment 는 mode 분기가 *약간 다름* — ``mode="all"`` 분기 ⊥.
    ``rules.is_counted_for_treatment_mode`` 가 그 정합 정합.

    RISK: 예약 1건 = count 1. 한 예약에 여러 코드가 있으면 *각 코드마다 1씩* 증분
    (api.py 정합 — 합산 가중치 ⊥).
    """
    counts: dict[str, int] = defaultdict(int)
    for a in rows:
        if not _rules.is_counted_for_treatment_mode(status=a.status, mode=mode):
            continue
        codes = parse_codes(a.treatment_codes)
        if not _rules.treatment_code_matches(
            codes=codes,
            treatment_code=treatment_code,
            manual_codes_set=manual_codes_set,
        ):
            continue
        for c in codes:
            counts[c] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
    return dict(counts)


# ─── daily 집계 (api.py:stats_daily line 4256~4282 정합) ────────────────────


def aggregate_daily(
    *,
    rows: list[Any],
    date_keys: list[str],
    manual_codes: list[str],
    manual_codes_set: set[str],
    treatment_code: str | None,
    parse_codes: Any,
    eswt_code: str = "eswt",
) -> dict[str, dict[str, Any]]:
    """날짜별 8키 dict — total / approved / manual / manual_approved / eswt /
    canceled / manual_by_code / manual_approved_by_code.

    COMPAT: ``api.py:stats_daily`` (line 4247~4282) 와 byte-equivalent.

    인자:
      ``date_keys`` : ``["YYYY-MM-DD", ...]`` (caller 가 ``date_list`` 로 빌드).
      ``manual_codes`` : 정렬된 manual 코드 리스트 (sort_order 순).
      ``manual_codes_set`` : 같은 코드의 set (매칭 효율).
      ``eswt_code`` : 체외충격파 코드 (기본 ``"eswt"``).

    RISK: 예약 1건 = count 1.
    """
    daily: dict[str, dict[str, Any]] = {
        dk: {
            "total": 0,
            "approved": 0,
            "manual": 0,
            "manual_approved": 0,
            "eswt": 0,
            "canceled": 0,
            "manual_by_code": {code: 0 for code in manual_codes},
            "manual_approved_by_code": {code: 0 for code in manual_codes},
        }
        for dk in date_keys
    }

    for a in rows:
        codes = parse_codes(a.treatment_codes)
        if not _rules.treatment_code_matches(
            codes=codes,
            treatment_code=treatment_code,
            manual_codes_set=manual_codes_set,
        ):
            continue
        dk = a.start_at.strftime("%Y-%m-%d")
        if dk not in daily:
            continue  # 안전 가드 (이론상 필터 이미 걸림).
        daily[dk]["total"] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
        if a.status == "canceled":
            daily[dk]["canceled"] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
        else:
            is_manual = any(c in manual_codes_set for c in codes)
            is_eswt = eswt_code in codes
            if is_manual:
                daily[dk]["manual"] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
                for c in codes:
                    if c in manual_codes_set:
                        daily[dk]["manual_by_code"][c] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
            if is_eswt:
                daily[dk]["eswt"] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
            if a.status == "approved":
                daily[dk]["approved"] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
                if is_manual:
                    daily[dk]["manual_approved"] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT
                    for c in codes:
                        if c in manual_codes_set:
                            daily[dk]["manual_approved_by_code"][c] += _rules.MANUAL_COUNT_INCREMENT_PER_APPT

    return daily


__all__ = [
    "aggregate_summary",
    "aggregate_by_hour",
    "aggregate_by_weekday",
    "aggregate_by_treatment",
    "aggregate_daily",
]
