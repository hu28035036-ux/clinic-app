"""19-11 stats 통계 집계 분리 contract.

검증 범위 (19-11 세션 지시문 정합):
  1. ``rules`` 의 매칭 / mode 분기 / weekday 라벨 / 카운트 정책 상수가 ``api.py``
     인라인 lambda / 분기와 byte-equivalent.
  2. **``MANUAL_COUNT_INCREMENT_PER_APPT == 1``** *시간 가중치 회귀 방지 가드*.
  3. ``repository`` read-only helper 가 ``api.py`` query 패턴과 동등 (DB 격리 fixture).
  4. ``aggregators`` 의 모든 집계 함수가 라우터 인라인 loop 와 byte-equivalent.
  5. ``service`` 의 응답 dict 빌더가 ``api.py`` 응답과 동일.
  6. ``service.resolve_stats_range`` / ``date_list`` 가 ``api.py`` 의 동등 helper 와
     byte-equivalent.
  7. ``schemas.*`` contract 상수가 실제 라우터 응답 dict 의 키 셋과 일치.
  8. modules.stats 가 ``app.routers`` 미참조 — 단방향 경계 (D-4).
  9. 라우터 통계 핸들러 시그니처 무수정.
 10. 기존 통계 / 예약 / 문자 / 휴무 / 치료항목 흐름 영향 없음.
 11. stats 모듈이 DB / 환자 / 치료사 / 휴무 / 문자 상태 변경 ⊥ (read-only 검증).
"""
from __future__ import annotations

import inspect
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.modules.stats import aggregators as _agg
from app.modules.stats import repository as _repo
from app.modules.stats import rules as _rules
from app.modules.stats import schemas as _schemas
from app.modules.stats import service as _service

# ──────────────────────── 1. 카운트 정책 상수 (시간 가중치 회귀 방지) ─────────


def test_manual_count_increment_per_appt_is_one():
    """RISK: ``manual30=1, manual60=2`` 같은 시간 가중치 방식으로 *되돌아가지 ⊥*.

    CLAUDE.md "manual60 = 1카운트 정책" 정합. 변경 시 환자 표시 / SMS 본문 / 통계
    모두 위반.
    """
    assert _rules.MANUAL_COUNT_INCREMENT_PER_APPT == 1
    assert _rules.TIME_WEIGHTED_COUNT_DENIED is True


def test_aggregators_use_only_unit_increment():
    """RISK: 모든 aggregator 가 ``+= 1`` (또는 ``MANUAL_COUNT_INCREMENT_PER_APPT``)
    만 사용. 시간 가중치 (``+= 2`` / 곱셈 가중치) 회귀 ⊥."""
    src = Path(_agg.__file__).read_text(encoding="utf-8")
    # 시간 가중치 회귀 방지 — 명시적 ``+= 2`` / ``* 2`` 패턴 부재.
    forbidden_patterns = ["+= 2", "* 2", "*= 2"]
    for pat in forbidden_patterns:
        assert pat not in src, f"aggregators 에 시간 가중치 패턴 발견: {pat}"


# ──────────────────────── 2. mode / treatment_code 매칭 byte-equivalent ────


@pytest.mark.parametrize(
    "treatment_code,codes,manual_set,expected",
    [
        # 빈 / "all" → 항상 True.
        ("", ["manual30"], {"manual30"}, True),
        (None, [], {"manual30"}, True),
        ("all", ["eswt"], {"manual30"}, True),
        # "manual_all" → manual codes 안에 하나라도 있으면 True.
        ("manual_all", ["manual30", "eswt"], {"manual30", "manual60"}, True),
        ("manual_all", ["eswt"], {"manual30"}, False),
        ("manual_all", [], {"manual30"}, False),
        # 특정 코드 → 그 코드가 codes 에 있으면 True.
        ("manual30", ["manual30"], {"manual30"}, True),
        ("manual30", ["manual60"], {"manual30", "manual60"}, False),
        ("eswt", ["eswt"], set(), True),
    ],
)
def test_treatment_code_matches_byte_equivalent(treatment_code, codes, manual_set, expected):
    """COMPAT: ``api.py`` 모든 통계 핸들러의 ``_matches`` lambda 정합."""
    assert _rules.treatment_code_matches(
        codes=codes, treatment_code=treatment_code, manual_codes_set=manual_set,
    ) is expected


