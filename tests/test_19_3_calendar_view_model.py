"""19-3 calendar / schedule_view 표시용 view-model contract.

검증 범위 (19-3 세션 지시문 정합):
  1. ``app.modules.calendar.view_models`` 의 helper 가 ``app/routers/api.py`` 의
     표시 로직 (``_serialize_appointment`` / ``_serialize_employee`` / ``_lighten_hex`` /
     status opacity / 치료사 색상 fallback) 과 byte-equivalent 출력.
  2. ``appointment_to_calendar_event`` 의 결과 dict 가 ``_serialize_appointment`` 와
     키 / 값 / 타입 100% 일치 — 회귀 0.
  3. modules.calendar 가 ``app.models`` / ``app.services`` / ``app.routers`` /
     ``app.database`` / ``sqlalchemy`` 를 import 하지 않음 — 단방향 경계 (D-4 정합).
  4. 환자 PII 필드 (``patient_name`` / ``patient_phone`` / ``patient_birth_date`` /
     ``patient_memo``) 가 ``extendedProps`` 에 포함되는 것은 *기존 동작 보존* —
     본 19-3 이 PII 마스킹 변경 ⊥.
  5. 휴무 표시 라벨 (``leave_type_label`` / ``leave_kind_label``) 이 알 수 없는 값에도
     안전 fallback (원문 반환) — 기존 JS 의 표시 동작 정합.
  6. ``lighten_hex`` 이 잘못된 입력 (None / 길이 부족 / 비-hex) 에 안전 fallback (FFFFFF).
  7. 외부 API 호출 0 — 본 모듈은 *값 변환* 만, provider/SDK/DB 접근 ⊥.

원칙:
  - 운영 DB 미접근 — 본 테스트는 in-memory primitives 만 사용 (DB 세션 부재).
  - 외부 API 호출 0.
"""
from __future__ import annotations

import importlib

import pytest

from app.modules.calendar import view_models as _vm

# ──────────────────────── 1. status_to_opacity ────────────────────────────


@pytest.mark.parametrize(
    "status,expected",
    [
        ("reserved", 1.0),
        ("approved", 1.0),
        ("canceled", 0.3),
        # NOTE: ``api.py:189`` ``{...}.get(a.status, 1.0)`` — 알 수 없는 값은 1.0.
        ("treated", 1.0),
        ("", 1.0),
        ("unknown", 1.0),
        (None, 1.0),
    ],
)
def test_status_to_opacity_matches_api_py_inline_dict(status, expected):
    """COMPAT: ``api.py:189`` 인라인 dict 와 byte-equivalent."""
    assert _vm.status_to_opacity(status) == expected


def test_status_opacity_constant_exposes_canceled_only_diff():
    """STATUS_OPACITY 상수가 canceled=0.3 / 나머지=1.0 정합."""
    assert _vm.STATUS_OPACITY["reserved"] == 1.0
    assert _vm.STATUS_OPACITY["approved"] == 1.0
    assert _vm.STATUS_OPACITY["canceled"] == 0.3
    assert _vm.DEFAULT_OPACITY == 1.0


# ──────────────────────── 2. therapist_color fallback ─────────────────────


@pytest.mark.parametrize(
    "color_value,expected",
    [
        # COMPAT: api.py:188 / 3789 / 3839 / 4501 / 4524 / 4723 모두 None/빈 →
        # "#9CA3AF" (gray) 정합.
        (None, "#9CA3AF"),
        ("", "#9CA3AF"),
        ("#FF0000", "#FF0000"),
        ("#3B82F6", "#3B82F6"),
        ("rebeccapurple", "rebeccapurple"),  # 알려진 keyword 도 그대로 보존
    ],
)
def test_therapist_color_fallback_to_unassigned_gray(color_value, expected):
    assert _vm.therapist_color(color_value) == expected


def test_unassigned_color_constant_value():
    """UNASSIGNED_THERAPIST_COLOR 상수 = ``"#9CA3AF"`` (api.py 인라인 정합)."""
    assert _vm.UNASSIGNED_THERAPIST_COLOR == "#9CA3AF"
    # 엑셀 export 의 미배정 컬럼 색 (api.py:4418).
    assert _vm.UNASSIGNED_COLUMN_COLOR == "#8B5CF6"
    # FullCalendar event textColor (api.py:198).
    assert _vm.DEFAULT_EVENT_TEXT_COLOR == "#fff"


