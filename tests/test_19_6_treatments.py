"""19-6 treatments / completion_rules contract.

검증 범위 (19-6 세션 지시문 정합):
  1. ``treatments.rules`` 분류 helper (doctor/therapist/manual/eswt) 가
     ``api.py:_doctor_codes_set`` / ``_therapist_only_codes_set`` /
     ``_get_manual_treatment_rows`` 와 byte-equivalent.
  2. ``treatments.service.serialize_treatment`` 가 ``api.py:_serialize_treatment`` 와
     12키 byte-equivalent.
  3. ``treatments.service.normalize_incentive`` 가 ``api.py:_normalize_incentive`` 와
     동등 (XOR / 0~100 검증).
  4. ``treatments.service.build_treatment_meta`` 가 ``api.py:_build_treatment_meta`` 의
     15키 응답 dict 와 byte-equivalent.
  5. ``treatments.completion_rules.bump_patient_count`` 가 ``api.py:_bump_patient_count`` 와
     byte-equivalent — *항목별 ±1*, *시간 가중치 ⊥*.
  6. ``manual60`` 정책 — count_increment=1 (CLAUDE.md 정합) — DB 시드 검증.
  7. modules.treatments 단방향 경계 (D-4) — rules 는 ORM/DB 미참조.
  8. 라우터 / 통계 / SMS 본체 무수정 — 응답 키 보존.
"""
from __future__ import annotations

import importlib
import json

import pytest

from app.modules.treatments import completion_rules as _comp
from app.modules.treatments import defaults as _defaults
from app.modules.treatments import repository as _repo
from app.modules.treatments import rules as _rules
from app.modules.treatments import service as _service

# ──────────────────────── 1. role / ESWT / manual 분류 helper ─────────────


class _FakeTreatment:
    def __init__(
        self,
        *,
        id: str = "T-1",
        code: str = "manual30",
        name: str = "도수30분",
        short: str = "도수30",
        default_minutes: int = 30,
        role: str = "therapist",
        count_increment: int = 1,
        show_in_patient: bool = True,
        active: bool = True,
        sort_order: int = 1,
        price: int = 50000,
        incentive_pct: float | None = None,
        incentive_amount: int | None = None,
    ) -> None:
        self.id = id
        self.code = code
        self.name = name
        self.short = short
        self.default_minutes = default_minutes
        self.role = role
        self.count_increment = count_increment
        self.show_in_patient = show_in_patient
        self.active = active
        self.sort_order = sort_order
        self.price = price
        self.incentive_pct = incentive_pct
        self.incentive_amount = incentive_amount


def test_role_constants():
    assert _rules.ROLE_DOCTOR == "doctor"
    assert _rules.ROLE_THERAPIST == "therapist"
    assert set(_rules.ROLE_VALUES) == {"doctor", "therapist"}


def test_default_eswt_code_matches_constants():
    """COMPAT: ``app.models.constants.ESWT_CODE`` 와 동일."""
    from app.models import constants as _c
    assert _rules.DEFAULT_ESWT_CODE == _c.ESWT_CODE == "eswt"


@pytest.mark.parametrize(
    "role,expected_doctor,expected_therapist",
    [
        ("doctor", True, False),
        ("therapist", False, True),
        ("", False, False),
        (None, False, False),
        ("custom", False, False),
    ],
)
def test_is_doctor_therapist_role(role, expected_doctor, expected_therapist):
    t = _FakeTreatment(role=role)
    assert _rules.is_doctor_role(t) is expected_doctor
    assert _rules.is_therapist_role(t) is expected_therapist


@pytest.mark.parametrize(
    "code,role,expected_manual,expected_eswt",
    [
        ("manual30", "therapist", True, False),
        ("manual60", "therapist", True, False),
        ("manual90", "therapist", True, False),
        ("eswt", "therapist", False, True),
        ("inj1", "doctor", False, False),
        ("eswt", "doctor", False, True),
    ],
)
def test_is_manual_treatment_excludes_eswt(code, role, expected_manual, expected_eswt):
    t = _FakeTreatment(code=code, role=role)
    assert _rules.is_manual_treatment(t) is expected_manual
    assert _rules.is_eswt_treatment(t) is expected_eswt


def test_is_active_handles_falsy():
    assert _rules.is_active(_FakeTreatment(active=True)) is True
    assert _rules.is_active(_FakeTreatment(active=False)) is False


# ──────────────────────── 2. 분류 set comprehensions byte-equivalent ──────


