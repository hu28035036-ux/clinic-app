"""19-8 therapists 치료사 / 직원 도메인 분리 contract.

검증 범위 (19-8 세션 지시문 정합):
  1. ``app.modules.therapists.rules`` 의 ROLE_DOCTOR / ROLE_THERAPIST / ROLES 가
     ``app.models.constants`` 와 동등 (단일 진실원천).
  2. 역할 판정 helper (``is_therapist_role`` / ``is_doctor_role`` / ``is_valid_role``) 정합.
  3. ``DEFAULT_THERAPIST_COLOR`` 가 19-3 calendar.view_models 와 동일 값 (``"#9CA3AF"``).
  4. ``therapist_color_or_default`` 가 19-3 ``calendar.view_models.therapist_color`` 와
     byte-equivalent.
  5. ``UNASSIGNED_SENTINEL`` / ``UNASSIGNED_LABEL`` 이 ``api.py:3495`` / ``api.py:3528``
     의 inline literal 정합.
  6. ``therapists.repository`` read-only helper 가 ``api.py:list_employees`` /
     ``list_therapists_alias`` 등 query 패턴과 동등 (실제 DB 격리 fixture 사용).
  7. ``therapists.service.serialize_employee`` 가 ``api.py:_serialize_employee`` 와
     byte-equivalent (10키 dict).
  8. ``serialize_employee`` 의 응답 키가 ``GET /api/employees`` 응답과 동일 (계약).
  9. ``build_employee_name_map`` / ``build_employee_color_map`` 의 미배정 sentinel 합산.
 10. ``build_therapist_resource_view`` 가 19-3 calendar.view_models.employee_to_resource_view
     와 동일 결과.
 11. ``next_sort_order_for_role`` 가 ``api.py:create_employee`` 의 ``count + 1`` 패턴 정합.
 12. modules.therapists 가 ``app.routers`` 미참조 — 단방향 경계 (D-4).
     ``app.models`` / ``app.modules.calendar`` 는 *조건부* 참조 가능 (rules.py 가
     view_models 의 색상 상수 re-export, repository / service 가 ORM lazy import).
 13. doctors / medical_staff 전용 모듈을 새로 만들지 않음 (현재 기능 부재 확인).
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from app.models import constants as _const
from app.modules.calendar import view_models as _cal_vm
from app.modules.therapists import repository as _repo
from app.modules.therapists import rules as _rules
from app.modules.therapists import service as _service

# ──────────────────────── 1. ROLE 상수 정합 ────────────────────────


def test_role_constants_match_models_constants():
    """COMPAT: app.models.constants 와 byte-equivalent."""
    assert _rules.ROLE_DOCTOR == _const.ROLE_DOCTOR == "doctor"
    assert _rules.ROLE_THERAPIST == _const.ROLE_THERAPIST == "therapist"
    assert set(_rules.ROLES) == set(_const.ROLES) == {"doctor", "therapist"}


def test_roles_tuple_is_immutable():
    """ROLES 는 ``tuple`` 로 노출 — 외부 수정 ⊥."""
    assert isinstance(_rules.ROLES, tuple)


# ──────────────────────── 2. 역할 판정 helper ────────────────────────


@pytest.mark.parametrize(
    "role,is_th,is_dr,is_valid",
    [
        ("therapist", True, False, True),
        ("doctor", False, True, True),
        ("", False, False, False),
        (None, False, False, False),
        ("admin", False, False, False),
        ("nurse", False, False, False),
    ],
)
def test_role_predicates(role, is_th, is_dr, is_valid):
    """COMPAT: api.py 의 역할 분기 정합."""
    assert _rules.is_therapist_role(role) is is_th
    assert _rules.is_doctor_role(role) is is_dr
    assert _rules.is_valid_role(role) is is_valid


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, "therapist"),
        ("", "therapist"),
        ("therapist", "therapist"),
        ("doctor", "doctor"),
        ("custom_unknown", "custom_unknown"),  # raw 그대로 통과
    ],
)
def test_normalize_role(raw, expected):
    """COMPAT: m001 ``role`` 컬럼 default ``"therapist"`` 정합."""
    assert _rules.normalize_role(raw) == expected


# ──────────────────────── 3. 색상 상수 정합 (19-3 단일 진실원천) ─────────────


def test_default_therapist_color_matches_calendar_view_models():
    """COMPAT: 19-3 calendar.view_models.UNASSIGNED_THERAPIST_COLOR 와 동일 값."""
    assert _rules.DEFAULT_THERAPIST_COLOR == _cal_vm.UNASSIGNED_THERAPIST_COLOR
    assert _rules.DEFAULT_THERAPIST_COLOR == "#9CA3AF"


# ──────────────────────── 4. therapist_color_or_default 동등 ─────────────────


@pytest.mark.parametrize(
    "color",
    [None, "", "#FF0000", "#9CA3AF", "#abc", "rgb(0,0,0)"],
)
def test_therapist_color_or_default_byte_equivalent_with_view_models(color):
    """COMPAT: 19-3 ``calendar.view_models.therapist_color`` 와 byte-equivalent."""
    rules_result = _rules.therapist_color_or_default(color)
    vm_result = _cal_vm.therapist_color(color)
    assert rules_result == vm_result


# ──────────────────────── 5. 활성 / 권한 정규화 ────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [(True, True), (False, False), (1, True), (0, False), (None, False)],
)
def test_is_active_employee(value, expected):
    """COMPAT: ``api.py:_serialize_employee`` 의 ``bool(e.active)`` 정합."""
    assert _rules.is_active_employee(value) is expected


@pytest.mark.parametrize(
    "value,expected",
    [(True, True), (False, False), (1, True), (0, False), (None, False)],
)
def test_can_handle_eswt(value, expected):
    """COMPAT: ``api.py:_serialize_employee`` 의 ``bool(e.can_eswt)`` 정합."""
    assert _rules.can_handle_eswt(value) is expected


@pytest.mark.parametrize(
    "value,expected",
    [(True, True), (False, False), (1, True), (0, False), (None, False)],
)
def test_can_handle_manual(value, expected):
    """COMPAT: ``api.py:_serialize_employee`` 의 ``bool(e.can_manual)`` 정합."""
    assert _rules.can_handle_manual(value) is expected


# ──────────────────────── 6. 미배정 sentinel ────────────────────────


def test_unassigned_sentinel_constants():
    """COMPAT: ``api.py:3495`` (``a.therapist_id or "__none__"``) /
    ``api.py:3528`` (``therapists["__none__"] = "미배정"``) 정합."""
    assert _rules.UNASSIGNED_SENTINEL == "__none__"
    assert _rules.UNASSIGNED_LABEL == "미배정"


@pytest.mark.parametrize(
    "tid,expected",
    [
        (None, True),
        ("", True),
        ("__none__", True),
        ("emp-1", False),
        ("any-other-id", False),
    ],
)
def test_is_unassigned(tid, expected):
    """COMPAT: ``api.py`` 통계 미배정 분기 정합."""
    assert _rules.is_unassigned(tid) is expected


# ──────────────────────── 7. repository — DB 격리 fixture 사용 ───────────────


def test_list_all_employees_includes_seed_therapists(client):
    """COMPAT: ``api.py:list_employees`` 와 동등 — 시드된 3명 치료사 포함."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_all_employees(db)
        names = {e.name for e in rows}
        assert "김테스트치료사" in names
        assert "이테스트치료사" in names
        assert "박테스트치료사" in names
    finally:
        db.close()


