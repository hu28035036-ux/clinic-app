"""19-7 patients / notes contract.

검증 범위 (19-7 세션 지시문 정합):
  1. ``patients.rules`` 중복 검사 / 신환 체크 / PII 마스킹 helper 가 ``api.py:
     _check_patient_duplicate`` / ``patient_manual_history_summary`` 와 byte-equivalent.
  2. ``patients.service`` 응답 dict 빌더가 ``api.py:_patient_to_dict`` /
     ``_patient_counts_dict`` / ``list_patients(light=1)`` / ``search_patients`` /
     ``patient_manual_history_summary`` 와 byte-equivalent.
  3. ``notes.rules`` 의 메모 분류 (Patient.memo / Appointment.memo) 가 *현재 구현* 정합.
  4. ``notes.rules.append_cancel_memo`` 가 ``api.py:cancel_appointment`` 의
     ``\\n[취소]`` prefix 패턴과 byte-equivalent.
  5. PII 마스킹 helper (mask_name / mask_phone / mask_birth_date / mask_memo /
     mask_chart_no) 가 *원문 노출 ⊥*.
  6. modules.patients / modules.notes 단방향 경계 (D-4 ast 기반).
  7. 라우터 / SMS / AI 본체 무수정 — 응답 키 보존.
"""
from __future__ import annotations

import importlib

import pytest

from app.modules.notes import rules as _notes_rules
from app.modules.patients import repository as _pat_repo
from app.modules.patients import rules as _pat_rules
from app.modules.patients import service as _pat_svc

# ──────────────────────── 1. 중복 검사 정규화 / 분기 helper ───────────────


@pytest.mark.parametrize(
    "name,birth_date,chart_no,expected",
    [
        ("홍길동", "1980-01-01", "C-100", ("홍길동", "1980-01-01", "C-100")),
        ("  홍길동  ", "  1980-01-01  ", "  C-100  ", ("홍길동", "1980-01-01", "C-100")),
        (None, None, None, ("", "", "")),
        ("", "", "", ("", "", "")),
        ("홍길동", "", "C-100", ("홍길동", "", "C-100")),
    ],
)
def test_normalize_for_duplicate_check(name, birth_date, chart_no, expected):
    """COMPAT: ``api.py:_check_patient_duplicate`` line 1415~1417 정규화 정합."""
    assert _pat_rules.normalize_for_duplicate_check(name, birth_date, chart_no) == expected


@pytest.mark.parametrize(
    "chart_no,expected",
    [("C-100", True), ("", False)],
)
def test_should_check_chart_no_duplicate(chart_no, expected):
    assert _pat_rules.should_check_chart_no_duplicate(chart_no) is expected


@pytest.mark.parametrize(
    "name,birth_date,expected",
    [
        ("홍길동", "1980-01-01", True),
        ("홍길동", "", False),
        ("", "1980-01-01", False),
        ("", "", False),
    ],
)
def test_should_check_name_birth_duplicate(name, birth_date, expected):
    assert _pat_rules.should_check_name_birth_duplicate(name, birth_date) is expected


def test_duplicate_messages_korean():
    """COMPAT: ``api.py:_check_patient_duplicate`` 메시지 정합."""
    assert _pat_rules.DUPLICATE_CHART_NO_MESSAGE == "이미 등록된 차트번호입니다."
    assert _pat_rules.DUPLICATE_NAME_BIRTH_MESSAGE == (
        "같은 이름과 생년월일의 환자가 이미 등록되어 있습니다."
    )


# ──────────────────────── 2. 신환 체크 helper ─────────────────────────────


@pytest.mark.parametrize(
    "flags,expected",
    [
        ([True], True),
        ([False, True], True),
        ([False, False], False),
        ([], False),
    ],
)
def test_derive_has_new_patient_flag(flags, expected):
    """COMPAT: ``api.py:patient_manual_history_summary`` line 1509~1515 정합."""
    assert _pat_rules.derive_has_new_patient_flag(flags) is expected


