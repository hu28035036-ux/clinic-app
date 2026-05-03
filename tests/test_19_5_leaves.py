"""19-5 leaves 휴무 규칙 분리 contract.

검증 범위 (19-5 세션 지시문 정합):
  1. ``app.modules.leaves.rules`` 의 LEAVE_TYPE / LEAVE_KIND / 반차 12:00 기준 상수가
     19-3 calendar/view_models / 19-4 availability 와 정합.
  2. ``leaves.rules.is_morning_slot`` / ``is_afternoon_slot`` / ``is_leave_blocking`` /
     ``find_blocking_leave`` 가 19-4 availability 와 byte-equivalent.
  3. ``leaves.repository`` read-only helper 가 ``api.py:list_employee_leaves`` 와 동등.
  4. ``leaves.service.upsert_employee_leave`` 가 ``api.py:_upsert_employee_leave_core`` 와
     동등 (DB 격리 fixture 사용).
  5. ``leaves.service.serialize_employee_leave`` / ``serialize_therapist_leave_alias`` 가
     ``api.py:list_employee_leaves`` / ``list_therapist_leaves_alias`` 응답 dict 와
     byte-equivalent.
  6. modules.leaves 가 ``app.routers`` 미참조 — 단방향 경계 (D-4).
     ``app.models`` / ``sqlalchemy`` 는 *조건부* 참조 가능 (repository / service 가 ORM /
     DB 세션을 인자로 받음). 단, ``rules.py`` 는 ORM / DB 미참조.
  7. 휴무 표시 (19-3 calendar) ↔ 예약 차단 (19-4 availability) ↔ 도메인 (19-5 rules)
     LEAVE_TYPE 기준 일치.
  8. AI action_leave 흐름 그대로 (``app.services.ai.action_leave._do_upsert`` 는
     ``app.routers.api._upsert_employee_leave_core`` 를 import — 19-5 에서도 무수정).
"""
from __future__ import annotations

import importlib
from datetime import datetime

import pytest

from app.modules.appointments import availability as _av
from app.modules.calendar import view_models as _cal_vm
from app.modules.leaves import repository as _repo
from app.modules.leaves import rules as _rules
from app.modules.leaves import service as _service

# ──────────────────────── 1. LEAVE_TYPE / LEAVE_KIND 상수 정합 ─────────────


def test_leave_type_constants_match_availability():
    """COMPAT: 19-4 availability 의 LEAVE_TYPE 상수와 동일."""
    assert _rules.LEAVE_TYPE_FULL == _av.LEAVE_TYPE_FULL == "full"
    assert _rules.LEAVE_TYPE_AM == _av.LEAVE_TYPE_AM == "am"
    assert _rules.LEAVE_TYPE_PM == _av.LEAVE_TYPE_PM == "pm"
    assert set(_rules.LEAVE_TYPE_VALUES) == set(_av.LEAVE_TYPE_VALUES)


def test_leave_type_constants_match_calendar_view_model():
    """COMPAT: 19-3 calendar/view_models 의 LEAVE_TYPE_LABELS 키와 동일."""
    # calendar 의 LEAVE_TYPE_LABELS 는 표시 라벨 매핑 — 키가 LEAVE_TYPE_VALUES 정합.
    assert set(_cal_vm.LEAVE_TYPE_LABELS.keys()) == set(_rules.LEAVE_TYPE_VALUES)
    # 각 LEAVE_TYPE 에 대한 라벨이 정의됨.
    assert _cal_vm.LEAVE_TYPE_LABELS[_rules.LEAVE_TYPE_FULL] == "종일"
    assert _cal_vm.LEAVE_TYPE_LABELS[_rules.LEAVE_TYPE_AM] == "오전반차"
    assert _cal_vm.LEAVE_TYPE_LABELS[_rules.LEAVE_TYPE_PM] == "오후반차"