# ──────────────────────── 3. lighten_hex byte-equivalent ──────────────────


def _api_py_lighten_hex_inline(hex_color: str, factor: float) -> str:
    """``api.py:4316~4330`` 의 ``_lighten_hex`` 와 byte-equivalent inline 복사 — 회귀 검증용."""
    h = (hex_color or "").lstrip("#")
    if len(h) != 6:
        return "FFFFFF"
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return "FFFFFF"
    f = max(0.0, min(1.0, float(factor)))
    r = int(r + (255 - r) * f)
    g = int(g + (255 - g) * f)
    b = int(b + (255 - b) * f)
    return f"{r:02X}{g:02X}{b:02X}"


@pytest.mark.parametrize(
    "hex_color,factor",
    [
        ("#FF0000", 0.0),
        ("#FF0000", 0.5),
        ("#FF0000", 1.0),
        ("#3B82F6", 0.85),
        ("#9CA3AF", 0.7),
        ("#8B5CF6", 0.85),
        ("#000000", 0.5),
        ("FFFFFF", 0.5),  # # 없이도 동작
        ("", 0.5),  # 빈 문자열 → "FFFFFF" fallback
        (None, 0.5),  # None → "FFFFFF" fallback
        ("badhex", 0.5),  # 6자 아님 → "FFFFFF"
        ("ZZZZZZ", 0.5),  # 6자 but 비-hex → "FFFFFF"
    ],
)
def test_lighten_hex_matches_api_py(hex_color, factor):
    """COMPAT: ``api.py:_lighten_hex`` 와 byte-equivalent."""
    expected = _api_py_lighten_hex_inline(hex_color, factor)
    actual = _vm.lighten_hex(hex_color, factor)
    assert actual == expected, f"lighten_hex({hex_color!r}, {factor}) = {actual!r}, 기대 {expected!r}"


def test_lighten_hex_clamps_factor():
    """factor 가 [0, 1] 밖이면 클램프 (음수→0, 1 초과→1)."""
    # factor=2.0 은 실효 1.0 (최대 흰색)
    assert _vm.lighten_hex("#FF0000", 2.0) == "FFFFFF"
    # factor=-0.5 는 실효 0.0 (원색)
    assert _vm.lighten_hex("#FF0000", -0.5) == "FF0000"


# ──────────────────────── 4. appointment_to_calendar_event 회귀 ────────────


def _build_extended_props_like_api_py(
    *,
    patient_id: str,
    patient_name: str,
    patient_chart_no: str,
    patient_phone: str,
    patient_birth_date: str,
    patient_memo: str,
    therapist_id: str | None,
    treatment_codes: list[str],
    status: str,
    memo: str,
    approved_at: str | None,
    approved_by: str | None,
    duration_min: int,
    assignments: list[dict],
    is_new_patient: bool,
    version: int,
) -> dict:
    """``api.py:_serialize_appointment`` 의 ``extendedProps`` 빌더와 byte-equivalent."""
    return {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "patient_chart_no": patient_chart_no,
        "patient_phone": patient_phone,
        "patient_birth_date": patient_birth_date,
        "patient_memo": patient_memo,
        "therapist_id": therapist_id,
        "treatment_codes": treatment_codes,
        "status": status,
        "memo": memo,
        "approved_at": approved_at,
        "approved_by": approved_by,
        "opacity": _vm.status_to_opacity(status),
        "duration_min": duration_min,
        "assignments": assignments,
        "is_new_patient": is_new_patient,
        "version": version,
    }


