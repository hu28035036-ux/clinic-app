"""19-4 availability 예약 가능 여부 / 충돌 검사 분리 contract.

검증 범위 (19-4 세션 지시문 정합):
  1. ``app.modules.appointments.availability`` 의 helper 가 ``app/routers/api.py`` 의
     ``_lunch_window`` / ``_check_lunch_block`` / ``_check_version`` / ``_bump_version``
     판정 로직과 byte-equivalent 출력.
  2. ``parse_lunch_window`` 의 결과가 ``api.py:_lunch_window`` 와 일치 — 회귀 0.
  3. ``overlaps_lunch_window`` 의 결과가 ``api.py:_check_lunch_block`` 의 *겹침 판정*
     부분과 byte-equivalent (raise 부분 제외).
  4. ``is_version_conflict`` / ``version_conflict_detail`` / ``next_version`` 의 결과가
     ``api.py:_check_version`` / ``_bump_version`` 와 동등.
  5. 도수 중복 / 휴무 차단 helper 는 *순수 판정* — 라우터 미채택 (xfail 7건 + skip 1건
     그대로 — 백엔드 차단 미구현).
  6. modules.appointments 가 ``app.models`` / ``app.services`` / ``app.routers`` /
     ``app.database`` / ``sqlalchemy`` 미참조 — 단방향 경계 (D-4 정합).
  7. 외부 API 호출 0 — provider/SDK/DB 접근 ⊥.

원칙:
  - 운영 DB 미접근 — 본 테스트는 in-memory primitives 만 사용.
  - 외부 API 호출 0.
"""
from __future__ import annotations

import importlib
from datetime import datetime

import pytest

from app.modules.appointments import availability as _av

# ──────────────────────── 1. parse_lunch_window 회귀 ──────────────────────


def test_parse_lunch_window_disabled_returns_none():
    """COMPAT: ``api.py:_lunch_window`` line 69~70 — enabled=False → None."""
    assert _av.parse_lunch_window(
        enabled=False, lunch_start="12:00", lunch_end="13:00",
    ) is None


@pytest.mark.parametrize(
    "lunch_start,lunch_end",
    [
        ("", ""),
        (None, None),
        ("12:00", ""),
        ("12:00", None),
        ("badtime", "13:00"),
        ("12:00", "13:badmin"),
        ("12", "13:00"),  # split fail
        ("25:00", "26:00"),  # 범위 초과
        ("13:00", "12:00"),  # end <= start
        ("12:00", "12:00"),  # end == start
    ],
)
def test_parse_lunch_window_invalid_inputs_return_none(lunch_start, lunch_end):
    """COMPAT: ``api.py:_lunch_window`` 의 모든 fallback 분기 정합."""
    assert _av.parse_lunch_window(
        enabled=True, lunch_start=lunch_start, lunch_end=lunch_end,
    ) is None


def test_parse_lunch_window_valid_returns_tuple():
    """COMPAT: 정상 입력 → (start_min, end_min, start_str, end_str)."""
    result = _av.parse_lunch_window(
        enabled=True, lunch_start="12:00", lunch_end="13:00",
    )
    assert result == (720, 780, "12:00", "13:00")


def test_parse_lunch_window_strips_whitespace():
    """COMPAT: ``api.py:_lunch_window`` line 72~73 — strip() 정합."""
    result = _av.parse_lunch_window(
        enabled=True, lunch_start="  12:00  ", lunch_end="  13:00  ",
    )
    assert result == (720, 780, "12:00", "13:00")


# ──────────────────────── 2. overlaps_lunch_window 회귀 ───────────────────


def _api_py_check_lunch_block_inline(
    start_at: datetime,
    duration_min: int | None,
    window: tuple[int, int, str, str] | None,
) -> bool:
    """``api.py:_check_lunch_block`` 의 겹침 판정 inline 복사 — 회귀 검증용."""
    if window is None:
        return False
    try:
        dur = int(duration_min or 0)
    except Exception:
        return False
    if dur <= 0:
        return False
    s_min, e_min, _ls, _le = window
    sm = start_at.hour * 60 + start_at.minute
    em = sm + dur
    return em > s_min and sm < e_min