@pytest.mark.parametrize(
    "ids,expected",
    [(["a"], True), (["a", "b"], True), ([], False)],
)
def test_derive_has_manual_history(ids, expected):
    assert _pat_rules.derive_has_manual_history(ids) is expected


# ──────────────────────── 3. PII 마스킹 helper ────────────────────────────


@pytest.mark.parametrize(
    "name,expected",
    [
        ("홍길동", "홍**"),
        ("김", "김**"),
        ("Alice", "A**"),
        ("", ""),
        (None, ""),
        ("   ", ""),
    ],
)
def test_mask_name(name, expected):
    """SAFETY: 환자명 첫 글자 + ``**``. 운영 응답에는 사용 ⊥."""
    assert _pat_rules.mask_name(name) == expected


@pytest.mark.parametrize(
    "phone,expected",
    [
        ("010-1234-5678", "010-****-5678"),
        ("01012345678", "010-****-5678"),
        ("010 1234 5678", "010-****-5678"),
        ("02-345-6789", "02-****-6789"),
        ("", ""),
        (None, ""),
        ("invalid", "****"),
    ],
)
def test_mask_phone(phone, expected):
    """SAFETY: 가운데 4자리 ``****``."""
    assert _pat_rules.mask_phone(phone) == expected


@pytest.mark.parametrize(
    "birth,expected",
    [
        ("1980-01-15", "1980-**-**"),
        ("1980/01/15", "1980-**-**"),
        ("19800115", "1980-**-**"),
        ("", ""),
        (None, ""),
        ("invalid", "****-**-**"),
    ],
)
def test_mask_birth_date(birth, expected):
    """SAFETY: 년도만 남기고 월/일 마스킹."""
    assert _pat_rules.mask_birth_date(birth) == expected


@pytest.mark.parametrize(
    "memo,expected",
    [
        ("짧은 메모", "짧은 메모"),
        ("", ""),
        (None, ""),
        ("a" * 25, f"{'a' * 20}…(25자)"),  # truncate at 20 + length suffix
    ],
)
def test_mask_memo(memo, expected):
    """SAFETY: 20자 초과 시 truncate + 길이 suffix."""
    assert _pat_rules.mask_memo(memo) == expected


def test_mask_memo_scrubs_phone_pattern_in_head():
    """SAFETY: 첫 20자 안에 전화번호가 있어도 ``***`` 로 치환."""
    memo = "환자 010-1234-5678 약 알레르기"
    masked = _pat_rules.mask_memo(memo)
    assert "010-1234-5678" not in masked
    assert "***" in masked


def test_mask_memo_scrubs_rrn_pattern():
    """SAFETY: 주민번호 패턴 (000000-0000000) 도 ``***`` 로 치환."""
    memo = "환자 800101-1234567 차트 갱신 필요"
    masked = _pat_rules.mask_memo(memo)
    assert "800101-1234567" not in masked
    assert "***" in masked


@pytest.mark.parametrize(
    "chart,expected",
    [
        ("C-12345", "C-****"),
        ("AB", "****"),
        ("", ""),
        (None, ""),
    ],
)
def test_mask_chart_no(chart, expected):
    """SAFETY: 앞 2자 + ``****``."""
    assert _pat_rules.mask_chart_no(chart) == expected


def test_patient_summary_for_log_does_not_leak_pii():
    """SAFETY: 마스킹 dict 결과에 *원문* PII 가 포함 ⊥."""
    raw_name = "홍길동"
    raw_phone = "010-1234-5678"
    raw_birth = "1980-01-15"
    raw_chart = "C-12345"
    raw_memo = (
        "환자가 어제 010-9999-8888 로 전화 와서 약 알레르기 있다고 함. 추가 진단 필요."
    )

    summary = _pat_rules.patient_summary_for_log(
        name=raw_name, phone=raw_phone, birth_date=raw_birth,
        chart_no=raw_chart, memo=raw_memo,
    )

    # 원문 어디에도 미포함.
    summary_str = str(summary)
    assert raw_name not in summary_str
    assert raw_phone not in summary_str
    assert raw_birth not in summary_str
    assert raw_chart not in summary_str
    # 메모 안의 별도 전화번호도 truncate 으로 마스킹됨.
    assert "010-9999-8888" not in summary_str

    # 결과 dict 5키.
    assert set(summary.keys()) == {"name", "phone", "birth_date", "chart_no", "memo"}