@pytest.mark.parametrize(
    "status,mode,expected",
    [
        # mode="all" → 항상 True.
        ("reserved", "all", True),
        ("approved", "all", True),
        ("canceled", "all", True),
        # mode="approved" → approved 만.
        ("reserved", "approved", False),
        ("approved", "approved", True),
        ("canceled", "approved", False),
        # mode="reserved" → canceled 제외.
        ("reserved", "reserved", True),
        ("approved", "reserved", True),
        ("canceled", "reserved", False),
        # mode=None / 알 수 없음 → reserved 분기 (안전 fallback).
        ("reserved", None, True),
        ("canceled", None, False),
        ("approved", "unknown", True),
        ("canceled", "unknown", False),
    ],
)
def test_is_counted_for_mode(status, mode, expected):
    """COMPAT: ``api.py:stats_by_hour`` / ``stats_by_weekday`` mode 분기 정합."""
    assert _rules.is_counted_for_mode(status=status, mode=mode) is expected


@pytest.mark.parametrize(
    "status,mode,expected",
    [
        # by_treatment 는 mode="all" 분기 ⊥.
        ("reserved", "approved", False),
        ("approved", "approved", True),
        ("canceled", "approved", False),
        ("reserved", "reserved", True),
        ("canceled", "reserved", False),
        # 알 수 없음 → reserved fallback.
        ("approved", "all", True),  # all 도 canceled 만 제외.
        ("canceled", "all", False),
    ],
)
def test_is_counted_for_treatment_mode(status, mode, expected):
    """COMPAT: ``api.py:stats_by_treatment`` mode 분기 정합 (line 4192~4195)."""
    assert _rules.is_counted_for_treatment_mode(status=status, mode=mode) is expected


# ──────────────────────── 3. weekday 라벨 ─────────────────────────────────


def test_weekday_labels_match_api():
    """COMPAT: ``api.py:stats_by_weekday`` (line 4149) 정합."""
    expected = ("월", "화", "수", "목", "금", "토", "일")
    assert _rules.WEEKDAY_LABELS == expected
    for i, label in enumerate(expected):
        assert _rules.weekday_label(i) == label
    # 범위 밖 → 빈 문자열.
    assert _rules.weekday_label(7) == ""
    assert _rules.weekday_label(-1) == ""


def test_unassigned_sentinel():
    """COMPAT: ``api.py`` 통계 미배정 분기 정합."""
    assert _rules.UNASSIGNED_SENTINEL == "__none__"
    assert _rules.UNASSIGNED_LABEL == "미배정"


def test_eswt_code_matches_constants():
    """COMPAT: ``app.models.constants.ESWT_CODE`` 와 동일."""
    from app.models import constants as _C
    assert _rules.ESWT_CODE == _C.ESWT_CODE


# ──────────────────────── 4. resolve_stats_range / date_list ──────────────


def test_resolve_stats_range_with_date_range():
    """COMPAT: ``api.py:_resolve_stats_range`` (date_from/date_to 분기) 정합."""
    ts, te, label = _service.resolve_stats_range(
        year=None, month=None, date_from="2099-07-01", date_to="2099-07-31",
    )
    assert ts == datetime(2099, 7, 1)
    assert te == datetime(2099, 8, 1)  # te_inc + 1 day
    assert label == "2099-07-01~2099-07-31"


def test_resolve_stats_range_with_year_month():
    ts, te, label = _service.resolve_stats_range(
        year=2099, month=7, date_from="", date_to="",
    )
    assert ts == datetime(2099, 7, 1)
    assert te == datetime(2099, 8, 1)
    assert label == "2099-07"


def test_resolve_stats_range_with_year_month_dec():
    """12월 → 다음 해 1월."""
    ts, te, label = _service.resolve_stats_range(
        year=2099, month=12, date_from="", date_to="",
    )
    assert ts == datetime(2099, 12, 1)
    assert te == datetime(2100, 1, 1)
    assert label == "2099-12"


def test_resolve_stats_range_invalid_format():
    """잘못된 형식 → StatsRangeError."""
    with pytest.raises(_service.StatsRangeError):
        _service.resolve_stats_range(
            year=None, month=None, date_from="bad", date_to="2099-12-31",
        )