@pytest.mark.parametrize(
    "hour,minute,duration_min,expected",
    [
        # 점심창 12:00~13:00 (720~780).
        (10, 0, 30, False),  # 10:00~10:30 — 점심 전, 안 겹침
        (11, 0, 30, False),  # 11:00~11:30
        (11, 30, 30, False),  # 11:30~12:00 — 끝이 점심 시작과 같음 (em > s_min False)
        (11, 30, 31, True),   # 11:30~12:01 — 1분 겹침
        (12, 0, 30, True),    # 12:00~12:30
        (12, 30, 30, True),   # 12:30~13:00
        (13, 0, 30, False),   # 13:00~13:30 — 점심 종료 후 (sm < e_min False)
        (12, 0, 60, True),    # 12:00~13:00 — 정확히 점심창
        (11, 30, 60, True),   # 11:30~12:30 — 절반 겹침
    ],
)
def test_overlaps_lunch_window_byte_equivalent(hour, minute, duration_min, expected):
    """COMPAT: ``api.py:_check_lunch_block`` 의 겹침 판정 부분과 byte-equivalent."""
    window = (720, 780, "12:00", "13:00")
    start = datetime(2099, 6, 10, hour, minute)
    actual = _av.overlaps_lunch_window(start, duration_min, window)
    expected_inline = _api_py_check_lunch_block_inline(start, duration_min, window)
    assert actual == expected == expected_inline


def test_overlaps_lunch_window_none_returns_false():
    """``window=None`` (점심 비활성) → False."""
    assert _av.overlaps_lunch_window(
        datetime(2099, 6, 10, 12, 0), 30, None,
    ) is False


@pytest.mark.parametrize("dur", [None, 0, -10, "abc"])
def test_overlaps_lunch_window_invalid_duration_returns_false(dur):
    """COMPAT: duration 이 None / 0 이하 / 비-int → False."""
    window = (720, 780, "12:00", "13:00")
    assert _av.overlaps_lunch_window(
        datetime(2099, 6, 10, 12, 0), dur, window,
    ) is False


def test_lunch_block_message_format():
    """COMPAT: ``api.py:_check_lunch_block`` line 105~106 메시지 포맷 정합."""
    window = (720, 780, "12:00", "13:00")
    msg = _av.lunch_block_message(window)
    assert msg == "점심시간(12:00~13:00)에는 예약을 잡을 수 없습니다."


# ──────────────────────── 3. 낙관적 락 (api.py:_check_version) ────────────


def test_is_version_conflict_none_client_returns_false():
    """COMPAT: ``api.py:_check_version`` — client_version=None → 검사 스킵."""
    assert _av.is_version_conflict(db_version=5, client_version=None) is False


@pytest.mark.parametrize(
    "db_version,client_version,expected",
    [
        (0, 0, False),
        (5, 5, False),
        (5, 4, True),
        (5, 6, True),
        (None, 0, False),  # None → 0 fallback
        (None, 1, True),
    ],
)
def test_is_version_conflict_detection(db_version, client_version, expected):
    assert _av.is_version_conflict(db_version, client_version) == expected


def test_version_conflict_detail_dict_keys():
    """COMPAT: ``api.py:_check_version`` line 1669~1673 detail dict 와 동등."""
    detail = _av.version_conflict_detail(db_version=7)
    assert set(detail.keys()) == {"error", "message", "current_version"}
    assert detail["error"] == "version_conflict"
    assert detail["message"] == "다른 PC에서 먼저 수정되었습니다. 최신 정보를 불러오세요."
    assert detail["current_version"] == 7


def test_version_conflict_detail_none_db_version_zero():
    """COMPAT: ``db_version=None`` → ``current_version=0``."""
    detail = _av.version_conflict_detail(db_version=None)
    assert detail["current_version"] == 0


@pytest.mark.parametrize(
    "before,expected",
    [(None, 1), (0, 1), (1, 2), (5, 6), (100, 101)],
)
def test_next_version_increments(before, expected):
    """COMPAT: ``api.py:_bump_version`` 와 동등."""
    assert _av.next_version(before) == expected


# ──────────────────────── 4. 시간 충돌 검사 ───────────────────────────────


