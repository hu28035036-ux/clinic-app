"""modules.therapists.service — 직원 / 치료사 직렬화 service helper (19-8 신규).

본 모듈은 ``api.py:_serialize_employee`` (line 169) 의 *동등 helper* + 통계
``id → name`` 맵 빌더 + 도수치료 표 / 캘린더 resource view 를 제공한다.
라우터 무수정 — 19-9 시점 채택 후보.

19-8 본 세션 범위:
  - 직원 응답 dict 빌더 (10키) — byte-equivalent.
  - 치료사 alias 응답 dict 빌더 (``/api/therapists`` 흐름 정합).
  - 통계 ``id → name`` 맵 + ``"미배정"`` sentinel 합산 helper.
  - 캘린더 resource view dict 빌더 (3키 — id/name/color, 단순 view 용).
  - 라우터 미채택 (라우터 본체 무수정).

# COMPAT: ``api.py:_serialize_employee`` (line 169~176) — 10키 dict 와 byte-equivalent.
#         ``api.py:list_employees`` (line 1018) / ``list_therapists_alias`` (line 1181) /
#         통계 ``id → name`` 매핑 (line 3527 / 3609 / 3702 / 3787) / 도수치료 표
#         (line 4364 / 4619) 모두 본 helper 와 동등 결과.

# SAFETY: 본 helper 는 *기존 직원 응답 dict 그대로* — 직원 모달 / 캘린더 / 통계
#         흐름이 의존. 본 19-8 이 응답 키 / 타입 변경 ⊥. 환자 PII 미참조.

# NOTE: ``_serialize_employee`` 의 10키:
#       id / name / role / color / active / birth_date / phone / hire_date /
#       can_eswt / can_manual / sort_order. 본 helper 가 *그대로* 보존.

# RISK: 응답 dict 키 변경 ⊥ — UI / 캘린더 / 통계 모두 의존. 도수치료 표 셀 색상
#       빌더 (api.py:4906~4911) 도 ``t["color"]`` 를 받으므로 본 직렬화 결과의
#       color fallback 정합 필수.
"""
from __future__ import annotations

from typing import Any

from app.modules.therapists import rules as _rules


# ─── Employee → 응답 dict (api.py:_serialize_employee 동등) ──────────────────


def serialize_employee(employee: Any) -> dict[str, Any]:
    """``Employee`` ORM → 10키 응답 dict.

    COMPAT: ``api.py:_serialize_employee`` (line 169~176) 와 byte-equivalent.
    10키: ``id / name / role / color / active / birth_date / phone / hire_date /
    can_eswt / can_manual / sort_order``.

    NOTE: ``e.color`` 는 *그대로* 노출 — caller 가 fallback 결정 (현재 라우터는
    color column NOT NULL DEFAULT ``"#9CA3AF"`` 로 fallback 보장 — m001 정합).
    ``e.active`` / ``e.can_eswt`` / ``e.can_manual`` 은 ``bool()`` 정규화.
    """
    return {
        "id": employee.id,
        "name": employee.name,
        "role": employee.role,
        "color": employee.color,
        "active": _rules.is_active_employee(employee.active),
        "birth_date": employee.birth_date,
        "phone": employee.phone,
        "hire_date": employee.hire_date,
        "can_eswt": _rules.can_handle_eswt(employee.can_eswt),
        "can_manual": _rules.can_handle_manual(employee.can_manual),
        "sort_order": employee.sort_order or 0,
    }


def serialize_employees(employees: list[Any]) -> list[dict[str, Any]]:
    """``list[Employee]`` → ``list[dict]``.

    COMPAT: ``api.py:list_employees`` (line 1018) /
    ``list_therapists_alias`` (line 1181) 의 list comprehension 정합.
    """
    return [serialize_employee(e) for e in employees]


# ─── 통계 id → name 매핑 + 미배정 합산 (api.py 통계 빌더 정합) ────────────────