def test_list_all_employees_role_filter(client):
    """COMPAT: ``api.py:list_employees`` ``role`` 쿼리 파라미터 정합."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        therapists_only = _repo.list_all_employees(db, role="therapist")
        assert all(_service.employee_can_manual(e) for e in therapists_only)
    finally:
        db.close()


def test_list_therapists_returns_only_therapist_role(client):
    """COMPAT: ``api.py:list_therapists_alias`` 와 동등 — role=therapist 만."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_therapists(db)
        assert all(_service.employee_can_manual(e) for e in rows)
        names = {e.name for e in rows}
        assert "김테스트치료사" in names
    finally:
        db.close()


def test_list_doctors_returns_only_doctor_role(client):
    """COMPAT: ``api.py:3525`` ``role == "doctor"`` query 정합.

    NOTE: 시드에는 의사가 없으므로 빈 리스트가 정상.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_doctors(db)
        assert all(_service.employee_can_doctor_treatment(e) for e in rows)
    finally:
        db.close()


def test_get_employee_by_id_round_trip(client):
    """COMPAT: ``api.py:update_employee`` ``db.get(Employee, eid)`` 정합."""
    from app.database import SessionLocal
    from tests.harness.seed_data import get_test_therapist_id

    tid = get_test_therapist_id("김테스트치료사")

    db = SessionLocal()
    try:
        e = _repo.get_employee_by_id(db, tid)
        assert e is not None
        assert e.id == tid
        assert e.name == "김테스트치료사"
    finally:
        db.close()


def test_get_employee_by_id_returns_none_for_missing(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        assert _repo.get_employee_by_id(db, "non-existent-id") is None
    finally:
        db.close()


def test_list_therapists_for_manual_scheduler_filters(client):
    """COMPAT: ``api.py:4364~4369`` 정합 — role=therapist + active + can_manual."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_therapists_for_manual_scheduler(db)
        for e in rows:
            assert bool(e.active) is True
            assert _service.employee_can_manual(e) is True
    finally:
        db.close()