def test_resolve_stats_range_inverted():
    """date_to < date_from → StatsRangeError."""
    with pytest.raises(_service.StatsRangeError):
        _service.resolve_stats_range(
            year=None, month=None, date_from="2099-12-31", date_to="2099-01-01",
        )


def test_resolve_stats_range_byte_equivalent_with_api():
    """COMPAT: ``api.py:_resolve_stats_range`` 정합."""
    from app.routers.api import _resolve_stats_range

    cases = [
        (2099, 7, "", ""),
        (None, None, "2099-07-01", "2099-07-31"),
        (2099, 12, "", ""),
    ]
    for year, month, df, dt in cases:
        api_ts, api_te, api_label = _resolve_stats_range(year, month, df, dt)
        svc_ts, svc_te, svc_label = _service.resolve_stats_range(
            year=year, month=month, date_from=df, date_to=dt,
        )
        assert api_ts == svc_ts
        assert api_te == svc_te
        assert api_label == svc_label


def test_date_list_byte_equivalent_with_api():
    """COMPAT: ``api.py:_date_list`` 정합."""
    from app.routers.api import _date_list

    ts = datetime(2099, 7, 1)
    te = datetime(2099, 7, 4)  # 3일치
    api_result = _date_list(ts, te)
    svc_result = _service.date_list(ts, te)
    assert api_result == svc_result == ["2099-07-01", "2099-07-02", "2099-07-03"]


def test_date_list_empty_range():
    """ts >= te → 빈 리스트."""
    assert _service.date_list(datetime(2099, 7, 1), datetime(2099, 7, 1)) == []


# ──────────────────────── 5. aggregators — summary ────────────────────────


def _parse_codes(raw):
    """test 용 _parse_codes (api.py 정합)."""
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def test_aggregate_summary_basic():
    """COMPAT: ``api.py:stats_summary`` (line 4013~4033) 정합."""
    rows = [
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved", start_at=datetime(2099, 7, 1, 10, 0)),
        SimpleNamespace(treatment_codes='["manual30"]', status="approved", start_at=datetime(2099, 7, 1, 11, 0)),
        SimpleNamespace(treatment_codes='["eswt"]', status="reserved", start_at=datetime(2099, 7, 1, 12, 0)),
        SimpleNamespace(treatment_codes='["manual60"]', status="canceled", start_at=datetime(2099, 7, 1, 13, 0)),
    ]
    counts = _agg.aggregate_summary(
        rows=rows,
        manual_codes_set={"manual30", "manual60"},
        treatment_code="all",
        parse_codes=_parse_codes,
    )
    assert counts == {
        "total": 4,
        "manual": 2,         # manual30 reserved + manual30 approved (canceled 제외)
        "approved": 1,       # manual30 approved
        "manual_approved": 1,
        "canceled": 1,       # manual60 canceled
    }


def test_aggregate_summary_treatment_filter():
    """treatment_code 필터 정합."""
    rows = [
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved", start_at=datetime(2099, 7, 1)),
        SimpleNamespace(treatment_codes='["eswt"]', status="reserved", start_at=datetime(2099, 7, 1)),
    ]
    counts = _agg.aggregate_summary(
        rows=rows, manual_codes_set={"manual30"},
        treatment_code="manual30", parse_codes=_parse_codes,
    )
    assert counts["total"] == 1


def test_aggregate_summary_unit_increment_only():
    """RISK: 시간 가중치 회귀 방지 — manual30 / manual60 모두 +=1 만."""
    rows = [
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved", start_at=datetime(2099, 7, 1)),
        SimpleNamespace(treatment_codes='["manual60"]', status="reserved", start_at=datetime(2099, 7, 1)),
    ]
    counts = _agg.aggregate_summary(
        rows=rows, manual_codes_set={"manual30", "manual60"},
        treatment_code="manual_all", parse_codes=_parse_codes,
    )
    # manual30 + manual60 = total 2 (시간 가중치라면 1+2=3 이지만 1+1=2 가 정답).
    assert counts["total"] == 2
    assert counts["manual"] == 2


# ──────────────────────── 6. aggregators — by_hour / by_weekday ────────────