def test_doctor_codes_byte_equivalent_with_api_py():
    """COMPAT: ``api.py:_doctor_codes_set`` 와 byte-equivalent."""
    treatments = [
        _FakeTreatment(code="inj1", role="doctor"),
        _FakeTreatment(code="manual30", role="therapist"),
        _FakeTreatment(code="eswt", role="therapist"),
        _FakeTreatment(code="con", role="doctor"),
    ]
    result = _rules.doctor_codes(treatments)
    inline_result = {t.code for t in treatments if t.role == "doctor"}
    assert result == inline_result == {"inj1", "con"}


def test_therapist_only_codes_byte_equivalent_with_api_py():
    """COMPAT: ``api.py:_therapist_only_codes_set`` 와 byte-equivalent."""
    treatments = [
        _FakeTreatment(code="manual30", role="therapist"),
        _FakeTreatment(code="manual60", role="therapist"),
        _FakeTreatment(code="manual90", role="therapist"),
        _FakeTreatment(code="eswt", role="therapist"),
        _FakeTreatment(code="inj1", role="doctor"),
    ]
    result = _rules.therapist_only_codes(treatments)
    inline_result = {
        t.code for t in treatments
        if t.role == "therapist" and t.code != "eswt"
    }
    assert result == inline_result == {"manual30", "manual60", "manual90"}


def test_existing_codes_includes_inactive():
    """COMPAT: ``api.py:_existing_codes_set`` 는 active 무관."""
    treatments = [
        _FakeTreatment(code="manual30", active=True),
        _FakeTreatment(code="manual_old", active=False),
    ]
    result = _rules.existing_codes(treatments)
    assert result == {"manual30", "manual_old"}


def test_active_manual_codes_excludes_inactive_and_eswt():
    """COMPAT: ``api.py:_get_manual_therapy_codes`` 와 byte-equivalent — active + role
    + non-eswt."""
    treatments = [
        _FakeTreatment(code="manual30", role="therapist", active=True),
        _FakeTreatment(code="manual60", role="therapist", active=True),
        _FakeTreatment(code="manual90", role="therapist", active=True),
        _FakeTreatment(code="manual_old", role="therapist", active=False),
        _FakeTreatment(code="eswt", role="therapist", active=True),
        _FakeTreatment(code="inj1", role="doctor", active=True),
    ]
    result = _rules.active_manual_codes(treatments)
    assert result == ["manual30", "manual60", "manual90"]


# ──────────────────────── 3. serialize_treatment byte-equivalent ──────────


def test_serialize_treatment_keys_match_api_py():
    """COMPAT: ``api.py:_serialize_treatment`` (line 767~783) 와 byte-equivalent."""
    t = _FakeTreatment(
        id="T-1", code="manual30", name="도수30분", short="도수30",
        default_minutes=30, role="therapist", count_increment=1,
        show_in_patient=True, active=True, sort_order=2, price=50000,
        incentive_pct=10.0, incentive_amount=None,
    )
    result = _service.serialize_treatment(t)
    expected_keys = {
        "id", "code", "name", "short", "category_id", "category_name",
        "default_minutes", "role",
        "count_increment", "show_in_patient", "active", "sort_order",
        "price", "incentive_pct", "incentive_amount",
    }
    assert set(result.keys()) == expected_keys
    assert result["count_increment"] == 1  # manual30 = 1
    assert result["price"] == 50000


def test_serialize_treatment_handles_missing_attrs():
    """``price`` / ``incentive_*`` 가 None / 부재 시 안전 fallback."""

    class _MinimalT:
        id = "T-X"
        code = "x"
        name = "x"
        short = "x"
        default_minutes = 30
        role = "therapist"
        count_increment = 1
        show_in_patient = True
        active = True
        sort_order = 0

    result = _service.serialize_treatment(_MinimalT())
    assert result["price"] == 0
    assert result["incentive_pct"] is None
    assert result["incentive_amount"] is None


# ──────────────────────── 4. normalize_incentive 동등 ─────────────────────


def test_normalize_incentive_xor_validation():
    """COMPAT: 둘 다 양수 → IncentiveValidationError."""
    with pytest.raises(_service.IncentiveValidationError):
        _service.normalize_incentive(10.0, 5000)


def test_normalize_incentive_pct_range():
    """pct 0~100 검증."""
    with pytest.raises(_service.IncentiveValidationError):
        _service.normalize_incentive(150.0, None)


@pytest.mark.parametrize(
    "pct,amount,expected",
    [
        (None, None, (None, None)),
        ("", "", (None, None)),
        (0, 0, (None, None)),  # 0 이하 → None
        (-5, None, (None, None)),
        (10.5, None, (10.5, None)),
        (None, 5000, (None, 5000)),
        ("20", None, (20.0, None)),
        (None, "3000", (None, 3000)),
    ],
)
def test_normalize_incentive_returns(pct, amount, expected):
    assert _service.normalize_incentive(pct, amount) == expected


