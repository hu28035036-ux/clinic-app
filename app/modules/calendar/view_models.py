"""modules.calendar.view_models — 캘린더 표시용 순수 helper (19-3 신규).

본 모듈은 ``_serialize_appointment`` / ``_serialize_employee`` / ``_lighten_hex`` /
``list_employee_leaves`` / ``list_therapist_leaves_alias`` 등 ``app/routers/api.py``
의 *표시용 데이터 조립* 로직을 *동등한 순수 helper* 로 추출한다.

19-3 본 세션 범위:
  - 표시용 helper 만 정의 — 기존 응답 dict 와 byte-equivalent 결과 보장.
  - DB / ORM import ⊥ — 본 모듈은 primitives 또는 ORM attribute 만 read.
  - 신규 저장소 / 신규 router 추가 ⊥.
  - 예약 저장 / 수정 / 삭제 로직 ⊥. 휴무 차단 규칙 ⊥. availability 판단 ⊥.

# COMPAT: ``app/routers/api.py:_serialize_appointment`` (라인 186~219) 와 결과 dict
#         (9 top-level + 16 extendedProps 키) byte-equivalent. 라우터에서 본 helper
#         를 import 하지 않아도 기존 응답 무변경 (DEC-C 정합).

# SAFETY: 환자 PII (``patient_name`` / ``patient_phone`` / ``patient_birth_date`` /
#         ``patient_memo``) 가 ``extendedProps`` 에 포함되는 것은 *기존 동작 보존* —
#         본 19-3 이 PII 추가 / 제거 / 마스킹 변경 ⊥. 로그 / audit_log 에 원문
#         부재 (기존 정책 — `pii.scan` + sha256 정합).

# NOTE: 예약 *저장* 로직 (POST/PUT/DELETE /api/appointments) 과 *표시* 로직을 분리
#       하는 이유 — appointments 본체 분리 (19-9) 시 view_model 이 별도 모듈로
#       유지되어야 의존성 그래프가 단방향 (D-4 정합) 으로 정리. 19-3 시점에는
#       "facade 신설 + 라우터 무수정" — 19-9 가 이 view_model 을 채택.

# RISK: FullCalendar event ID / start / end / status / version / treatment_codes /
#       extendedProps 키 변경 ⊥ — main.html 인라인 JS 의존. 본 helper 출력이
#       기존 dict 와 byte-equivalent 인지 19-3 contract 테스트가 회귀 보호.
"""
from __future__ import annotations

from typing import Any, Final


# ─── 표시용 색상 상수 (api.py 내 inline literal 추출) ────────────────────────

# 치료사 미배정 / 색상 미설정 시 fallback (gray) — api.py:188 / 3789 / 3839 /
# 4501 / 4524 / 4723 의 "#9CA3AF" 인라인 사용.
UNASSIGNED_THERAPIST_COLOR: Final[str] = "#9CA3AF"

# 엑셀 export 의 "미배정" 컬럼 색 (purple) — api.py:4418 의 UNASSIGNED_HEX.
UNASSIGNED_COLUMN_COLOR: Final[str] = "#8B5CF6"

# FullCalendar event textColor — api.py:198 의 "#fff" 인라인.
DEFAULT_EVENT_TEXT_COLOR: Final[str] = "#fff"


# ─── 예약 status → opacity 매핑 (api.py:189 인라인 dict 추출) ─────────────────

# COMPAT: ``_serialize_appointment`` 의 ``opacity = {...}.get(a.status, 1.0)`` 와
# byte-equivalent. 추가 status 가 들어오면 1.0 (default) — canceled 만 0.3.
STATUS_OPACITY: Final[dict[str, float]] = {
    "reserved": 1.0,
    "approved": 1.0,
    "canceled": 0.3,
}

DEFAULT_OPACITY: Final[float] = 1.0


def status_to_opacity(status: str | None) -> float:
    """``a.status`` → FullCalendar event opacity.

    COMPAT: ``api.py:189`` 의 ``{"reserved": 1.0, "approved": 1.0, "canceled": 0.3}.get(a.status, 1.0)``
    와 byte-equivalent.
    """
    if status is None:
        return DEFAULT_OPACITY
    return STATUS_OPACITY.get(status, DEFAULT_OPACITY)


# ─── 치료사 색상 fallback ─────────────────────────────────────────────────────


def therapist_color(employee_color: str | None) -> str:
    """치료사 색상 (없으면 UNASSIGNED 회색 fallback).

    COMPAT: ``api.py:188`` (``a.therapist.color if a.therapist else "#9CA3AF"``)
    + ``api.py:3789`` (``t.color or "#9CA3AF"``) + ``api.py:4501`` 등 정합.
    빈 문자열도 None 과 동일 처리.
    """
    if not employee_color:
        return UNASSIGNED_THERAPIST_COLOR
    return employee_color