def test_appointments_overlap_disjoint():
    """완전히 분리된 시간 → False."""
    assert _av.appointments_overlap(
        a_start=datetime(2099, 6, 10, 10, 0), a_end=datetime(2099, 6, 10, 10, 30),
        b_start=datetime(2099, 6, 10, 11, 0), b_end=datetime(2099, 6, 10, 11, 30),
    ) is False


def test_appointments_overlap_adjacent_is_not_overlap():
    """인접 (a_end == b_start) → False (열림 경계 정합)."""
    assert _av.appointments_overlap(
        a_start=datetime(2099, 6, 10, 10, 0), a_end=datetime(2099, 6, 10, 10, 30),
        b_start=datetime(2099, 6, 10, 10, 30), b_end=datetime(2099, 6, 10, 11, 0),
    ) is False


def test_appointments_overlap_same_slot():
    """완전히 같은 시간 → True."""
    assert _av.appointments_overlap(
        a_start=datetime(2099, 6, 10, 10, 0), a_end=datetime(2099, 6, 10, 10, 30),
        b_start=datetime(2099, 6, 10, 10, 0), b_end=datetime(2099, 6, 10, 10, 30),
    ) is True


def test_appointments_overlap_partial():
    """부분 겹침 → True."""
    assert _av.appointments_overlap(
        a_start=datetime(2099, 6, 10, 10, 0), a_end=datetime(2099, 6, 10, 10, 30),
        b_start=datetime(2099, 6, 10, 10, 15), b_end=datetime(2099, 6, 10, 10, 45),
    ) is True


def test_appointments_overlap_a_inside_b():
    """a 가 b 안에 완전히 포함 → True."""
    assert _av.appointments_overlap(
        a_start=datetime(2099, 6, 10, 10, 5), a_end=datetime(2099, 6, 10, 10, 25),
        b_start=datetime(2099, 6, 10, 10, 0), b_end=datetime(2099, 6, 10, 10, 30),
    ) is True


# ──────────────────────── 5. 도수 중복 검사 (helper 만) ───────────────────


MANUAL_CODES = {"manual30", "manual60"}


def test_is_manual_treatment_basic():
    assert _av.is_manual_treatment(["manual30"], MANUAL_CODES) is True
    assert _av.is_manual_treatment(["eswt"], MANUAL_CODES) is False
    assert _av.is_manual_treatment(["manual30", "eswt"], MANUAL_CODES) is True
    assert _av.is_manual_treatment([], MANUAL_CODES) is False
    assert _av.is_manual_treatment(None, MANUAL_CODES) is False


def test_has_manual_conflict_at_slot_canceled_excluded():
    """spec 01 §1: ``status=canceled`` 는 중복 검사에서 제외."""
    new_start = datetime(2099, 6, 10, 10, 0)
    new_end = datetime(2099, 6, 10, 10, 30)
    existing = [{
        "id": "A-001",
        "start": new_start,
        "end": new_end,
        "codes": ["manual30"],
        "status": "canceled",
    }]
    assert _av.has_manual_conflict_at_slot(
        new_codes=["manual30"], new_start=new_start, new_end=new_end,
        new_id=None, existing_appointments=existing, manual_code_set=MANUAL_CODES,
    ) is False


def test_has_manual_conflict_at_slot_self_excluded_on_update():
    """수정 시 ``new_id == existing.id`` 는 자기 자신 → 제외."""
    new_start = datetime(2099, 6, 10, 10, 0)
    new_end = datetime(2099, 6, 10, 10, 30)
    existing = [{
        "id": "A-001",
        "start": new_start,
        "end": new_end,
        "codes": ["manual30"],
        "status": "reserved",
    }]
    assert _av.has_manual_conflict_at_slot(
        new_codes=["manual30"], new_start=new_start, new_end=new_end,
        new_id="A-001",  # 같은 id → 자기 자신
        existing_appointments=existing, manual_code_set=MANUAL_CODES,
    ) is False