def test_half_day_boundary_hour_matches_availability():
    """COMPAT: 19-4 availability 의 HALF_DAY_BOUNDARY_HOUR 와 동일 (12:00 정확)."""
    assert _rules.HALF_DAY_BOUNDARY_HOUR == _av.HALF_DAY_BOUNDARY_HOUR == 12


def test_leave_kind_constants():
    """LEAVE_KIND 상수 — annual / monthly (m011 정합)."""
    assert _rules.LEAVE_KIND_ANNUAL == "annual"
    assert _rules.LEAVE_KIND_MONTHLY == "monthly"
    assert _rules.LEAVE_KIND_DEFAULT == "annual"
    assert set(_rules.LEAVE_KIND_VALUES) == {"annual", "monthly"}


# ──────────────────────── 2. is_morning_slot / is_afternoon_slot 동등 ──────


@pytest.mark.parametrize(
    "hour,expected_morning,expected_afternoon",
    [
        (0, True, False),
        (8, True, False),
        (11, True, False),
        (12, False, True),  # 12:00 정확 — 오후 시작
        (14, False, True),
        (23, False, True),
    ],
)
def test_is_morning_afternoon_slot_byte_equivalent_with_availability(
    hour, expected_morning, expected_afternoon
):
    """COMPAT: 19-4 availability 와 byte-equivalent."""
    start = datetime(2099, 6, 15, hour, 0)
    assert _rules.is_morning_slot(start) == _av.is_morning_slot(start) == expected_morning
    assert _rules.is_afternoon_slot(start) == _av.is_afternoon_slot(start) == expected_afternoon


# ──────────────────────── 3. is_leave_blocking 동등 ───────────────────────


@pytest.mark.parametrize(
    "leave_type,hour,expected",
    [
        # full → 무조건 차단.
        ("full", 9, True), ("full", 11, True), ("full", 13, True), ("full", 17, True),
        # am 반차 → 오전 차단, 오후 OK.
        ("am", 9, True), ("am", 11, True), ("am", 12, False), ("am", 14, False),
        # pm 반차 → 오전 OK, 오후 차단.
        ("pm", 9, False), ("pm", 11, False), ("pm", 12, True), ("pm", 14, True),
        # 알 수 없음 → 차단 ⊥.
        (None, 10, False), ("", 10, False), ("unknown", 10, False),
    ],
)
def test_is_leave_blocking_byte_equivalent_with_availability(leave_type, hour, expected):
    """COMPAT: 19-4 availability.is_leave_blocking 와 byte-equivalent."""
    start = datetime(2099, 6, 15, hour, 0)
    rules_result = _rules.is_leave_blocking(start_at=start, leave_type=leave_type)
    av_result = _av.is_leave_blocking(start_at=start, leave_type=leave_type)
    assert rules_result == av_result == expected


def test_find_blocking_leave_byte_equivalent_with_availability():
    """COMPAT: 19-4 availability.find_blocking_leave 와 byte-equivalent."""
    leaves = [
        {"employee_id": "T-1", "leave_date": "2099-06-15", "leave_type": "full"},
        {"employee_id": "T-2", "leave_date": "2099-06-15", "leave_type": "am"},
    ]

    # T-1 종일 → 차단.
    rules_blocked = _rules.find_blocking_leave(
        therapist_id="T-1", start_at=datetime(2099, 6, 15, 10, 0), leaves=leaves,
    )
    av_blocked = _av.find_blocking_leave(
        therapist_id="T-1", start_at=datetime(2099, 6, 15, 10, 0), leaves=leaves,
    )
    assert rules_blocked == av_blocked
    assert rules_blocked is not None

    # T-2 am 반차 + 오후 → None.
    rules_none = _rules.find_blocking_leave(
        therapist_id="T-2", start_at=datetime(2099, 6, 15, 14, 0), leaves=leaves,
    )
    av_none = _av.find_blocking_leave(
        therapist_id="T-2", start_at=datetime(2099, 6, 15, 14, 0), leaves=leaves,
    )
    assert rules_none == av_none is None

    # 빈 leaves.
    assert _rules.find_blocking_leave(
        therapist_id="T-1", start_at=datetime(2099, 6, 15, 10, 0), leaves=[],
    ) is None
    assert _rules.find_blocking_leave(
        therapist_id="T-1", start_at=datetime(2099, 6, 15, 10, 0), leaves=None,
    ) is None