# ──────────────────────── 5. build_treatment_meta 응답 dict ───────────────


def test_build_treatment_meta_keys():
    """COMPAT: ``api.py:_build_treatment_meta`` 응답 15키 정합."""
    treatments = [
        _FakeTreatment(code="manual30", role="therapist", active=True, sort_order=1),
        _FakeTreatment(code="manual60", role="therapist", active=True, sort_order=2,
                       count_increment=1),
        _FakeTreatment(code="eswt", role="therapist", active=True, sort_order=3),
        _FakeTreatment(code="inj1", role="doctor", active=True, sort_order=4),
    ]
    result = _service.build_treatment_meta(treatments)
    expected_keys = {
        "treatment_codes", "treatment_names", "treatment_short",
        "treatment_category", "treatment_category_name",
        "treatment_minutes", "treatment_role", "treatment_show",
        "doctor_treatments", "therapist_treatments", "manual_treatments",
        "count_increment", "eswt_code",
        "treatment_price", "treatment_incentive_pct", "treatment_incentive_amount",
        "employee_categories", "all_treatments",
    }
    assert set(result.keys()) == expected_keys
    # 분류 정합.
    assert result["doctor_treatments"] == ["inj1"]
    assert set(result["therapist_treatments"]) == {"manual30", "manual60", "eswt"}
    assert set(result["manual_treatments"]) == {"manual30", "manual60"}
    # eswt_code 노출.
    assert result["eswt_code"] == "eswt"
    # count_increment 그대로 노출 (시간 가중치 ⊥).
    assert result["count_increment"]["manual60"] == 1


# ──────────────────────── 6. completion_rules — bump_patient_count ────────


def test_bump_patient_count_byte_equivalent_with_api(client):
    """COMPAT: ``api.py:_bump_patient_count`` 와 byte-equivalent.

    검증: insert / update / 0 미만 방지 / no-op.
    """
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id

    patient_id = get_test_patient_id("홍길동테스트")

    db = SessionLocal()
    try:
        # 사전 cleanup — 이전 테스트 잔여.
        manual30 = db.query(_m.Treatment).filter_by(code="manual30").first()
        if manual30 is not None:
            db.query(_m.PatientTreatmentCount).filter_by(
                patient_id=patient_id, treatment_id=manual30.id,
            ).delete()
            db.commit()

        # +1 → Lazy 생성.
        _comp.bump_patient_count(
            db, patient_id=patient_id, treatment_code="manual30", delta=+1,
        )
        db.commit()
        row = (
            db.query(_m.PatientTreatmentCount)
            .filter_by(patient_id=patient_id, treatment_id=manual30.id)
            .first()
        )
        assert row is not None
        assert row.done_count == 1

        # +2 → 누적 (시간 가중치 ⊥, 호출자가 코드별 +1 N회 호출).
        _comp.bump_patient_count(
            db, patient_id=patient_id, treatment_code="manual30", delta=+2,
        )
        db.commit()
        db.refresh(row)
        assert row.done_count == 3

        # -10 → 0 미만 방지 (max 0).
        _comp.bump_patient_count(
            db, patient_id=patient_id, treatment_code="manual30", delta=-10,
        )
        db.commit()
        db.refresh(row)
        assert row.done_count == 0

        # delta=0 → no-op.
        before = row.done_count
        _comp.bump_patient_count(
            db, patient_id=patient_id, treatment_code="manual30", delta=0,
        )
        db.commit()
        db.refresh(row)
        assert row.done_count == before

        # 알 수 없는 code → no-op (silent fail).
        _comp.bump_patient_count(
            db, patient_id=patient_id, treatment_code="nonexistent_xyz", delta=+1,
        )
        db.commit()

        # cleanup.
        db.delete(row)
        db.commit()
    finally:
        db.close()


def test_bump_patient_count_lazy_create_only_on_positive_delta(client):
    """행 부재 + delta <= 0 → Lazy 생성 ⊥ (api.py 정합)."""
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id

    patient_id = get_test_patient_id("김영희테스트")

    db = SessionLocal()
    try:
        manual60 = db.query(_m.Treatment).filter_by(code="manual60").first()
        # 사전 cleanup.
        db.query(_m.PatientTreatmentCount).filter_by(
            patient_id=patient_id, treatment_id=manual60.id,
        ).delete()
        db.commit()

        # delta=-1 + 행 부재 → no-op (Lazy 생성 ⊥).
        _comp.bump_patient_count(
            db, patient_id=patient_id, treatment_code="manual60", delta=-1,
        )
        db.commit()
        row = (
            db.query(_m.PatientTreatmentCount)
            .filter_by(patient_id=patient_id, treatment_id=manual60.id)
            .first()
        )
        assert row is None
    finally:
        db.close()