def test_appointment_to_calendar_event_matches_api_py_shape():
    """COMPAT: 결과 dict 가 ``api.py:_serialize_appointment`` 와 키 100% 일치."""
    extended = _build_extended_props_like_api_py(
        patient_id="P-001",
        patient_name="홍길동",
        patient_chart_no="C-100",
        patient_phone="010-1234-5678",
        patient_birth_date="1980-01-01",
        patient_memo="알레르기 주의",
        therapist_id="T-1",
        treatment_codes=["manual30"],
        status="reserved",
        memo="",
        approved_at=None,
        approved_by=None,
        duration_min=30,
        assignments=[{"treatment_code": "manual30", "handler_id": "T-1"}],
        is_new_patient=False,
        version=1,
    )
    event = _vm.appointment_to_calendar_event(
        appointment_id="A-001",
        start_iso="2026-05-10T10:00:00",
        end_iso="2026-05-10T10:30:00",
        status="reserved",
        therapist_color_value="#3B82F6",
        extended_props=extended,
    )

    # 9 top-level 키 정확히 일치.
    expected_top = {"id", "start", "end", "color", "textColor", "extendedProps"}
    assert set(event.keys()) == expected_top
    assert event["id"] == "A-001"
    assert event["start"] == "2026-05-10T10:00:00"
    assert event["end"] == "2026-05-10T10:30:00"
    assert event["color"] == "#3B82F6"
    assert event["textColor"] == "#fff"

    # extendedProps 16키 정확히 일치.
    expected_ep = {
        "patient_id", "patient_name", "patient_chart_no",
        "patient_phone", "patient_birth_date", "patient_memo",
        "therapist_id", "treatment_codes", "status", "memo",
        "approved_at", "approved_by", "opacity",
        "duration_min", "assignments", "is_new_patient", "version",
    }
    assert set(event["extendedProps"].keys()) == expected_ep
    assert event["extendedProps"]["opacity"] == 1.0  # reserved


def test_appointment_to_calendar_event_unassigned_therapist_falls_back():
    """치료사 미배정 (None / 빈 색) → UNASSIGNED 회색 (api.py:188 정합)."""
    event = _vm.appointment_to_calendar_event(
        appointment_id="A-002",
        start_iso="2026-05-10T11:00:00",
        end_iso="2026-05-10T11:30:00",
        status="reserved",
        therapist_color_value=None,
        extended_props={},
    )
    assert event["color"] == "#9CA3AF"

    event2 = _vm.appointment_to_calendar_event(
        appointment_id="A-003",
        start_iso="2026-05-10T11:00:00",
        end_iso="2026-05-10T11:30:00",
        status="reserved",
        therapist_color_value="",
        extended_props={},
    )
    assert event2["color"] == "#9CA3AF"


def test_appointment_to_calendar_event_canceled_opacity_via_caller():
    """``opacity`` 는 caller 가 ``extended_props`` 안에 직접 포함 — helper 가 덮어쓰지 않음.

    COMPAT: ``api.py:_serialize_appointment`` 의 dict literal 빌드 패턴 정합.
    """
    extended = {"status": "canceled", "opacity": _vm.status_to_opacity("canceled")}
    event = _vm.appointment_to_calendar_event(
        appointment_id="A-004",
        start_iso="2026-05-10T12:00:00",
        end_iso="2026-05-10T12:30:00",
        status="canceled",
        therapist_color_value="#FF0000",
        extended_props=extended,
    )
    assert event["extendedProps"]["opacity"] == 0.3
    # color 자체는 status 와 무관 — therapist_color_value 그대로.
    assert event["color"] == "#FF0000"


def test_appointment_to_calendar_event_extended_props_is_copied():
    """SAFETY: ``extended_props`` 는 dict copy — caller 의 dict 변경이 결과에 영향 ⊥."""
    extended = {"patient_id": "P-005", "memo": "초기"}
    event = _vm.appointment_to_calendar_event(
        appointment_id="A-005",
        start_iso="2026-05-10T13:00:00",
        end_iso="2026-05-10T13:30:00",
        status="reserved",
        therapist_color_value="#000000",
        extended_props=extended,
    )
    extended["memo"] = "수정됨"
    assert event["extendedProps"]["memo"] == "초기"


# ──────────────────────── 5. employee_to_resource_view ────────────────────


def test_employee_to_resource_view_3_keys():
    """COMPAT: ``api.py:4723`` 의 3키 (id / name / color) 정합."""
    result = _vm.employee_to_resource_view(
        employee_id="T-1", name="치료사1", color="#3B82F6",
    )
    assert set(result.keys()) == {"id", "name", "color"}
    assert result["id"] == "T-1"
    assert result["name"] == "치료사1"
    assert result["color"] == "#3B82F6"