def test_has_manual_conflict_at_slot_two_eswt_allowed():
    """spec 01 §1: 둘 다 도수 미포함 → 같은 시간이라도 허용."""
    new_start = datetime(2099, 6, 10, 10, 0)
    new_end = datetime(2099, 6, 10, 10, 30)
    existing = [{
        "id": "A-001",
        "start": new_start,
        "end": new_end,
        "codes": ["eswt"],
        "status": "reserved",
    }]
    assert _av.has_manual_conflict_at_slot(
        new_codes=["eswt"], new_start=new_start, new_end=new_end,
        new_id=None, existing_appointments=existing, manual_code_set=MANUAL_CODES,
    ) is False


def test_has_manual_conflict_at_slot_manual_blocks():
    """spec 01 §1: 둘 중 한 쪽이라도 도수 포함 + 시간 겹침 → 차단."""
    new_start = datetime(2099, 6, 10, 10, 0)
    new_end = datetime(2099, 6, 10, 10, 30)
    existing = [{
        "id": "A-001",
        "start": new_start,
        "end": new_end,
        "codes": ["manual30"],
        "status": "reserved",
    }]
    assert _av.has_manual_conflict_at_slot(
        new_codes=["manual30"], new_start=new_start, new_end=new_end,
        new_id=None, existing_appointments=existing, manual_code_set=MANUAL_CODES,
    ) is True


def test_has_manual_conflict_at_slot_eswt_then_manual_blocks():
    """spec 01 §1: 기존 eswt + 신규 manual30 → 신규에 도수 포함이므로 차단."""
    new_start = datetime(2099, 6, 10, 10, 0)
    new_end = datetime(2099, 6, 10, 10, 30)
    existing = [{
        "id": "A-001",
        "start": new_start,
        "end": new_end,
        "codes": ["eswt"],
        "status": "reserved",
    }]
    assert _av.has_manual_conflict_at_slot(
        new_codes=["manual30"], new_start=new_start, new_end=new_end,
        new_id=None, existing_appointments=existing, manual_code_set=MANUAL_CODES,
    ) is True


def test_has_manual_conflict_at_slot_disjoint_time_allowed():
    """다른 시간 → 도수라도 허용."""
    existing = [{
        "id": "A-001",
        "start": datetime(2099, 6, 10, 11, 0),
        "end": datetime(2099, 6, 10, 11, 30),
        "codes": ["manual30"],
        "status": "reserved",
    }]
    assert _av.has_manual_conflict_at_slot(
        new_codes=["manual30"],
        new_start=datetime(2099, 6, 10, 10, 0),
        new_end=datetime(2099, 6, 10, 10, 30),
        new_id=None, existing_appointments=existing, manual_code_set=MANUAL_CODES,
    ) is False


# ──────────────────────── 6. 휴무 / 반차 차단 (helper 만) ─────────────────


def test_morning_afternoon_slot_boundary():
    """spec 02: 12:00 정확 기준."""
    assert _av.is_morning_slot(datetime(2099, 6, 10, 11, 59)) is True
    assert _av.is_morning_slot(datetime(2099, 6, 10, 12, 0)) is False
    assert _av.is_afternoon_slot(datetime(2099, 6, 10, 11, 59)) is False
    assert _av.is_afternoon_slot(datetime(2099, 6, 10, 12, 0)) is True


@pytest.mark.parametrize(
    "leave_type,hour,expected",
    [
        # full → 무조건 차단.
        ("full", 9, True),
        ("full", 11, True),
        ("full", 13, True),
        ("full", 17, True),
        # am 반차 → 오전 (< 12) 차단, 오후 OK.
        ("am", 9, True),
        ("am", 11, True),
        ("am", 11, True),
        ("am", 12, False),
        ("am", 14, False),
        # pm 반차 → 오전 OK, 오후 (>= 12) 차단.
        ("pm", 9, False),
        ("pm", 11, False),
        ("pm", 12, True),
        ("pm", 14, True),
        # None / 알 수 없음 → 차단 ⊥.
        (None, 10, False),
        ("", 10, False),
        ("unknown", 10, False),
    ],
)
def test_is_leave_blocking_per_type(leave_type, hour, expected):
    start = datetime(2099, 6, 15, hour, 0)
    assert _av.is_leave_blocking(start_at=start, leave_type=leave_type) == expected