# ──────────────────────── 4. service — counts dict ───────────────────────


class _FakeTreatment:
    def __init__(
        self, *, id="T-1", code="manual30", name="도수30", short="도수",
        role="therapist", show_in_patient=True, active=True, sort_order=1,
    ):
        self.id = id
        self.code = code
        self.name = name
        self.short = short
        self.role = role
        self.show_in_patient = show_in_patient
        self.active = active
        self.sort_order = sort_order


class _FakeCount:
    def __init__(self, *, treatment_id, rx_count=0, done_count=0):
        self.treatment_id = treatment_id
        self.rx_count = rx_count
        self.done_count = done_count


def test_build_patient_counts_dict_structure():
    """COMPAT: ``api.py:_patient_counts_dict`` 9키 per item 정합."""
    treatments = [
        _FakeTreatment(id="T-1", code="manual30"),
        _FakeTreatment(id="T-2", code="eswt"),
    ]
    counts = [_FakeCount(treatment_id="T-1", rx_count=5, done_count=3)]

    result = _pat_svc.build_patient_counts_dict(
        treatments_sorted=treatments, counts_rows=counts,
    )

    assert "T-1" in result and "T-2" in result
    expected_keys = {
        "treatment_id", "code", "name", "short", "role",
        "show", "active", "rx_count", "done_count",
    }
    assert set(result["T-1"].keys()) == expected_keys
    assert result["T-1"]["rx_count"] == 5
    assert result["T-1"]["done_count"] == 3
    # row 부재 → 0 / 0.
    assert result["T-2"]["rx_count"] == 0
    assert result["T-2"]["done_count"] == 0


# ──────────────────────── 5. service — patient_to_dict ────────────────────


class _FakePatient:
    def __init__(
        self, *, id="P-1", name="홍길동", birth_date="1980-01-15",
        phone="010-1234-5678", chart_no="C-100", gender="m",
        memo="환자 메모",
    ):
        self.id = id
        self.name = name
        self.birth_date = birth_date
        self.phone = phone
        self.chart_no = chart_no
        self.gender = gender
        self.memo = memo


def test_build_patient_dict_keys():
    """COMPAT: ``api.py:_patient_to_dict`` 9키 정합."""
    p = _FakePatient()
    counts = {
        "T-1": {
            "treatment_id": "T-1", "code": "manual30",
            "name": "도수30", "short": "도수",
            "role": "therapist",
            "show": True, "active": True,
            "rx_count": 1, "done_count": 0,
        },
        "T-2": {
            "treatment_id": "T-2", "code": "eswt",
            "name": "ESWT", "short": "충",
            "role": "therapist",
            "show": False, "active": True,
            "rx_count": 0, "done_count": 0,
        },
    }
    result = _pat_svc.build_patient_dict(p, counts=counts)

    expected_keys = {
        "id", "name", "birth_date", "phone", "chart_no",
        "gender", "memo", "counts", "counts_show",
    }
    assert set(result.keys()) == expected_keys
    # counts_show: show=True AND active=True 만, code 순.
    assert len(result["counts_show"]) == 1
    assert result["counts_show"][0]["code"] == "manual30"


def test_build_patient_dict_handles_missing_gender_and_empty_memo():
    """``gender`` 부재 → 빈 문자열 / ``memo`` None → 빈 문자열."""

    class _MinimalPatient:
        id = "P-X"
        name = "X"
        birth_date = "1990-01-01"
        phone = ""
        chart_no = ""
        memo = None

    result = _pat_svc.build_patient_dict(_MinimalPatient(), counts={})
    assert result["gender"] == ""
    assert result["memo"] == ""