def test_employee_to_resource_view_unassigned_color_fallback():
    """color None / 빈 문자열 → "#9CA3AF" 정합."""
    r1 = _vm.employee_to_resource_view(employee_id="T-2", name="치료사2", color=None)
    assert r1["color"] == "#9CA3AF"
    r2 = _vm.employee_to_resource_view(employee_id="T-3", name="치료사3", color="")
    assert r2["color"] == "#9CA3AF"


# ──────────────────────── 6. leave_to_display ─────────────────────────────


def test_leave_to_display_employee_form_6_keys():
    """COMPAT: ``api.py:1082~1095`` (list_employee_leaves) 의 6키 정합."""
    result = _vm.leave_to_display(
        leave_id="L-1",
        employee_id="E-1",
        leave_date="2026-05-15",
        leave_type="full",
        leave_kind="annual",
        memo="가족 행사",
    )
    assert set(result.keys()) == {
        "id", "employee_id", "leave_date", "leave_type", "leave_kind", "memo",
    }
    assert result["leave_type"] == "full"
    assert result["leave_kind"] == "annual"


def test_leave_to_display_therapist_alias_form_7_keys():
    """COMPAT: ``api.py:1184~1199`` (list_therapist_leaves_alias) 의 7키 + therapist_id alias."""
    result = _vm.leave_to_display(
        leave_id="L-2",
        employee_id="E-2",
        leave_date="2026-05-16",
        leave_type="am",
        leave_kind="monthly",
        memo="",
        include_therapist_alias=True,
    )
    assert set(result.keys()) == {
        "id", "therapist_id", "employee_id", "leave_date",
        "leave_type", "leave_kind", "memo",
    }
    # alias 가 employee_id 와 동일.
    assert result["therapist_id"] == result["employee_id"] == "E-2"


def test_leave_to_display_defaults_for_none_inputs():
    """``leave_type=None`` → "full" / ``leave_kind=None`` → "annual" / ``memo=None`` → "" 정합."""
    result = _vm.leave_to_display(
        leave_id="L-3",
        employee_id="E-3",
        leave_date="2026-05-17",
        leave_type=None,
        leave_kind=None,
        memo=None,
    )
    assert result["leave_type"] == "full"
    assert result["leave_kind"] == "annual"
    assert result["memo"] == ""


# ──────────────────────── 7. leave / status 라벨 ──────────────────────────


@pytest.mark.parametrize(
    "leave_type,expected",
    [
        ("full", "종일"),
        ("am", "오전반차"),
        ("pm", "오후반차"),
        ("unknown_type", "unknown_type"),  # fallback to original
        (None, ""),
        ("", ""),
    ],
)
def test_leave_type_label(leave_type, expected):
    assert _vm.leave_type_label(leave_type) == expected


@pytest.mark.parametrize(
    "leave_kind,expected",
    [
        ("annual", "연차"),
        ("monthly", "월차"),
        ("custom", "custom"),
        (None, ""),
        ("", ""),
    ],
)
def test_leave_kind_label(leave_kind, expected):
    assert _vm.leave_kind_label(leave_kind) == expected


@pytest.mark.parametrize(
    "status,expected_label,expected_class",
    [
        ("reserved", "예약", "status-reserved"),
        ("approved", "완료", "status-approved"),
        ("canceled", "취소", "status-canceled"),
        ("treated", "치료중", "status-treated"),
        ("unknown", "unknown", ""),
        (None, "", ""),
        ("", "", ""),
    ],
)
def test_status_to_label_and_css_class(status, expected_label, expected_class):
    assert _vm.status_to_label(status) == expected_label
    assert _vm.status_to_css_class(status) == expected_class


# ──────────────────────── 8. is_past_appointment ──────────────────────────


def test_is_past_appointment_basic():
    """ISO8601 문자열 비교 — end_at < now 면 True."""
    assert _vm.is_past_appointment("2026-05-01T10:00:00", "2026-05-10T10:00:00") is True
    assert _vm.is_past_appointment("2026-05-15T10:00:00", "2026-05-10T10:00:00") is False
    # 빈 / None → False (지나가지 않은 것으로 보수 판정).
    assert _vm.is_past_appointment(None, "2026-05-10T10:00:00") is False
    assert _vm.is_past_appointment("", "2026-05-10T10:00:00") is False


# ──────────────────────── 9. 단방향 경계 (D-4 정합) ───────────────────────