# ─── 색상 lighten (엑셀 export 표시용) ────────────────────────────────────────


def lighten_hex(hex_color: str, factor: float) -> str:
    """``#RRGGBB`` → 흰색 쪽으로 ``factor`` (0~1) 만큼 블렌드한 ``RRGGBB`` (``#`` 없이).

    factor=0 → 원색, factor=1 → 흰색.

    COMPAT: ``api.py:4316~4330`` ``_lighten_hex`` 와 byte-equivalent. 잘못된
    형식 (6자 아니거나 hex 파싱 실패) 은 ``"FFFFFF"`` (흰색) fallback.
    """
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


# ─── 휴무 표시 라벨 (일자별 휴무자 표시용) ──────────────────────────────────


# leave_type 코드 → 화면 표시 라벨 (UI / 캘린더 휴무자 표시용).
# COMPAT: 기존 프론트 JS 가 leave_type 원문을 받아 표시하지만, post-19-P 의
# UI 분리 / API 응답 통합 시점에 본 라벨이 *서버 사이드 단일 진실원천* 으로
# 채택될 후보. 19-3 시점에는 *helper 만 정의*, 라우터 미채택.
LEAVE_TYPE_LABELS: Final[dict[str, str]] = {
    "full": "종일",
    "am": "오전반차",
    "pm": "오후반차",
}

# leave_kind 코드 → 화면 표시 라벨.
LEAVE_KIND_LABELS: Final[dict[str, str]] = {
    "annual": "연차",
    "monthly": "월차",
}


def leave_type_label(leave_type: str | None) -> str:
    """``leave_type`` (full / am / pm) → 화면 표시 라벨.

    NOTE: 알 수 없는 값은 그대로 반환 (기존 JS 가 원문을 표시하는 동작 정합).
    """
    if not leave_type:
        return ""
    return LEAVE_TYPE_LABELS.get(leave_type, leave_type)


def leave_kind_label(leave_kind: str | None) -> str:
    """``leave_kind`` (annual / monthly) → 화면 표시 라벨."""
    if not leave_kind:
        return ""
    return LEAVE_KIND_LABELS.get(leave_kind, leave_kind)


# ─── 예약 상태 표시용 label / CSS class ───────────────────────────────────────

# COMPAT: 기존 JS 의 stMark = `{reserved:'📅', treated:'✓', approved:'✅',
# canceled:'❌'}[ep.status]` 와 정합 (main.html 인라인). 본 helper 는 *서버
# 사이드* 단일 진실원천 후보 — 19-3 시점에는 frontend 무수정, 라우터 미채택.
STATUS_DISPLAY_LABELS: Final[dict[str, str]] = {
    "reserved": "예약",
    "approved": "완료",
    "canceled": "취소",
    "treated": "치료중",
}

STATUS_CSS_CLASSES: Final[dict[str, str]] = {
    "reserved": "status-reserved",
    "approved": "status-approved",
    "canceled": "status-canceled",
    "treated": "status-treated",
}


def status_to_label(status: str | None) -> str:
    """``status`` → 한국어 표시 라벨.

    NOTE: 알 수 없는 값은 그대로 반환.
    """
    if not status:
        return ""
    return STATUS_DISPLAY_LABELS.get(status, status)


def status_to_css_class(status: str | None) -> str:
    """``status`` → CSS class 이름.

    NOTE: 알 수 없는 값은 빈 문자열 — JS 가 추가 클래스 부여 안 함.
    """
    if not status:
        return ""
    return STATUS_CSS_CLASSES.get(status, "")


# ─── 지나간 일정 / 다가오는 일정 분류 (시간 비교) ────────────────────────────


def is_past_appointment(end_at_iso: str | None, now_iso: str) -> bool:
    """예약 종료시각 < now → 지나간 일정 (회색 처리 후보).

    NOTE: 본 helper 는 *시간 비교만* — 실제 회색 처리 / opacity 변경은 프론트가
    결정. 19-3 시점에는 wire 안 함, 향후 view_model 채택용.
    SAFETY: 시간 형식 파싱 실패 시 False (지나가지 않은 것으로 보수 판정).
    """
    if not end_at_iso:
        return False
    try:
        return end_at_iso < now_iso
    except Exception:
        return False


# ─── 캘린더 이벤트 view-model 조립 (api.py:_serialize_appointment 와 동등) ────