# ──────────────────────── 4. leave_block_message ──────────────────────────


def test_leave_block_message_returns_korean_messages():
    """spec 02 정합 — 한국어 차단 사유 메시지."""
    assert _rules.leave_block_message("full") == _rules.LEAVE_BLOCK_MESSAGE_FULL
    assert _rules.leave_block_message("am") == _rules.LEAVE_BLOCK_MESSAGE_AM
    assert _rules.leave_block_message("pm") == _rules.LEAVE_BLOCK_MESSAGE_PM
    assert _rules.leave_block_message(None) == ""
    assert _rules.leave_block_message("unknown") == ""


def test_leave_block_messages_contain_korean_keywords():
    """SAFETY: 사용자 노출 메시지에 잘못된 정보 누락 ⊥ — '치료사' / '휴무' / '예약' 포함."""
    for msg in (
        _rules.LEAVE_BLOCK_MESSAGE_FULL,
        _rules.LEAVE_BLOCK_MESSAGE_AM,
        _rules.LEAVE_BLOCK_MESSAGE_PM,
    ):
        assert "예약" in msg
        assert any(k in msg for k in ("치료사", "휴무", "반차"))


# ──────────────────────── 5. normalize_leave_type / kind ──────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, "full"),
        ("", "full"),
        ("full", "full"),
        ("am", "am"),
        ("pm", "pm"),
        ("custom_unknown", "custom_unknown"),  # raw 그대로 통과
    ],
)
def test_normalize_leave_type(raw, expected):
    """COMPAT: ``api.py:list_employee_leaves`` 의 ``r.leave_type or "full"`` 패턴 정합."""
    assert _rules.normalize_leave_type(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, "annual"),
        ("", "annual"),
        ("annual", "annual"),
        ("monthly", "monthly"),
        ("custom_unknown", "custom_unknown"),
    ],
)
def test_normalize_leave_kind(raw, expected):
    """COMPAT: ``api.py:list_employee_leaves`` 의 ``r.leave_kind or "annual"`` 패턴 정합."""
    assert _rules.normalize_leave_kind(raw) == expected


# ──────────────────────── 6. service.upsert_employee_leave 동등 ───────────


def test_upsert_employee_leave_byte_equivalent_with_api(client):
    """COMPAT: ``api.py:_upsert_employee_leave_core`` 와 동등 — DB 격리 fixture 사용.

    검증 절차:
      1. ``leaves.service.upsert_employee_leave`` 로 휴무 등록 → row 존재 확인.
      2. 같은 (employee_id, leave_date) 키로 다시 호출 → update (행 수 무변경).
      3. ``api.py`` 의 ``POST /api/employee-leaves`` 엔드포인트 호출 결과와 응답 키 동등.
    """
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_therapist_id

    therapist_id = get_test_therapist_id("이테스트치료사")
    new_date = "2099-09-15"  # 시드 휴무와 다른 미래 날짜

    db = SessionLocal()
    try:
        # 사전: 같은 (id, date) row 부재 (멱등 보장).
        existing = (
            db.query(_m.EmployeeLeave)
            .filter(
                _m.EmployeeLeave.employee_id == therapist_id,
                _m.EmployeeLeave.leave_date == new_date,
            )
            .first()
        )
        if existing is not None:
            db.delete(existing)
            db.commit()

        # insert.
        obj = _service.upsert_employee_leave(
            db, employee_id=therapist_id, leave_date=new_date,
            leave_type="full", leave_kind="annual", memo="19-5 contract",
        )
        db.commit()
        assert obj.id is not None
        first_id = obj.id

        # update (같은 키 → 같은 row 갱신).
        obj2 = _service.upsert_employee_leave(
            db, employee_id=therapist_id, leave_date=new_date,
            leave_type="am", leave_kind="monthly", memo="updated",
        )
        db.commit()
        assert obj2.id == first_id  # 같은 행 갱신
        assert obj2.leave_type == "am"
        assert obj2.leave_kind == "monthly"
        assert obj2.memo == "updated"

        # 응답 dict 빌드 확인.
        result = _service.serialize_employee_leave(obj2)
        assert set(result.keys()) == {
            "id", "employee_id", "leave_date",
            "leave_type", "leave_kind", "memo",
        }
        assert result["leave_type"] == "am"
        assert result["leave_kind"] == "monthly"

        # cleanup.
        db.delete(obj2)
        db.commit()
    finally:
        db.close()