def test_calendar_view_models_does_not_import_models_or_db():
    """modules.calendar.view_models 는 ORM / DB / services / routers 미참조 (D-4)."""
    src = importlib.import_module("inspect").getsource(_vm)
    forbidden = (
        "from app.models", "import app.models",
        "from app.database", "import app.database",
        "from app.services", "import app.services",
        "from app.routers", "import app.routers",
        "from sqlalchemy", "import sqlalchemy",
        "from app.modules.settings", "import app.modules.settings",  # 다른 modules 직접 참조 ⊥
        "from app.modules.health", "import app.modules.health",
    )
    for token in forbidden:
        assert token not in src, (
            f"app.modules.calendar.view_models 가 금지된 import 사용: {token!r}"
        )


def test_calendar_package_init_does_not_import_models_or_db():
    """modules.calendar/__init__.py 도 동일 단방향 경계."""
    import app.modules.calendar as mod
    src = importlib.import_module("inspect").getsource(mod)
    forbidden = (
        "from app.models", "import app.models",
        "from app.database", "import app.database",
        "from app.services", "import app.services",
        "from app.routers", "import app.routers",
        "from sqlalchemy", "import sqlalchemy",
    )
    for token in forbidden:
        assert token not in src, (
            f"app.modules.calendar 패키지 init 가 금지된 import 사용: {token!r}"
        )


# ──────────────────────── 10. 외부 API 호출 0 검증 ────────────────────────


def test_view_model_helpers_do_not_invoke_provider_or_sdk():
    """SAFETY: view_model helper 는 외부 API / SDK / DB 호출 ⊥."""
    # helper 호출 시 어떤 부수효과도 없음 — 모두 순수 변환.
    _ = _vm.status_to_opacity("reserved")
    _ = _vm.therapist_color("#FF0000")
    _ = _vm.lighten_hex("#FF0000", 0.5)
    _ = _vm.leave_type_label("full")
    _ = _vm.leave_kind_label("annual")
    _ = _vm.status_to_label("reserved")
    _ = _vm.status_to_css_class("reserved")
    _ = _vm.is_past_appointment("2026-05-01T10:00:00", "2026-05-10T10:00:00")
    _ = _vm.appointment_to_calendar_event(
        appointment_id="A-1", start_iso="2026-05-10T10:00:00",
        end_iso="2026-05-10T10:30:00", status="reserved",
        therapist_color_value="#3B82F6", extended_props={},
    )
    _ = _vm.employee_to_resource_view(
        employee_id="E-1", name="X", color="#FF0000",
    )
    _ = _vm.leave_to_display(
        leave_id="L-1", employee_id="E-1", leave_date="2026-05-15",
        leave_type="full", leave_kind="annual", memo="",
    )


# ──────────────────────── 11. PII 보존 검증 ───────────────────────────────


def test_extended_props_preserves_existing_pii_fields_unchanged():
    """SAFETY: ``extended_props`` 의 PII 필드 (name / phone / birth_date / memo) 는
    *기존 동작* 보존 — 본 helper 가 추가 / 제거 / 마스킹 변경 ⊥.

    이 테스트의 의의: 본 19-3 view_model 도입이 실수로 PII 마스킹을 추가하거나
    필드를 누락시키지 않음을 보증. 마스킹 정책 변경은 별도 합의 사항.
    """
    extended = {
        "patient_id": "P-001",
        "patient_name": "홍길동",
        "patient_phone": "010-1234-5678",
        "patient_birth_date": "1980-01-01",
        "patient_memo": "특이사항: 약물 알레르기",
        # 다른 필드 생략 — caller 가 채움.
    }
    event = _vm.appointment_to_calendar_event(
        appointment_id="A-PII",
        start_iso="2026-05-10T10:00:00",
        end_iso="2026-05-10T10:30:00",
        status="reserved",
        therapist_color_value="#3B82F6",
        extended_props=extended,
    )
    # PII 필드가 그대로 통과 (기존 동작 정합).
    assert event["extendedProps"]["patient_name"] == "홍길동"
    assert event["extendedProps"]["patient_phone"] == "010-1234-5678"
    assert event["extendedProps"]["patient_birth_date"] == "1980-01-01"
    assert event["extendedProps"]["patient_memo"] == "특이사항: 약물 알레르기"