def test_list_active_therapists_filters(client):
    """COMPAT: ``api.py:3783~3786`` 정합 — role=therapist + active=True."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_active_therapists(db)
        for e in rows:
            assert bool(e.active) is True
            assert _service.employee_can_manual(e) is True
    finally:
        db.close()


def test_get_employees_by_ids_with_in_filter(client):
    """COMPAT: ``api.py:1552`` ``in_(emp_ids)`` 정합."""
    from app.database import SessionLocal
    from tests.harness.seed_data import get_test_therapist_id

    t1 = get_test_therapist_id("김테스트치료사")
    t2 = get_test_therapist_id("이테스트치료사")

    db = SessionLocal()
    try:
        rows = _repo.get_employees_by_ids(db, [t1, t2])
        ids = {e.id for e in rows}
        assert ids == {t1, t2}

        # 빈 리스트는 빈 결과 반환 (in_([]) 호출 회피).
        empty_rows = _repo.get_employees_by_ids(db, [])
        assert empty_rows == []
    finally:
        db.close()


def test_count_employees_by_role(client):
    """COMPAT: ``api.py:create_employee`` ``count()`` 정합."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        therapist_count = _repo.count_employees_by_role(db, "therapist")
        # 시드 3명 이상.
        assert therapist_count >= 3
    finally:
        db.close()


# ──────────────────────── 8. service — serialize_employee 동등 ───────────────


def test_serialize_employee_byte_equivalent_with_api(client):
    """COMPAT: ``api.py:_serialize_employee`` 의 12키 dict 와 byte-equivalent.

    20-3-2 (post-19-P / F-11): 11키 + permission_level = 12키.
    """
    from app.database import SessionLocal
    from app.routers.api import _serialize_employee
    from tests.harness.seed_data import get_test_therapist_id

    tid = get_test_therapist_id("김테스트치료사")

    db = SessionLocal()
    try:
        e = _repo.get_employee_by_id(db, tid)
        assert e is not None

        api_dict = _serialize_employee(e)
        service_dict = _service.serialize_employee(e)

        assert api_dict == service_dict
        # role 공개 제거 + 과/권한 계약 정합.
        assert set(service_dict.keys()) == {
            "id", "name", "category_id", "category_name", "color", "active",
            "birth_date", "phone", "hire_date",
            "can_doctor_treatment", "can_eswt", "can_manual",
            "can_doctor_treatment_override",
            "can_eswt_override", "can_manual_override",
            "treatment_override_enabled", "treatment_ids",
            "sort_order",
            # 20-3-2 (post-19-P / F-11)
            "permission_level",
        }
    finally:
        db.close()


def test_serialize_employees_list(client):
    """COMPAT: ``api.py:list_employees`` 의 list comprehension 정합."""
    from app.database import SessionLocal
    from app.routers.api import _serialize_employee

    db = SessionLocal()
    try:
        rows = _repo.list_therapists(db)
        api_list = [_serialize_employee(e) for e in rows]
        service_list = _service.serialize_employees(rows)
        assert api_list == service_list
    finally:
        db.close()


def test_get_employees_endpoint_keys_match_serialize_employee(client):
    """API 계약: ``GET /api/employees`` 응답이 serialize_employee 와 동일 키.

    응답 회귀 보호 — 본 테스트가 fail 하면 라우터 응답 dict 가 임의 변경됨.
    """
    r = client.get("/api/employees?role=therapist")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    expected_keys = {
        "id", "name", "category_id", "category_name", "color", "active",
        "birth_date", "phone", "hire_date",
        "can_doctor_treatment", "can_eswt", "can_manual",
        "can_doctor_treatment_override",
        "can_eswt_override", "can_manual_override",
        "treatment_override_enabled", "treatment_ids",
        "sort_order",
        # 20-3-2 (post-19-P / F-11)
        "permission_level",
    }
    for item in items:
        assert set(item.keys()) == expected_keys