def test_aggregate_by_hour_basic():
    """COMPAT: ``api.py:stats_by_hour`` (line 4087~4098) 정합."""
    rows = [
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved",
                        start_at=datetime(2099, 7, 1, 10, 0)),
        SimpleNamespace(treatment_codes='["manual30"]', status="approved",
                        start_at=datetime(2099, 7, 1, 10, 30)),
        SimpleNamespace(treatment_codes='["manual30"]', status="canceled",
                        start_at=datetime(2099, 7, 1, 14, 0)),
    ]
    # mode=reserved → canceled 제외.
    counts = _agg.aggregate_by_hour(
        rows=rows, manual_codes_set={"manual30"},
        treatment_code="all", mode="reserved", parse_codes=_parse_codes,
    )
    assert counts == {10: 2}


def test_aggregate_by_hour_mode_approved():
    rows = [
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved",
                        start_at=datetime(2099, 7, 1, 10, 0)),
        SimpleNamespace(treatment_codes='["manual30"]', status="approved",
                        start_at=datetime(2099, 7, 1, 11, 0)),
    ]
    counts = _agg.aggregate_by_hour(
        rows=rows, manual_codes_set={"manual30"},
        treatment_code="all", mode="approved", parse_codes=_parse_codes,
    )
    assert counts == {11: 1}


def test_aggregate_by_weekday_basic():
    """COMPAT: ``api.py:stats_by_weekday`` (line 4136~4147) 정합."""
    # 2026-05-04 = 월요일 (weekday=0).
    rows = [
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved",
                        start_at=datetime(2026, 5, 4)),
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved",
                        start_at=datetime(2026, 5, 6)),  # 수요일
    ]
    counts = _agg.aggregate_by_weekday(
        rows=rows, manual_codes_set={"manual30"},
        treatment_code="all", mode="reserved", parse_codes=_parse_codes,
    )
    assert counts == {0: 1, 2: 1}


# ──────────────────────── 7. aggregators — by_treatment ────────────────────


def test_aggregate_by_treatment_basic():
    """COMPAT: ``api.py:stats_by_treatment`` (line 4190~4200) 정합."""
    rows = [
        SimpleNamespace(treatment_codes='["manual30", "eswt"]', status="reserved",
                        start_at=datetime(2099, 7, 1)),
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved",
                        start_at=datetime(2099, 7, 1)),
        SimpleNamespace(treatment_codes='["manual30"]', status="canceled",
                        start_at=datetime(2099, 7, 1)),
    ]
    # mode=reserved → canceled 제외. 한 예약에 여러 코드면 *각 코드마다* +1.
    counts = _agg.aggregate_by_treatment(
        rows=rows, manual_codes_set={"manual30"},
        treatment_code="all", mode="reserved", parse_codes=_parse_codes,
    )
    assert counts == {"manual30": 2, "eswt": 1}


# ──────────────────────── 8. aggregators — daily ──────────────────────────


def test_aggregate_daily_basic():
    """COMPAT: ``api.py:stats_daily`` (line 4256~4282) 정합."""
    rows = [
        SimpleNamespace(treatment_codes='["manual30"]', status="reserved",
                        start_at=datetime(2099, 7, 1, 10, 0)),
        SimpleNamespace(treatment_codes='["manual30", "eswt"]', status="approved",
                        start_at=datetime(2099, 7, 1, 11, 0)),
        SimpleNamespace(treatment_codes='["eswt"]', status="canceled",
                        start_at=datetime(2099, 7, 2, 9, 0)),
    ]
    daily = _agg.aggregate_daily(
        rows=rows,
        date_keys=["2099-07-01", "2099-07-02"],
        manual_codes=["manual30", "manual60"],
        manual_codes_set={"manual30", "manual60"},
        treatment_code="all",
        parse_codes=_parse_codes,
    )
    assert daily["2099-07-01"]["total"] == 2
    assert daily["2099-07-01"]["manual"] == 2
    assert daily["2099-07-01"]["approved"] == 1
    assert daily["2099-07-01"]["manual_approved"] == 1
    assert daily["2099-07-01"]["eswt"] == 1
    assert daily["2099-07-01"]["canceled"] == 0
    assert daily["2099-07-01"]["manual_by_code"]["manual30"] == 2
    assert daily["2099-07-01"]["manual_approved_by_code"]["manual30"] == 1
    assert daily["2099-07-02"]["canceled"] == 1
    assert daily["2099-07-02"]["total"] == 1