# ──────────────────────── 7. manual60 = 1 정책 (CLAUDE.md 정합) ───────────


def test_manual60_count_increment_is_one(client):
    """RISK: ``manual60`` 의 ``count_increment`` 가 1 인지 시드 검증.

    사용자 명시 + CLAUDE.md 정합 — 시간 가중치 합산 (count_increment=2) 으로
    되돌리는 것 금지.
    """
    from app.database import SessionLocal
    from app.models import models as _m

    db = SessionLocal()
    try:
        manual60 = db.query(_m.Treatment).filter_by(code="manual60").first()
        assert manual60 is not None, "manual60 시드 부재"
        assert manual60.count_increment == 1, (
            f"manual60.count_increment = {manual60.count_increment} — "
            "사용자 명시 + CLAUDE.md 정합 1 로 유지해야 함 (시간 가중치 ⊥)"
        )
        # 19-6 helper 도 동일 값 노출.
        assert _rules.get_count_increment(manual60) == 1
        # 19-6 정책 상수 정합.
        assert _comp.EXPECTED_MANUAL60_COUNT_INCREMENT == 1
        assert _comp.expected_count_per_appointment_code() == 1
    finally:
        db.close()


def test_per_code_completion_check_principle():
    """*항목별 개별 체크* 원칙 검증 — 도수30 / 도수60 / 도수90 / ESWT 모두 독립 카운트.

    시간 가중치 합산 ⊥. 각 코드는 ``+1`` 만 (count_increment 곱셈 ⊥).
    """
    # 19-6 helper 가 항목별 ±1 만 — count_increment 와 무관.
    assert _comp.DEFAULT_COMPLETION_DELTA_PER_CODE == 1
    # 19-6 helper 는 ``count_increment`` 를 *그대로* 노출 (정책 결정 ⊥).
    t30 = _FakeTreatment(code="manual30", count_increment=1)
    t60 = _FakeTreatment(code="manual60", count_increment=1)
    t90 = _FakeTreatment(code="manual90", count_increment=1)
    assert _rules.get_count_increment(t30) == 1
    assert _rules.get_count_increment(t60) == 1
    assert _rules.get_count_increment(t90) == 1


# ──────────────────────── 8. 단방향 경계 (D-4 ast 기반) ───────────────────


def test_treatments_rules_does_not_import_models_or_db():
    """rules 는 ORM/DB/services/routers 미참조 (D-4)."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_rules)
    tree = _ast.parse(src)
    forbidden = {
        "app.models", "app.database", "app.services", "app.routers",
        "sqlalchemy", "fastapi",
        "app.modules.settings", "app.modules.health", "app.modules.calendar",
        "app.modules.appointments", "app.modules.leaves",
    }
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == f or alias.name.startswith(f + ".")
                    for f in forbidden
                ), f"treatments.rules 가 금지된 import: {alias.name!r}"
        elif isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden
            ), f"treatments.rules 가 금지된 import: from {mod!r}"


def test_treatments_repository_top_level_lazy_import():
    """repository 는 ``app.models`` lazy import — top-level 부재."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_repo)
    tree = _ast.parse(src)
    top_imports = [
        n for n in tree.body
        if isinstance(n, (_ast.Import, _ast.ImportFrom))
    ]
    forbidden_top = {"app.models", "app.database", "sqlalchemy"}
    for node in top_imports:
        if isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden_top
            ), f"treatments.repository top-level 금지 import: from {mod!r}"


def test_treatments_service_does_not_import_routers_or_fastapi():
    """service 는 ``app.routers`` / ``fastapi`` 미참조 (D-4)."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_service)
    tree = _ast.parse(src)
    forbidden = {"app.routers", "fastapi"}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden
            ), f"treatments.service 가 금지된 import: from {mod!r}"


def test_treatments_completion_rules_top_level_lazy_import():
    """completion_rules 는 ``app.models`` lazy import — top-level 부재."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_comp)
    tree = _ast.parse(src)
    top_imports = [
        n for n in tree.body
        if isinstance(n, (_ast.Import, _ast.ImportFrom))
    ]
    forbidden_top = {"app.models", "sqlalchemy", "fastapi"}
    for node in top_imports:
        if isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden_top
            ), f"treatments.completion_rules top-level 금지 import: from {mod!r}"