# ──────────────────────── 9. id → name / color 매핑 ────────────────────────


def test_build_employee_name_map_includes_unassigned(client):
    """COMPAT: ``api.py:3527 + 3528`` (``id → name`` + ``"__none__" = "미배정"``) 정합."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        therapists = _repo.list_therapists(db)
        name_map = _service.build_employee_name_map(therapists, include_unassigned=True)
        assert _rules.UNASSIGNED_SENTINEL in name_map
        assert name_map[_rules.UNASSIGNED_SENTINEL] == _rules.UNASSIGNED_LABEL
        for e in therapists:
            assert name_map[e.id] == e.name
    finally:
        db.close()


def test_build_employee_name_map_without_unassigned(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        therapists = _repo.list_therapists(db)
        name_map = _service.build_employee_name_map(therapists, include_unassigned=False)
        assert _rules.UNASSIGNED_SENTINEL not in name_map
    finally:
        db.close()


def test_build_employee_color_map_applies_fallback(client):
    """COMPAT: ``api.py:3789`` (``t.color or "#9CA3AF"``) 정합."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        therapists = _repo.list_therapists(db)
        color_map = _service.build_employee_color_map(therapists, include_unassigned=True)
        for e in therapists:
            expected = e.color or _rules.DEFAULT_THERAPIST_COLOR
            assert color_map[e.id] == expected
        assert color_map[_rules.UNASSIGNED_SENTINEL] == _rules.DEFAULT_THERAPIST_COLOR
    finally:
        db.close()


# ──────────────────────── 10. resource view 동등 (19-3) ──────────────────────


def test_build_therapist_resource_view_matches_calendar_view_models(client):
    """COMPAT: 19-3 ``calendar.view_models.employee_to_resource_view`` 와 동일 결과."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_therapists(db)
        for e in rows:
            cal_view = _cal_vm.employee_to_resource_view(
                employee_id=e.id, name=e.name, color=e.color,
            )
            therapist_view = _service.build_therapist_resource_view(e)
            assert cal_view == therapist_view
            assert set(therapist_view.keys()) == {"id", "name", "color"}
    finally:
        db.close()


def test_build_therapist_resource_views_list(client):
    """resource view list 빌더 — 도수치료 표 / 캘린더 lane 표시용."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        rows = _repo.list_therapists(db)
        views = _service.build_therapist_resource_views(rows)
        assert len(views) == len(rows)
        for v, e in zip(views, rows, strict=True):
            assert v["id"] == e.id
            assert v["name"] == e.name
    finally:
        db.close()


# ──────────────────────── 11. next_sort_order_for_role ───────────────────────


@pytest.mark.parametrize(
    "current_count,expected",
    [(0, 1), (1, 2), (5, 6), (99, 100)],
)
def test_next_sort_order_for_role(current_count, expected):
    """COMPAT: ``api.py:create_employee`` (line 1038~1042) 의 ``count + 1`` 정합."""
    assert _service.next_sort_order_for_role(current_count_for_role=current_count) == expected


# ──────────────────────── 12. 단방향 경계 (D-4) ────────────────────────


def test_rules_does_not_import_routers():
    """rules.py 가 ``app.routers`` 미참조 — 단방향 경계."""
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src
    assert "from app.routers" not in src


def test_rules_does_not_import_sqlalchemy():
    """rules.py 가 SQLAlchemy / DB 미참조 — 순수 helper."""
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    assert "sqlalchemy" not in src.lower()
    assert "from app.database" not in src
    assert "from app.models import models" not in src