# ──────────────────────── 9. service — 응답 빌더 ──────────────────────────


def test_build_summary_response_keys_and_values():
    """COMPAT: ``api.py:stats_summary`` 응답 (line 4038~4053) 정합."""
    out = _service.build_summary_response(
        ts=datetime(2099, 7, 1),
        te=datetime(2099, 8, 1),
        range_label="2099-07",
        counts={"total": 100, "manual": 50, "approved": 80, "manual_approved": 40, "canceled": 5},
        treatment_code="all",
    )
    assert set(out.keys()) == _schemas.SUMMARY_RESPONSE_KEYS
    assert out["year"] == 2099
    assert out["month"] == 7
    assert out["date_from"] == "2099-07-01"
    assert out["date_to"] == "2099-07-31"
    assert out["days"] == 31
    assert out["total"] == 100
    assert out["manual"] == 50
    assert out["approved"] == 80
    assert out["canceled"] == 5
    assert out["treatment_code"] == "all"


def test_build_by_hour_response_keys():
    out = _service.build_by_hour_response(year=2099, month=7, counts={10: 5, 14: 3})
    assert set(out.keys()) == _schemas.BY_HOUR_RESPONSE_KEYS
    assert len(out["items"]) == 24
    for item in out["items"]:
        assert set(item.keys()) == _schemas.BY_HOUR_ITEM_KEYS
    assert out["items"][10]["count"] == 5
    assert out["items"][14]["count"] == 3
    assert out["items"][0]["count"] == 0  # 빈 시간대.
    assert out["items"][10]["label"] == "10시"


def test_build_by_weekday_response_keys():
    out = _service.build_by_weekday_response(year=2099, month=7, counts={0: 10, 6: 5})
    assert set(out.keys()) == _schemas.BY_WEEKDAY_RESPONSE_KEYS
    assert len(out["items"]) == 7
    for item in out["items"]:
        assert set(item.keys()) == _schemas.BY_WEEKDAY_ITEM_KEYS
    assert out["items"][0]["label"] == "월"
    assert out["items"][6]["label"] == "일"
    assert out["items"][0]["count"] == 10


def test_build_by_treatment_response_sorted_desc():
    out = _service.build_by_treatment_response(
        year=2099, month=7,
        counts={"manual30": 30, "eswt": 5, "manual60": 10},
        tx_name_map={"manual30": "도수30", "eswt": "충", "manual60": "도수60"},
    )
    assert set(out.keys()) == _schemas.BY_TREATMENT_RESPONSE_KEYS
    # 내림차순 정렬.
    assert out["items"][0]["code"] == "manual30"
    assert out["items"][1]["code"] == "manual60"
    assert out["items"][2]["code"] == "eswt"
    for item in out["items"]:
        assert set(item.keys()) == _schemas.BY_TREATMENT_ITEM_KEYS


def test_build_daily_response_keys():
    daily_counts = {
        "2099-07-01": {
            "total": 5, "approved": 3, "manual": 4, "manual_approved": 2,
            "eswt": 1, "canceled": 0,
            "manual_by_code": {"manual30": 4, "manual60": 0},
            "manual_approved_by_code": {"manual30": 2, "manual60": 0},
        },
    }
    out = _service.build_daily_response(
        ts=datetime(2099, 7, 1), te=datetime(2099, 7, 2),
        range_label="2099-07-01~2099-07-01",
        date_keys=["2099-07-01"], daily_counts=daily_counts,
        manual_codes=["manual30", "manual60"],
        manual_names={"manual30": "도수30", "manual60": "도수60"},
        treatment_code="all",
    )
    assert set(out.keys()) == _schemas.DAILY_RESPONSE_KEYS
    assert len(out["items"]) == 1
    for item in out["items"]:
        assert set(item.keys()) == _schemas.DAILY_ITEM_KEYS


# ──────────────────────── 10. repository — DB 격리 fixture ─────────────────


def test_list_appointments_in_range_byte_equivalent(client):
    """COMPAT: ``api.py:stats_summary`` query 패턴 정합."""
    from app.database import SessionLocal
    from app.models import models as _m

    ts = datetime(2099, 9, 1)
    te = datetime(2099, 10, 1)
    db = SessionLocal()
    try:
        repo_rows = _repo.list_appointments_in_range(db, start=ts, end=te)
        api_rows = (
            db.query(_m.Appointment)
            .filter(_m.Appointment.start_at >= ts, _m.Appointment.start_at < te)
            .all()
        )
        assert {a.id for a in repo_rows} == {a.id for a in api_rows}
    finally:
        db.close()