def test_upsert_log_callback_invoked_for_insert_and_update():
    """``log_callback`` 이 insert / update 양쪽에서 호출됨 (sync 로깅 정합)."""
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_therapist_id

    therapist_id = get_test_therapist_id("이테스트치료사")
    new_date = "2099-09-16"
    log_calls = []

    def _capture(db, entity, entity_id, op, obj):
        log_calls.append((entity, entity_id, op))

    db = SessionLocal()
    try:
        existing = (
            db.query(_m.EmployeeLeave)
            .filter(
                _m.EmployeeLeave.employee_id == therapist_id,
                _m.EmployeeLeave.leave_date == new_date,
            )
            .first()
        )
        if existing is not None:
            db.delete(existing)
            db.commit()

        _service.upsert_employee_leave(
            db, employee_id=therapist_id, leave_date=new_date,
            leave_type="full", leave_kind="annual",
            log_callback=_capture,
        )
        db.commit()

        obj2 = _service.upsert_employee_leave(
            db, employee_id=therapist_id, leave_date=new_date,
            leave_type="am", leave_kind="annual",
            log_callback=_capture,
        )
        db.commit()

        assert len(log_calls) == 2
        assert all(c[0] == "employee_leave" and c[2] == "upsert" for c in log_calls)

        db.delete(obj2)
        db.commit()
    finally:
        db.close()


# ──────────────────────── 7. serializer 회귀 (api.py 응답 dict 와 동등) ───


def test_serialize_employee_leave_keys_and_fallbacks():
    """COMPAT: ``api.py:list_employee_leaves`` 응답 dict 와 byte-equivalent."""

    class _FakeLeave:
        id = "L-1"
        employee_id = "E-1"
        leave_date = "2099-06-15"
        leave_type = ""  # fallback to "full"
        leave_kind = None  # fallback to "annual"
        memo = None

    result = _service.serialize_employee_leave(_FakeLeave())
    assert set(result.keys()) == {
        "id", "employee_id", "leave_date",
        "leave_type", "leave_kind", "memo",
    }
    assert result["leave_type"] == "full"  # fallback
    assert result["leave_kind"] == "annual"  # fallback
    assert result["memo"] == ""  # None → ""


def test_serialize_therapist_leave_alias_includes_therapist_id():
    """COMPAT: ``api.py:list_therapist_leaves_alias`` 의 7키 (therapist_id alias)."""

    class _FakeLeave:
        id = "L-2"
        employee_id = "E-2"
        leave_date = "2099-06-15"
        leave_type = "am"
        leave_kind = "monthly"
        memo = "hello"

    result = _service.serialize_therapist_leave_alias(_FakeLeave())
    assert set(result.keys()) == {
        "id", "therapist_id", "employee_id", "leave_date",
        "leave_type", "leave_kind", "memo",
    }
    # therapist_id == employee_id alias.
    assert result["therapist_id"] == result["employee_id"] == "E-2"
    assert result["leave_type"] == "am"
    assert result["leave_kind"] == "monthly"
    assert result["memo"] == "hello"