def build_employee_name_map(
    employees: list[Any],
    *,
    include_unassigned: bool = True,
) -> dict[str, str]:
    """``list[Employee]`` → ``{employee_id: name}`` 매핑.

    COMPAT: ``api.py:3527`` (``{t.id: t.name for t in db.query(Employee).all()}``) /
    ``api.py:3525`` (``role == "doctor"`` 분기) / ``api.py:3609`` / ``api.py:3702``
    / ``api.py:3788`` 정합. ``include_unassigned=True`` 면 ``UNASSIGNED_SENTINEL`` =
    ``UNASSIGNED_LABEL`` 항목 추가.

    NOTE: 통계 / 일별 차트 빌더가 ``a.therapist_id or "__none__"`` 으로 미배정 슬롯을
    같은 sentinel 키에 모음 — caller 가 ``include_unassigned=True`` 로 쉽게 추가.
    """
    name_map = {e.id: e.name for e in employees}
    if include_unassigned:
        name_map[_rules.UNASSIGNED_SENTINEL] = _rules.UNASSIGNED_LABEL
    return name_map


def build_employee_color_map(
    employees: list[Any],
    *,
    include_unassigned: bool = True,
) -> dict[str, str]:
    """``list[Employee]`` → ``{employee_id: color}`` 매핑 (fallback 적용).

    COMPAT: ``api.py:3789`` (``{t.id: (t.color or "#9CA3AF") for t in
    therapist_list}``) 정합. 빈 색상 / None → ``DEFAULT_THERAPIST_COLOR``.
    ``include_unassigned=True`` 면 미배정 sentinel 도 fallback 색으로 추가.
    """
    color_map = {
        e.id: _rules.therapist_color_or_default(e.color) for e in employees
    }
    if include_unassigned:
        color_map[_rules.UNASSIGNED_SENTINEL] = _rules.DEFAULT_THERAPIST_COLOR
    return color_map


# ─── 캘린더 resource view (api.py:4723 정합) ─────────────────────────────────


def build_therapist_resource_view(employee: Any) -> dict[str, Any]:
    """치료사 → 캘린더 resource view 표시 dict (id / name / color).

    COMPAT: ``api.py:4723`` (``{"id": t.id, "name": t.name, "color": t.color or
    "#9CA3AF"}``) 와 byte-equivalent. 19-3 ``calendar.view_models.employee_to_resource_view``
    와 동일 결과.

    NOTE: 도수치료 표 컬럼 / 캘린더 resource lane 표시용 *3키* — caller 가 다른
    필드 (canMmanual / sort_order 등) 가 필요하면 ``serialize_employee`` 사용.
    """
    return {
        "id": employee.id,
        "name": employee.name,
        "color": _rules.therapist_color_or_default(employee.color),
    }


def build_therapist_resource_views(employees: list[Any]) -> list[dict[str, Any]]:
    """``list[Employee]`` → ``list[resource view dict]`` (3키).

    COMPAT: ``api.py:3867~3870`` 통계 일별 ``therapists`` 리스트 +
    ``api.py:4707~4711`` 도수치료 표 시간 헤더 정합.
    """
    return [build_therapist_resource_view(e) for e in employees]


# ─── 신규 직원 sort_order 자동 할당 (api.py:create_employee 정합) ─────────────


def next_sort_order_for_role(*, current_count_for_role: int) -> int:
    """역할별 sort_order 자동 할당 — ``count + 1``.

    COMPAT: ``api.py:create_employee`` (line 1038~1042) 의
    ``max_order = db.query(...).filter(role == p.role).count(); e.sort_order =
    max_order + 1`` 정합. 본 helper 는 *primitives* 만 받음 — DB 호출은 caller.
    """
    return int(current_count_for_role) + 1


__all__ = [
    "serialize_employee",
    "serialize_employees",
    "build_employee_name_map",
    "build_employee_color_map",
    "build_therapist_resource_view",
    "build_therapist_resource_views",
    "next_sort_order_for_role",
]