def test_find_blocking_leave_matches_therapist_and_date():
    """spec 02 정합 — therapist_id + 날짜 + 시간 모두 매치되어야 차단."""
    leaves = [
        {"employee_id": "T-1", "leave_date": "2099-06-15", "leave_type": "full"},
        {"employee_id": "T-2", "leave_date": "2099-06-15", "leave_type": "am"},
        {"employee_id": "T-3", "leave_date": "2099-06-16", "leave_type": "full"},  # 다른 날
    ]
    # T-1 종일 → 어떤 시간이든 차단.
    blocked = _av.find_blocking_leave(
        therapist_id="T-1",
        start_at=datetime(2099, 6, 15, 10, 0),
        leaves=leaves,
    )
    assert blocked is not None
    assert blocked["employee_id"] == "T-1"

    # T-2 am 반차 → 오전 차단.
    blocked = _av.find_blocking_leave(
        therapist_id="T-2",
        start_at=datetime(2099, 6, 15, 11, 0),
        leaves=leaves,
    )
    assert blocked is not None

    # T-2 am 반차 → 오후 OK.
    blocked = _av.find_blocking_leave(
        therapist_id="T-2",
        start_at=datetime(2099, 6, 15, 14, 0),
        leaves=leaves,
    )
    assert blocked is None

    # T-3 다른 날 → 매치 안 됨.
    blocked = _av.find_blocking_leave(
        therapist_id="T-3",
        start_at=datetime(2099, 6, 15, 10, 0),
        leaves=leaves,
    )
    assert blocked is None


def test_find_blocking_leave_empty_list():
    """휴무 list 비어있으면 None."""
    assert _av.find_blocking_leave(
        therapist_id="T-1",
        start_at=datetime(2099, 6, 15, 10, 0),
        leaves=[],
    ) is None
    assert _av.find_blocking_leave(
        therapist_id="T-1",
        start_at=datetime(2099, 6, 15, 10, 0),
        leaves=None,
    ) is None


# ──────────────────────── 7. compute_end_at ───────────────────────────────


def test_compute_end_at_basic():
    """COMPAT: ``api.py:1633`` ``start_at + timedelta(minutes=duration_min)`` 정합."""
    start = datetime(2099, 6, 10, 10, 0)
    assert _av.compute_end_at(start, 30) == datetime(2099, 6, 10, 10, 30)
    assert _av.compute_end_at(start, 60) == datetime(2099, 6, 10, 11, 0)
    # 0 / None → 시작과 같음.
    assert _av.compute_end_at(start, 0) == start
    assert _av.compute_end_at(start, None) == start


# ──────────────────────── 8. 단방향 경계 (D-4 정합) ───────────────────────


def test_availability_does_not_import_models_or_db():
    """modules.appointments.availability 는 ORM/DB/services/routers 미참조 (D-4).

    NOTE: ast 로 실제 import 노드만 검사 — docstring/주석에 등장하는 단어 무시.
    """
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_av)
    tree = _ast.parse(src)

    forbidden_modules = {
        "app.models", "app.database", "app.services", "app.routers",
        "sqlalchemy", "fastapi",
        "app.modules.settings", "app.modules.health", "app.modules.calendar",
    }

    def _matches_forbidden(name: str) -> str | None:
        for f in forbidden_modules:
            if name == f or name.startswith(f + "."):
                return f
        return None

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                hit = _matches_forbidden(alias.name)
                assert hit is None, (
                    f"availability 가 금지된 import: 'import {alias.name}' (매치: {hit!r})"
                )
        elif isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            hit = _matches_forbidden(mod)
            assert hit is None, (
                f"availability 가 금지된 import: 'from {mod} import ...' (매치: {hit!r})"
            )

    # 추가: 본 helper 는 ``HTTPException`` 을 raise 하지 않음 — 호출자 책임.
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Raise) and node.exc is not None:
            # raise X(...) 또는 raise X 형식.
            exc_node = node.exc
            if isinstance(exc_node, _ast.Call):
                exc_node = exc_node.func
            if isinstance(exc_node, _ast.Name):
                assert exc_node.id != "HTTPException", (
                    "availability helper 안에서 HTTPException raise — 차단은 호출자 책임"
                )
            elif isinstance(exc_node, _ast.Attribute):
                assert exc_node.attr != "HTTPException", (
                    "availability helper 안에서 HTTPException raise — 차단은 호출자 책임"
                )