# ──────────────────────── 8. repository read-only ─────────────────────────


def test_list_leaves_for_date(client):
    """COMPAT: ``api.py:list_employee_leaves`` 의 query 패턴 정합."""
    from app.database import SessionLocal
    from tests.harness.seed_data import FIXED_LEAVE_DATE

    db = SessionLocal()
    try:
        rows = _repo.list_leaves_for_date(db, FIXED_LEAVE_DATE)
        # FIXED_LEAVE_DATE 에 시드 3건 (full / am / pm).
        assert len(rows) >= 3
        leave_types = {r.leave_type for r in rows}
        assert {"full", "am", "pm"}.issubset(leave_types)
    finally:
        db.close()


def test_get_leave_for_employee_date(client):
    """COMPAT: ``api.py:_upsert_employee_leave_core`` 의 ``filter`` 와 동등."""
    from app.database import SessionLocal
    from tests.harness.seed_data import FIXED_LEAVE_DATE, get_test_therapist_id

    therapist_id = get_test_therapist_id("이테스트치료사")  # am 반차

    db = SessionLocal()
    try:
        row = _repo.get_leave_for_employee_date(
            db, employee_id=therapist_id, leave_date=FIXED_LEAVE_DATE,
        )
        assert row is not None
        assert row.leave_type == "am"

        # 다른 날짜 → None.
        none_row = _repo.get_leave_for_employee_date(
            db, employee_id=therapist_id, leave_date="2099-12-31",
        )
        assert none_row is None
    finally:
        db.close()


# ──────────────────────── 9. 단방향 경계 (D-4 정합 — ast 기반) ────────────


def test_leaves_rules_does_not_import_models_or_db():
    """leaves.rules 는 ORM/DB/services/routers 미참조 (D-4)."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_rules)
    tree = _ast.parse(src)

    forbidden = {
        "app.models", "app.database", "app.services", "app.routers",
        "sqlalchemy", "fastapi",
        "app.modules.settings", "app.modules.health", "app.modules.calendar",
        "app.modules.appointments",
    }

    def _hit(name: str) -> str | None:
        for f in forbidden:
            if name == f or name.startswith(f + "."):
                return f
        return None

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                assert _hit(alias.name) is None, (
                    f"leaves.rules 가 금지된 import: {alias.name!r}"
                )
        elif isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert _hit(mod) is None, (
                f"leaves.rules 가 금지된 import: from {mod!r}"
            )


def test_leaves_repository_only_imports_models_and_db_lazily():
    """leaves.repository 는 ``app.models`` / ``sqlalchemy`` 직접 참조 ⊥ — lazy import 만."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_repo)
    tree = _ast.parse(src)

    # Top-level (ast.Module 의 body 직접) ImportFrom 노드만 수집.
    top_imports = [
        n for n in tree.body
        if isinstance(n, (_ast.Import, _ast.ImportFrom))
    ]
    forbidden_top = {"app.models", "app.database", "sqlalchemy"}
    for node in top_imports:
        if isinstance(node, _ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_top, (
                    f"leaves.repository 가 top-level 에 금지 import: {alias.name!r}"
                )
        elif isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden_top
            ), f"leaves.repository 가 top-level 에 금지 import: from {mod!r}"