def test_build_patient_light_dict_keys():
    """COMPAT: ``api.py:list_patients(light=1)`` 7키 정합."""
    p = _FakePatient()
    result = _pat_svc.build_patient_light_dict(p)
    expected_keys = {
        "id", "name", "chart_no", "phone", "birth_date", "gender", "memo",
    }
    assert set(result.keys()) == expected_keys
    assert "counts" not in result


# ──────────────────────── 6. service — search response envelope ──────────


def test_build_patient_search_response_keys():
    """COMPAT: ``api.py:search_patients`` 6키 envelope 정합."""
    items = [{"id": "P-1"}]
    result = _pat_svc.build_patient_search_response(
        items=items, total=10, limit=20, offset=0, q="홍",
    )
    assert set(result.keys()) == {"items", "total", "limit", "offset", "q", "has_more"}
    assert result["has_more"] is True  # offset(0)+len(1) < total(10)


def test_build_patient_search_has_more_boundary():
    """has_more = (offset + len(items)) < total."""
    items = [{"id": "P-1"}, {"id": "P-2"}]
    # 정확히 마지막 페이지.
    result = _pat_svc.build_patient_search_response(
        items=items, total=2, limit=20, offset=0, q="",
    )
    assert result["has_more"] is False


# ──────────────────────── 7. service — manual history summary ────────────


def test_build_manual_history_summary_keys():
    """COMPAT: ``api.py:patient_manual_history_summary`` 5키 정합."""
    result = _pat_svc.build_manual_history_summary(
        patient_id="P-1",
        manual_appointment_ids=["A-1", "A-2"],
        has_new_patient_flag=True,
    )
    assert set(result.keys()) == {
        "patient_id", "has_manual_history", "manual_count",
        "has_new_patient_flag", "manual_appointment_ids",
    }
    assert result["has_manual_history"] is True
    assert result["manual_count"] == 2
    assert result["has_new_patient_flag"] is True


def test_build_manual_history_summary_empty_appointments():
    result = _pat_svc.build_manual_history_summary(
        patient_id="P-1",
        manual_appointment_ids=[],
        has_new_patient_flag=False,
    )
    assert result["has_manual_history"] is False
    assert result["manual_count"] == 0


# ──────────────────────── 8. notes — 메모 분류 ─────────────────────────


def test_note_kind_constants():
    """현재 구현된 메모 종류 — Patient / Appointment 두 종만."""
    assert _notes_rules.NOTE_KIND_PATIENT == "patient"
    assert _notes_rules.NOTE_KIND_APPOINTMENT == "appointment"
    assert set(_notes_rules.NOTE_KIND_VALUES) == {"patient", "appointment"}


def test_is_persistent_note_only_patient():
    """RISK: *공식 정의 ⊥* — 현재 구현 매핑만."""
    assert _notes_rules.is_persistent_note("patient") is True
    assert _notes_rules.is_persistent_note("appointment") is False
    assert _notes_rules.is_persistent_note("unknown") is False


def test_is_per_appointment_note_only_appointment():
    assert _notes_rules.is_per_appointment_note("appointment") is True
    assert _notes_rules.is_per_appointment_note("patient") is False


# ──────────────────────── 9. notes — append_cancel_memo ───────────────


@pytest.mark.parametrize(
    "existing,reason,expected",
    [
        ("", "환자 요청", "\n[취소] 환자 요청"),
        ("기존 메모", "환자 요청", "기존 메모\n[취소] 환자 요청"),
        ("기존 메모", "", "기존 메모\n[취소]"),
        ("기존 메모", None, "기존 메모\n[취소]"),
        (None, "사유", "\n[취소] 사유"),
        (None, None, "\n[취소]"),
    ],
)
def test_append_cancel_memo_byte_equivalent_with_api_py(existing, reason, expected):
    """COMPAT: ``api.py:cancel_appointment`` line 2016 인라인 패턴 정합."""
    assert _notes_rules.append_cancel_memo(existing, reason) == expected