def appointment_to_calendar_event(
    *,
    appointment_id: str,
    start_iso: str,
    end_iso: str,
    status: str | None,
    therapist_color_value: str | None,
    extended_props: dict[str, Any],
) -> dict[str, Any]:
    """``Appointment`` ORM 인스턴스 (caller 가 dict 로 변환) → FullCalendar event dict.

    COMPAT: ``api.py:_serialize_appointment`` (라인 186~219) 와 *키 / 값 / 타입* 100%
    일치. 9 top-level 키 (``id / start / end / color / textColor / extendedProps``)
    + caller 가 만든 ``extended_props`` (16키 — patient_id / patient_name /
    patient_chart_no / patient_phone / patient_birth_date / patient_memo /
    therapist_id / treatment_codes / status / memo / approved_at / approved_by /
    opacity / duration_min / assignments / is_new_patient / version).

    NOTE: caller 가 ``extended_props`` 안의 ``opacity`` 를 미리 포함 / 미포함 모두
    허용 — 본 helper 는 ``status`` 로부터 ``opacity`` 를 *덮어쓰지 않음*.
    ``api.py`` 의 dict literal 빌더가 status 별 opacity 를 직접 계산해 dict 안에
    포함시키는 패턴 정합 — 본 helper 는 *조립* 만 담당, 정책 결정은 caller.

    SAFETY: ``extended_props`` 안에 환자 PII (name / phone / birth_date / memo)
    가 포함되는 것은 *기존 동작 보존*. 본 helper 가 PII 마스킹 변경 ⊥ — caller
    가 책임. 로그 / audit_log 에는 원문 부재 (기존 정책).
    """
    return {
        "id": appointment_id,
        "start": start_iso,
        "end": end_iso,
        "color": therapist_color(therapist_color_value),
        "textColor": DEFAULT_EVENT_TEXT_COLOR,
        "extendedProps": dict(extended_props),
    }


# ─── 직원 / 치료사 view-model (api.py:_serialize_employee 와 동등) ────────────


def employee_to_resource_view(
    *,
    employee_id: str,
    name: str,
    color: str | None,
) -> dict[str, Any]:
    """치료사 / 직원 → 캘린더 resource view 표시 dict (id / name / color).

    COMPAT: ``api.py:4723`` (``{"id": t.id, "name": t.name, "color": t.color or
    "#9CA3AF"}``) 와 byte-equivalent. ``api.py:_serialize_employee`` 의 *전체* 9키
    (id/name/role/color/active/birth_date/phone/hire_date/can_eswt/can_manual/
    sort_order) 가 아니라 *캘린더 색상 표시용 3키* 만 — caller 가 다른 필드를
    추가하면 dict 합쳐 사용.
    """
    return {
        "id": employee_id,
        "name": name,
        "color": therapist_color(color),
    }


# ─── 휴무 view-model (api.py:list_employee_leaves / list_therapist_leaves_alias) ───


def leave_to_display(
    *,
    leave_id: str,
    employee_id: str,
    leave_date: str,
    leave_type: str | None,
    leave_kind: str | None,
    memo: str | None,
    include_therapist_alias: bool = False,
) -> dict[str, Any]:
    """휴무 ORM → 화면 표시 dict.

    COMPAT: ``include_therapist_alias=False`` → ``api.py:1082~1095``
    (list_employee_leaves) 의 6키. ``include_therapist_alias=True`` →
    ``api.py:1184~1199`` (list_therapist_leaves_alias) 의 7키 (``therapist_id``
    이중 키 — 프론트 호환).

    NOTE: 휴무 *차단 규칙* 은 19-5 leaves 분리 시점. 본 helper 는 *표시* 만.
    """
    out: dict[str, Any] = {
        "id": leave_id,
        "employee_id": employee_id,
        "leave_date": leave_date,
        "leave_type": leave_type or "full",
        "leave_kind": leave_kind or "annual",
        "memo": memo or "",
    }
    if include_therapist_alias:
        # COMPAT: 프론트 호환 alias — therapist_id 이중 키.
        out["therapist_id"] = employee_id
    return out


__all__ = [
    # 색상 상수
    "UNASSIGNED_THERAPIST_COLOR",
    "UNASSIGNED_COLUMN_COLOR",
    "DEFAULT_EVENT_TEXT_COLOR",
    # opacity
    "STATUS_OPACITY",
    "DEFAULT_OPACITY",
    "status_to_opacity",
    # 색상 helper
    "therapist_color",
    "lighten_hex",
    # 휴무 라벨
    "LEAVE_TYPE_LABELS",
    "LEAVE_KIND_LABELS",
    "leave_type_label",
    "leave_kind_label",
    # 상태 라벨 / class
    "STATUS_DISPLAY_LABELS",
    "STATUS_CSS_CLASSES",
    "status_to_label",
    "status_to_css_class",
    # 시간 비교
    "is_past_appointment",
    # view-model 조립
    "appointment_to_calendar_event",
    "employee_to_resource_view",
    "leave_to_display",
]