def test_list_manual_treatment_rows(client):
    """COMPAT: ``api.py:_get_manual_treatment_rows`` 정합."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_manual_treatment_rows(db)
        for t in rows:
            assert t.role == "therapist"
            assert t.code != _rules.ESWT_CODE
            assert bool(t.active) is True
    finally:
        db.close()


def test_list_manual_treatment_codes(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        codes = _repo.list_manual_treatment_codes(db)
        assert isinstance(codes, list)
        for c in codes:
            assert c != _rules.ESWT_CODE
    finally:
        db.close()


def test_list_therapist_employees(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_therapist_employees(db)
        for e in rows:
            assert e.role == "therapist"
    finally:
        db.close()


# ──────────────────────── 11. schemas — contract 회귀 보호 ─────────────────


def test_summary_response_keys_contract():
    assert _schemas.SUMMARY_RESPONSE_KEYS == frozenset({
        "year", "month", "date_from", "date_to", "range_label", "days",
        "total", "manual", "approved", "manual_approved", "canceled",
        "treatment_code",
    })


def test_by_hour_keys_contract():
    assert _schemas.BY_HOUR_RESPONSE_KEYS == frozenset({"year", "month", "items"})
    assert _schemas.BY_HOUR_ITEM_KEYS == frozenset({"hour", "label", "count"})


def test_by_weekday_keys_contract():
    assert _schemas.BY_WEEKDAY_RESPONSE_KEYS == frozenset({"year", "month", "items"})
    assert _schemas.BY_WEEKDAY_ITEM_KEYS == frozenset({"weekday", "label", "count"})


def test_by_treatment_keys_contract():
    assert _schemas.BY_TREATMENT_RESPONSE_KEYS == frozenset({"year", "month", "items"})
    assert _schemas.BY_TREATMENT_ITEM_KEYS == frozenset({"code", "label", "count"})


def test_daily_keys_contract():
    assert "manual_codes" in _schemas.DAILY_RESPONSE_KEYS
    assert "manual_by_code" in _schemas.DAILY_ITEM_KEYS


def test_aggregate_keys_contract():
    assert _schemas.AGGREGATE_RESPONSE_KEYS == frozenset({
        "year", "month", "manual_codes", "manual_names", "eswt_name", "items",
    })
    assert _schemas.AGGREGATE_ITEM_KEYS == frozenset({
        "therapist_id", "therapist_name", "manual_breakdown",
        "new_patient_count", "eswt_count",
    })


# ──────────────────────── 12. 단방향 경계 (D-4) ────────────────────────────


def test_rules_does_not_import_routers():
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src
    assert "from app.routers" not in src


def test_rules_does_not_import_orm_or_db():
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    assert "from app.models.models" not in src
    assert "from app.database" not in src
    assert "sqlalchemy" not in src.lower()
    assert "fastapi" not in src.lower()


def test_aggregators_does_not_import_routers_or_orm():
    src = Path(_agg.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src
    assert "from app.models" not in src
    assert "from app.database" not in src
    assert "sqlalchemy" not in src.lower()
    assert "fastapi" not in src.lower()


def test_repository_does_not_import_routers():
    src = Path(_repo.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_repository_uses_lazy_import_for_models():
    """repository.py 가 ``app.models`` 을 함수 안 lazy import — 순환참조 회피."""
    src = Path(_repo.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        if line.startswith("from app.models"):
            pytest.fail(f"top-level app.models import 발견: {line}")


def test_service_does_not_import_routers():
    src = Path(_service.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_schemas_does_not_import_routers():
    src = Path(_schemas.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_modules_stats_importable():
    """app.modules.stats 패키지 import 가능."""
    import app.modules.stats  # noqa: F401
    import app.modules.stats.aggregators  # noqa: F401
    import app.modules.stats.repository  # noqa: F401
    import app.modules.stats.rules  # noqa: F401
    import app.modules.stats.schemas  # noqa: F401
    import app.modules.stats.service  # noqa: F401


# ──────────────────────── 13. 라우터 시그니처 무수정 ────────────────────────


@pytest.mark.parametrize(
    "func_name",
    [
        "stats_summary",
        "stats_by_hour",
        "stats_by_weekday",
        "stats_by_treatment",
        "stats_daily",
        "stats_aggregate",
        "stats_by_therapist",
        "stats_manual_by_therapist",
        "stats_daily_by_therapist",
    ],
)
def test_stats_router_signatures_unchanged(func_name):
    """라우터 9개 통계 핸들러 시그니처 보존."""
    from app.routers import api as _api_module

    fn = getattr(_api_module, func_name, None)
    assert fn is not None, f"{func_name} 미존재"
    sig = inspect.signature(fn)
    assert "db" in sig.parameters


# ──────────────────────── 14. 기존 흐름 영향 없음 (계약 회귀 보호) ────────


def test_stats_summary_endpoint_keys_match_contract(client):
    """``GET /api/stats/summary`` 응답 키 = ``SUMMARY_RESPONSE_KEYS``."""
    r = client.get("/api/stats/summary?year=2099&month=7")
    assert r.status_code == 200
    assert set(r.json().keys()) == _schemas.SUMMARY_RESPONSE_KEYS


def test_stats_by_hour_endpoint_keys_match_contract(client):
    r = client.get("/api/stats/by-hour?year=2099&month=7")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == _schemas.BY_HOUR_RESPONSE_KEYS
    assert len(body["items"]) == 24
    for item in body["items"]:
        assert set(item.keys()) == _schemas.BY_HOUR_ITEM_KEYS


def test_stats_by_weekday_endpoint_keys_match_contract(client):
    r = client.get("/api/stats/by-weekday?year=2099&month=7")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == _schemas.BY_WEEKDAY_RESPONSE_KEYS
    assert len(body["items"]) == 7
    for item in body["items"]:
        assert set(item.keys()) == _schemas.BY_WEEKDAY_ITEM_KEYS


def test_stats_by_treatment_endpoint_keys_match_contract(client):
    r = client.get("/api/stats/by-treatment?year=2099&month=7")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == _schemas.BY_TREATMENT_RESPONSE_KEYS
    for item in body["items"]:
        assert set(item.keys()) == _schemas.BY_TREATMENT_ITEM_KEYS


def test_stats_daily_endpoint_keys_match_contract(client):
    r = client.get("/api/stats/daily?year=2099&month=7")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == _schemas.DAILY_RESPONSE_KEYS
    for item in body["items"]:
        assert set(item.keys()) == _schemas.DAILY_ITEM_KEYS


def test_stats_aggregate_endpoint_keys_match_contract(client):
    r = client.get("/api/stats/aggregate?year=2099&month=7")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == _schemas.AGGREGATE_RESPONSE_KEYS


# ──────────────────────── 15. stats 모듈은 read-only — DB 변경 ⊥ ────────────


def test_stats_module_does_not_use_session_commit_or_add():
    """SAFETY: stats 모듈 어느 파일도 ``db.commit()`` / ``db.add()`` / ``db.delete()``
    미사용 — read-only 보장."""
    files = [
        Path(_rules.__file__),
        Path(_repo.__file__),
        Path(_agg.__file__),
        Path(_service.__file__),
        Path(_schemas.__file__),
    ]
    for f in files:
        src = f.read_text(encoding="utf-8")
        assert "db.commit" not in src, f"{f.name}: db.commit() 발견"
        assert "db.add(" not in src, f"{f.name}: db.add() 발견"
        assert "db.delete(" not in src, f"{f.name}: db.delete() 발견"
        assert "db.flush" not in src, f"{f.name}: db.flush() 발견"


def test_stats_module_no_external_calls():
    """SAFETY: stats 모듈 어느 파일도 ``urllib.request`` / ``requests`` / ``httpx``
    import ⊥ — 외부 API 호출 ⊥."""
    files = [
        Path(_rules.__file__),
        Path(_repo.__file__),
        Path(_agg.__file__),
        Path(_service.__file__),
        Path(_schemas.__file__),
    ]
    for f in files:
        src = f.read_text(encoding="utf-8")
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert "urllib.request" not in stripped
                assert "import requests" not in stripped
                assert "import httpx" not in stripped