def test_cancel_memo_prefix_constant():
    assert _notes_rules.CANCEL_MEMO_PREFIX == "\n[취소]"


# ──────────────────────── 10. notes — mask_memo_for_log ──────────────


def test_notes_mask_memo_equivalent_to_patients_mask_memo():
    """COMPAT: ``notes.rules.mask_memo_for_log`` == ``patients.rules.mask_memo``."""
    samples = [
        None, "", "짧은", "a" * 25,
        "전화 010-9999-8888 진단 알레르기 있음 추가 메모 길게 작성",
    ]
    for s in samples:
        assert _notes_rules.mask_memo_for_log(s) == _pat_rules.mask_memo(s)


def test_notes_mask_memo_truncates_pii_in_long_memo():
    """SAFETY: 메모 안 PII (전화 / 진단명) 가 *원문* 으로 노출 ⊥ — truncate 됨."""
    long_memo = "환자가 010-9999-8888 로 연락 와서 진단명 ABC 알레르기 가능성 의심됨"
    masked = _notes_rules.mask_memo_for_log(long_memo, max_chars=15)
    assert "010-9999-8888" not in masked  # truncate 으로 잘림
    assert masked.endswith(f"…({len(long_memo)}자)")


# ──────────────────────── 11. 단방향 경계 (D-4 ast 기반) ──────────────


def test_patients_rules_does_not_import_models_or_db():
    """patients.rules 는 ORM/DB/services/routers 미참조."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_pat_rules)
    tree = _ast.parse(src)
    forbidden = {
        "app.models", "app.database", "app.services", "app.routers",
        "sqlalchemy", "fastapi",
        "app.modules.settings", "app.modules.health", "app.modules.calendar",
        "app.modules.appointments", "app.modules.leaves",
        "app.modules.treatments",
    }
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == f or alias.name.startswith(f + ".")
                    for f in forbidden
                ), f"patients.rules 가 금지된 import: {alias.name!r}"
        elif isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden
            ), f"patients.rules 가 금지된 import: from {mod!r}"


def test_patients_repository_top_level_lazy_import():
    """patients.repository 는 top-level ``app.models`` 미참조 (lazy import)."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_pat_repo)
    tree = _ast.parse(src)
    top_imports = [
        n for n in tree.body if isinstance(n, (_ast.Import, _ast.ImportFrom))
    ]
    forbidden_top = {"app.models", "app.database", "sqlalchemy"}
    for node in top_imports:
        if isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden_top
            ), f"patients.repository top-level 금지 import: from {mod!r}"