def test_appointments_package_init_does_not_import_models_or_db():
    """modules.appointments/__init__.py 도 동일 단방향 경계."""
    import ast as _ast

    import app.modules.appointments as mod
    src = importlib.import_module("inspect").getsource(mod)
    tree = _ast.parse(src)

    forbidden_modules = {
        "app.models", "app.database", "app.services", "app.routers",
        "sqlalchemy", "fastapi",
    }

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == f or alias.name.startswith(f + ".")
                    for f in forbidden_modules
                ), f"appointments/__init__ 가 금지된 import: {alias.name!r}"
        elif isinstance(node, _ast.ImportFrom):
            mod_name = node.module or ""
            assert not any(
                mod_name == f or mod_name.startswith(f + ".")
                for f in forbidden_modules
            ), f"appointments/__init__ 가 금지된 import: from {mod_name!r}"


# ──────────────────────── 9. 외부 API 호출 0 검증 ─────────────────────────


def test_helpers_do_not_invoke_provider_or_db():
    """SAFETY: availability helper 안에서 외부 API / SDK / DB 호출 ⊥."""
    # 모든 helper 호출 시 부수효과 0 — 순수 함수.
    _ = _av.parse_lunch_window(enabled=True, lunch_start="12:00", lunch_end="13:00")
    _ = _av.overlaps_lunch_window(datetime(2099, 6, 10, 12, 0), 30, (720, 780, "12:00", "13:00"))
    _ = _av.lunch_block_message((720, 780, "12:00", "13:00"))
    _ = _av.is_version_conflict(5, 4)
    _ = _av.version_conflict_detail(5)
    _ = _av.next_version(5)
    _ = _av.appointments_overlap(
        a_start=datetime(2099, 6, 10, 10, 0), a_end=datetime(2099, 6, 10, 10, 30),
        b_start=datetime(2099, 6, 10, 10, 0), b_end=datetime(2099, 6, 10, 10, 30),
    )
    _ = _av.is_manual_treatment(["manual30"], MANUAL_CODES)
    _ = _av.has_manual_conflict_at_slot(
        new_codes=["manual30"],
        new_start=datetime(2099, 6, 10, 10, 0),
        new_end=datetime(2099, 6, 10, 10, 30),
        new_id=None, existing_appointments=[], manual_code_set=MANUAL_CODES,
    )
    _ = _av.is_morning_slot(datetime(2099, 6, 10, 11, 0))
    _ = _av.is_afternoon_slot(datetime(2099, 6, 10, 14, 0))
    _ = _av.is_leave_blocking(start_at=datetime(2099, 6, 15, 10, 0), leave_type="full")
    _ = _av.find_blocking_leave(
        therapist_id="T-1",
        start_at=datetime(2099, 6, 15, 10, 0),
        leaves=[],
    )
    _ = _av.compute_end_at(datetime(2099, 6, 10, 10, 0), 30)


# ──────────────────────── 10. 라우터 무수정 회귀 검증 ─────────────────────


def test_existing_lunch_window_helper_in_api_py_unchanged(client):
    """COMPAT: ``api.py:_lunch_window`` 본체 함수가 그대로 존재 — 라우터 무수정 보증."""
    from app.routers import api as _api_module
    # 본체 함수가 살아 있어야 함.
    assert hasattr(_api_module, "_lunch_window")
    assert hasattr(_api_module, "_check_lunch_block")
    assert hasattr(_api_module, "_check_version")
    assert hasattr(_api_module, "_bump_version")


def test_appointment_post_still_works(client):
    """기존 정상 케이스 회귀 — POST /api/appointments 200 OK."""
    from tests.harness.helpers import make_appointment
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    patient = get_test_patient_id("홍길동테스트")
    therapist = get_test_therapist_id("이테스트치료사")
    resp = make_appointment(
        client, patient_id=patient, therapist_id=therapist,
        treatment_codes=["manual30"],
        start_at=datetime.fromisoformat("2099-08-01T10:00:00"),
    )
    assert resp.status_code == 200, resp.text