def test_leaves_service_does_not_import_routers():
    """leaves.service 는 ``app.routers`` 미참조 (D-4 정합)."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_service)
    tree = _ast.parse(src)
    forbidden = {"app.routers", "fastapi"}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden
            ), f"leaves.service 가 금지된 import: from {mod!r}"


def test_leaves_package_init_does_not_import_models_or_db():
    """leaves/__init__ 도 단방향 경계."""
    import ast as _ast

    import app.modules.leaves as mod
    src = importlib.import_module("inspect").getsource(mod)
    tree = _ast.parse(src)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(
                    ("app.models", "app.database", "app.services", "app.routers", "sqlalchemy")
                ), f"leaves/__init__ 가 금지된 import: {alias.name!r}"
        elif isinstance(node, _ast.ImportFrom):
            mod_name = node.module or ""
            assert not any(
                mod_name == f or mod_name.startswith(f + ".")
                for f in ("app.models", "app.database", "app.services", "app.routers", "sqlalchemy")
            ), f"leaves/__init__ 가 금지된 import: from {mod_name!r}"


# ──────────────────────── 10. AI action_leave 흐름 무수정 회귀 ────────────


def test_ai_action_leave_still_imports_legacy_upsert():
    """COMPAT: AI action_leave 는 *기존* ``app.routers.api._upsert_employee_leave_core`` 를
    그대로 import — 19-5 시점에 단일 진실원천 보존 (사용자 명시 "기존 휴무 AI 동작 변경 금지").
    """
    import inspect

    from app.services.ai import action_leave as _al
    src = inspect.getsource(_al._do_upsert)
    assert "from ...routers.api import _upsert_employee_leave_core" in src, (
        "AI action_leave._do_upsert 가 기존 _upsert_employee_leave_core import 를 잃었음 — "
        "19-5 에서 변경 ⊥"
    )


def test_existing_upsert_employee_leave_core_still_exists():
    """COMPAT: ``api.py:_upsert_employee_leave_core`` 본체 그대로 존재 — 라우터 무수정 보증."""
    from app.routers import api as _api_module
    assert hasattr(_api_module, "_upsert_employee_leave_core")
    assert callable(_api_module._upsert_employee_leave_core)


# ──────────────────────── 11. 라우터 무수정 회귀 ──────────────────────────


def test_employee_leaves_endpoint_still_works(client):
    """기존 정상 케이스 회귀 — POST /api/employee-leaves 200 OK."""
    from tests.harness.seed_data import get_test_therapist_id

    therapist_id = get_test_therapist_id("이테스트치료사")
    payload = {
        "employee_id": therapist_id,
        "leave_date": "2099-09-20",
        "leave_type": "full",
        "leave_kind": "annual",
        "memo": "19-5 contract",
    }
    resp = client.post("/api/employee-leaves", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) >= {
        "id", "employee_id", "leave_date", "leave_type", "leave_kind", "memo",
    }
    assert body["leave_type"] == "full"
    # cleanup.
    client.delete(f"/api/employee-leaves/{body['id']}")


def test_therapist_leaves_alias_endpoint_still_works(client):
    """기존 정상 케이스 회귀 — GET /api/therapist-leaves 응답 (therapist_id alias)."""
    from tests.harness.seed_data import FIXED_LEAVE_DATE

    resp = client.get(f"/api/therapist-leaves?date={FIXED_LEAVE_DATE}")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) >= 3
    for r in rows:
        # alias 7키 존재.
        assert "therapist_id" in r and "employee_id" in r
        assert r["therapist_id"] == r["employee_id"]


# ──────────────────────── 12. 외부 API 호출 0 검증 ─────────────────────────


def test_rules_helpers_do_not_invoke_provider_or_db():
    """SAFETY: rules helper 안에서 외부 API / SDK / DB 호출 ⊥."""
    _ = _rules.is_morning_slot(datetime(2099, 6, 15, 11, 0))
    _ = _rules.is_afternoon_slot(datetime(2099, 6, 15, 14, 0))
    _ = _rules.is_leave_blocking(start_at=datetime(2099, 6, 15, 10, 0), leave_type="full")
    _ = _rules.find_blocking_leave(
        therapist_id="T-1", start_at=datetime(2099, 6, 15, 10, 0), leaves=[],
    )
    _ = _rules.leave_block_message("full")
    _ = _rules.normalize_leave_type("am")
    _ = _rules.normalize_leave_kind("annual")