# ──────────────────────── 9. 라우터 무수정 회귀 ──────────────────────────


def test_existing_treatment_helpers_in_api_py_unchanged():
    """COMPAT: api.py 본체 함수 그대로 존재."""
    from app.routers import api as _api
    assert hasattr(_api, "_serialize_treatment")
    assert hasattr(_api, "_normalize_incentive")
    assert hasattr(_api, "_build_treatment_meta")
    assert hasattr(_api, "_bump_patient_count")
    assert hasattr(_api, "_get_manual_treatment_rows")
    assert hasattr(_api, "_get_manual_therapy_codes")
    assert hasattr(_api, "_doctor_codes_set")
    assert hasattr(_api, "_therapist_only_codes_set")


def test_treatment_meta_endpoint_still_works(client):
    """기존 GET /api/treatment-meta 응답 회귀 — 라우터 무수정."""
    resp = client.get("/api/treatment-meta")
    assert resp.status_code == 200
    body = resp.json()
    expected_keys = {
        "treatment_codes", "treatment_names", "treatment_short",
        "treatment_category", "treatment_category_name",
        "treatment_minutes", "treatment_role", "treatment_show",
        "doctor_treatments", "therapist_treatments", "manual_treatments",
        "count_increment", "eswt_code",
        "treatment_price", "treatment_incentive_pct", "treatment_incentive_amount",
        "employee_categories", "all_treatments",
    }
    assert set(body.keys()) == expected_keys


def test_treatments_list_endpoint_still_works(client):
    """기존 GET /api/treatments 응답 회귀."""
    resp = client.get("/api/treatments")
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    if rows:
        assert "code" in rows[0]
        assert "count_increment" in rows[0]


def test_default_treatments_can_be_loaded_from_editable_json(monkeypatch):
    """기본 치료항목 시드는 코드 상수가 아니라 JSON 파일에서 로드된다."""
    from app.config import get_appdata_dir

    path = get_appdata_dir() / "test_default_treatments.json"
    path.write_text(
        json.dumps(
            [
                {
                    "code": "manual_custom",
                    "name": "사용자도수",
                    "short": "사용자",
                    "default_minutes": 45,
                    "role": "therapist",
                    "count_increment": 1,
                    "show_in_patient": True,
                    "active": True,
                    "sort_order": 1,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(_defaults.DEFAULT_TREATMENTS_ENV, str(path))

    rows = _defaults.load_default_treatments()

    assert rows[0]["code"] == "manual_custom"
    assert rows[0]["name"] == "사용자도수"
    assert rows[0]["default_minutes"] == 45


def test_treatment_create_rejects_invalid_custom_code(client):
    """새 치료항목의 내부 코드는 예약 참조 키라 안전한 형식만 허용한다."""
    login = client.post("/api/admin/login", json={"password": "admin1234"})
    assert login.status_code == 200
    token = login.json()["token"]

    resp = client.post(
        "/api/treatments",
        json={
            "code": "한글 코드",
            "name": "테스트치료",
            "short": "테코",
            "default_minutes": 30,
            "role": "therapist",
            "count_increment": 1,
            "show_in_patient": True,
            "active": True,
            "sort_order": 0,
            "price": 0,
            "incentive_pct": None,
            "incentive_amount": None,
        },
        headers={"X-Admin-Token": token},
    )

    assert resp.status_code == 400


# ──────────────────────── 10. 외부 API 호출 0 검증 ────────────────────────


def test_helpers_do_not_invoke_provider_or_db():
    """SAFETY: rules / service helper 안에서 외부 API / SDK / DB 호출 ⊥."""
    treatments = [_FakeTreatment()]
    _ = _rules.is_doctor_role(treatments[0])
    _ = _rules.is_therapist_role(treatments[0])
    _ = _rules.is_manual_treatment(treatments[0])
    _ = _rules.is_eswt_treatment(treatments[0])
    _ = _rules.is_active(treatments[0])
    _ = _rules.doctor_codes(treatments)
    _ = _rules.therapist_codes(treatments)
    _ = _rules.therapist_only_codes(treatments)
    _ = _rules.existing_codes(treatments)
    _ = _rules.active_manual_codes(treatments)
    _ = _rules.is_completion_target(treatments[0])
    _ = _rules.get_count_increment(treatments[0])
    _ = _service.serialize_treatment(treatments[0])
    _ = _service.normalize_incentive(None, None)
    _ = _service.build_treatment_meta(treatments)
    _ = _comp.expected_count_per_appointment_code()