def test_repository_does_not_import_routers():
    src = Path(_repo.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_service_does_not_import_routers():
    src = Path(_service.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_repository_uses_lazy_import_for_models():
    """repository.py 가 ``app.models`` 을 함수 안 lazy import — 순환참조 회피."""
    src = Path(_repo.__file__).read_text(encoding="utf-8")
    # top-level ``from app.models`` 부재 (re 모듈 / typing 만).
    for line in src.splitlines():
        if line.startswith("from app.models"):
            pytest.fail(f"top-level app.models import 발견: {line}")


def test_modules_therapists_importable():
    """app.modules.therapists 패키지 import 가능."""
    import app.modules.therapists  # noqa: F401
    import app.modules.therapists.repository  # noqa: F401
    import app.modules.therapists.rules  # noqa: F401
    import app.modules.therapists.service  # noqa: F401


# ──────────────────────── 13. doctors / medical_staff 현재 기능 부재 확인 ─────


def test_no_medical_staff_module_created():
    """19-8 시점 단언 갱신 (post-19-P / 20-3-3 F-1 (c) 정합).

    NOTE: 19-8 시점에는 doctors / medical_staff 모듈 부재였으나, post-19-P /
    20-3-3 에서 사용자 §5-7 (c) 결정으로 ``app/modules/doctors/`` *가벼운
    의사만* 신설됨. medical_staff 통합 모듈은 여전히 부재.
    """
    from pathlib import Path

    modules_dir = Path(_rules.__file__).parent.parent
    # 20-3-3 F-1 (c) — doctors 신설됨
    assert (modules_dir / "doctors").exists()
    # medical_staff 통합 모듈은 여전히 부재 (post-(c) 후속 결정)
    assert not (modules_dir / "medical_staff").exists()


def test_doctors_endpoint_added_after_20_3_3(client):
    """``/api/doctors`` 엔드포인트가 20-3-3 F-1 (c) 에서 신설됨.

    NOTE: 19-8 시점에는 부재 (404/405). post-19-P / 20-3-3 신설 후 200 응답.
    Employee.role="doctor" 분기는 별개로 보존.
    """
    r = client.get("/api/doctors")
    assert r.status_code == 200  # 20-3-3 F-1 (c) 도입


def test_existing_employee_role_doctor_endpoint_still_works(client):
    """``GET /api/employees?role=doctor`` 가 정상 응답 (기존 흐름 유지)."""
    r = client.get("/api/employees?role=doctor")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # 시드에는 진료항목 처리 가능 직원이 없으므로 빈 리스트 또는 해당 권한 직원만.
    for item in items:
        assert item["can_doctor_treatment"] is True


# ──────────────────────── 14. 라우터 함수 시그니처 무수정 ────────────────────


def test_serialize_employee_router_signature_unchanged():
    """``api.py:_serialize_employee`` 의 시그니처 유지 — 라우터 무수정 확인."""
    from app.routers.api import _serialize_employee

    sig = inspect.signature(_serialize_employee)
    assert list(sig.parameters.keys()) == ["e"]


def test_list_employees_router_signature_unchanged():
    """``api.py:list_employees`` 의 query param 시그니처 유지."""
    from app.routers.api import list_employees

    sig = inspect.signature(list_employees)
    # role legacy filter / category_id / active / db 파라미터.
    assert "role" in sig.parameters
    assert "category_id" in sig.parameters
    assert "active" in sig.parameters
    assert "db" in sig.parameters


def test_list_therapists_alias_router_signature_unchanged():
    """``api.py:list_therapists_alias`` 의 시그니처 유지."""
    from app.routers.api import list_therapists_alias

    sig = inspect.signature(list_therapists_alias)
    # db 1 파라미터.
    assert "db" in sig.parameters


# ──────────────────────── 15. 기존 휴무 / 통계 흐름 영향 없음 ────────────────


def test_employee_leaves_endpoint_still_works(client):
    """``GET /api/employee-leaves`` 흐름 보존 (19-5 무수정)."""
    r = client.get("/api/employee-leaves")
    assert r.status_code == 200


def test_therapist_leaves_alias_endpoint_still_works(client):
    """``GET /api/therapist-leaves`` 흐름 보존 (19-5 무수정)."""
    r = client.get("/api/therapist-leaves")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    for item in items:
        # therapist_id 이중 키 (프론트 호환) 유지.
        assert "therapist_id" in item
        assert "employee_id" in item


def test_treatment_meta_endpoint_unchanged(client):
    """``GET /api/treatment-meta`` 의 doctor / therapist 분류 흐름 보존."""
    r = client.get("/api/treatment-meta")
    assert r.status_code == 200
    data = r.json()
    assert "doctor_treatments" in data
    assert "therapist_treatments" in data
    assert "manual_treatments" in data