def test_patients_service_does_not_import_routers_or_fastapi():
    """patients.service 는 ``app.routers`` / ``fastapi`` 미참조."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_pat_svc)
    tree = _ast.parse(src)
    forbidden = {"app.routers", "fastapi"}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden
            ), f"patients.service 가 금지된 import: from {mod!r}"


def test_notes_rules_does_not_import_models_or_db():
    """notes.rules 는 ORM/DB 미참조."""
    import ast as _ast
    src = importlib.import_module("inspect").getsource(_notes_rules)
    tree = _ast.parse(src)
    forbidden = {
        "app.models", "app.database", "app.services", "app.routers",
        "sqlalchemy", "fastapi",
    }
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom):
            mod = node.module or ""
            assert not any(
                mod == f or mod.startswith(f + ".") for f in forbidden
            ), f"notes.rules 가 금지된 import: from {mod!r}"


def test_patients_init_does_not_import_models():
    """patients/__init__ 단방향."""
    import ast as _ast

    import app.modules.patients as _mod
    src = importlib.import_module("inspect").getsource(_mod)
    tree = _ast.parse(src)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom):
            mod_name = node.module or ""
            assert not any(
                mod_name == f or mod_name.startswith(f + ".")
                for f in ("app.models", "app.database", "app.services", "app.routers", "sqlalchemy")
            ), f"patients/__init__ 가 금지된 import: from {mod_name!r}"


def test_notes_init_does_not_import_models():
    """notes/__init__ 단방향."""
    import ast as _ast

    import app.modules.notes as _mod
    src = importlib.import_module("inspect").getsource(_mod)
    tree = _ast.parse(src)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom):
            mod_name = node.module or ""
            assert not any(
                mod_name == f or mod_name.startswith(f + ".")
                for f in ("app.models", "app.database", "app.services", "app.routers", "sqlalchemy")
            ), f"notes/__init__ 가 금지된 import: from {mod_name!r}"


# ──────────────────────── 12. 라우터 무수정 회귀 ──────────────────────


def test_existing_patient_helpers_in_api_py_unchanged():
    """COMPAT: api.py 본체 함수 그대로 존재."""
    from app.routers import api as _api
    assert hasattr(_api, "_check_patient_duplicate")
    assert hasattr(_api, "_patient_counts_dict")
    assert hasattr(_api, "_patient_to_dict")
    assert hasattr(_api, "_serialize_patients_bulk")
    assert hasattr(_api, "_apply_patient_counts")
    assert hasattr(_api, "patient_manual_history_summary")
    assert hasattr(_api, "update_patient_memo")


def test_patients_endpoint_still_works(client):
    """기존 GET /api/patients?light=1 응답 회귀."""
    resp = client.get("/api/patients?light=1")
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    if rows:
        keys = set(rows[0].keys())
        assert keys == {
            "id", "name", "chart_no", "phone", "birth_date", "gender", "memo",
        }


def test_patients_search_endpoint_still_works(client):
    """기존 GET /api/patients/search 응답 회귀 — 6키 envelope."""
    resp = client.get("/api/patients/search?q=&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "items", "total", "limit", "offset", "q", "has_more",
    }


def test_patient_manual_history_summary_endpoint_still_works(client):
    """기존 GET /api/patients/{pid}/manual-history-summary 응답 회귀 — 5키."""
    from tests.harness.seed_data import get_test_patient_id
    pid = get_test_patient_id("홍길동테스트")
    resp = client.get(f"/api/patients/{pid}/manual-history-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "patient_id", "has_manual_history", "manual_count",
        "has_new_patient_flag", "manual_appointment_ids",
    }


# ──────────────────────── 13. 외부 API 호출 0 검증 ────────────────────


def test_helpers_do_not_invoke_provider_or_db():
    """SAFETY: rules / service helper 안에서 외부 API / SDK / DB 호출 ⊥."""
    p = _FakePatient()
    treatments = [_FakeTreatment()]

    # patients.rules
    _ = _pat_rules.normalize_for_duplicate_check("a", "b", "c")
    _ = _pat_rules.should_check_chart_no_duplicate("c")
    _ = _pat_rules.should_check_name_birth_duplicate("a", "b")
    _ = _pat_rules.derive_has_new_patient_flag([True])
    _ = _pat_rules.derive_has_manual_history(["a"])
    _ = _pat_rules.mask_name("홍길동")
    _ = _pat_rules.mask_phone("010-1234-5678")
    _ = _pat_rules.mask_birth_date("1980-01-15")
    _ = _pat_rules.mask_memo("test")
    _ = _pat_rules.mask_chart_no("C-100")
    _ = _pat_rules.patient_summary_for_log(name="홍", phone="010-1-2", birth_date="1980")

    # patients.service
    _ = _pat_svc.build_patient_counts_dict(treatments_sorted=treatments, counts_rows=[])
    _ = _pat_svc.build_patient_dict(p, counts={})
    _ = _pat_svc.build_patient_light_dict(p)
    _ = _pat_svc.build_patient_search_response(items=[], total=0, limit=10, offset=0, q="")
    _ = _pat_svc.build_manual_history_summary(
        patient_id="P-1", manual_appointment_ids=[], has_new_patient_flag=False,
    )

    # notes.rules
    _ = _notes_rules.append_cancel_memo("a", "b")
    _ = _notes_rules.mask_memo_for_log("test")
    _ = _notes_rules.is_persistent_note("patient")
    _ = _notes_rules.is_per_appointment_note("appointment")
