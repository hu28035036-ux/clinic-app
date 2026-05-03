"""modules.therapists.repository — 직원 row read-only 조회 helper (19-8 신규).

본 모듈은 ``Employee`` 테이블의 *조회 전용* 함수만 제공한다. 실제 변경
(create / update / delete) 은 라우터 책임 (19-9 시점 채택 후보).

19-8 본 세션 범위:
  - 단건 / 전체 / 역할 필터 / 활성 필터 조회 helper.
  - 통계 / 캘린더 / 도수치료 표 / 휴무 흐름이 사용하는 query 패턴을 단일 진실원천에 모음.
  - DB 세션은 호출자 주입 — 운영 DB 직접 open ⊥, lazy import.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:list_employees`` (line 1009) / ``list_therapists_alias``
#         (line 1175) / 통계 ``id→name`` 매핑 query (line 3525 / 3527 / 3609 /
#         3702 / 3787) / 도수치료 표 (line 4364 / 4619) 의 query 패턴 정합.

# SAFETY: 운영 DB 직접 접근 ⊥ — caller dependency 의 격리 세션만 사용. 환자 PII
#         미참조 (employee 정보만). 외부 API 호출 ⊥.

# NOTE: 본 repository 의 정렬 기준은 ``api.py`` 의 *기존 동작* 정합:
#       - ``list_employees`` : ``sort_order, name`` (api.py:1017).
#       - ``list_therapists_alias`` : ``name`` (api.py:1180).
#       - 도수치료 표 (manual scheduler) : ``sort_order, name`` (api.py:4369).
"""
from __future__ import annotations

from typing import Any


def list_all_employees(
    db: Any,
    *,
    role: str | None = None,
    active: bool | None = None,
) -> list[Any]:
    """직원 목록 조회 (sort_order, name 순).

    COMPAT: ``api.py:list_employees`` (line 1009~1018) 의 query 패턴 정합 —
    ``role`` 빈 값 / None → 필터 미적용, ``active`` None → 필터 미적용,
    ``sort_order, name`` 정렬.
    """
    from app.models import models as _m

    q = db.query(_m.Employee)
    if role:
        q = q.filter(_m.Employee.role == role)
    if active is not None:
        q = q.filter(_m.Employee.active == active)
    return q.order_by(_m.Employee.sort_order, _m.Employee.name).all()


def get_employee_by_id(db: Any, employee_id: str) -> Any | None:
    """ID 로 단건 직원 조회.

    COMPAT: ``api.py:update_employee`` (line 1052) / ``delete_employee``
    (line 1070) ``db.get(Employee, eid)`` 정합.
    """
    from app.models import models as _m

    return db.get(_m.Employee, employee_id)


def list_therapists(db: Any, *, active: bool | None = None) -> list[Any]:
    """치료사 (role=therapist) 목록 (name 순).

    COMPAT: ``api.py:list_therapists_alias`` (line 1175~1181) 의 query 정합 —
    ``Employee.name`` 단일 정렬. ``active`` None → 활성/비활성 모두 포함.
    """
    from app.models import models as _m
    from app.modules.therapists import rules as _rules

    q = db.query(_m.Employee).filter(_m.Employee.role == _rules.ROLE_THERAPIST)
    if active is not None:
        q = q.filter(_m.Employee.active == active)
    return q.order_by(_m.Employee.name).all()


def list_doctors(db: Any, *, active: bool | None = None) -> list[Any]:
    """의사 (role=doctor) 목록 (name 순).

    COMPAT: ``api.py:3525`` (``models.Employee.role == "doctor"``) 의 query 패턴
    정합. ``active`` None → 활성/비활성 모두 포함.

    NOTE: 현재 의사 *전용* 표시 / 진료 흐름 ⊥. 본 helper 는 통계 ``stats_by_therapist``
    의 doctor 필터 분기에서 ``id → name`` 매핑 빌드용.
    """
    from app.models import models as _m
    from app.modules.therapists import rules as _rules

    q = db.query(_m.Employee).filter(_m.Employee.role == _rules.ROLE_DOCTOR)
    if active is not None:
        q = q.filter(_m.Employee.active == active)
    return q.order_by(_m.Employee.name).all()


def list_therapists_for_manual_scheduler(db: Any) -> list[Any]:
    """도수치료 표 / 캘린더용 활성 치료사 (sort_order, name 순).

    COMPAT: ``api.py:4364~4369`` (``role=='therapist' AND active=True AND
    can_manual=True``) 의 query 정합. 도수치료 컬럼 / 캘린더 resource 표시용.
    """
    from app.models import models as _m
    from app.modules.therapists import rules as _rules

    return (
        db.query(_m.Employee)
        .filter(
            _m.Employee.role == _rules.ROLE_THERAPIST,
            _m.Employee.active == True,  # noqa: E712 — SQLAlchemy expr
            _m.Employee.can_manual == True,  # noqa: E712 — SQLAlchemy expr
        )
        .order_by(_m.Employee.sort_order, _m.Employee.name)
        .all()
    )


def list_active_therapists(db: Any) -> list[Any]:
    """활성 치료사 (role=therapist AND active=True) — 통계 / 일별 차트용.

    COMPAT: ``api.py:3783~3786`` (``models.Employee.role == "therapist", active ==
    True``) 의 query 패턴 정합. ``Employee.name`` 단일 정렬.
    """
    from app.models import models as _m
    from app.modules.therapists import rules as _rules

    return (
        db.query(_m.Employee)
        .filter(
            _m.Employee.role == _rules.ROLE_THERAPIST,
            _m.Employee.active == True,  # noqa: E712 — SQLAlchemy expr
        )
        .order_by(_m.Employee.name)
        .all()
    )


def get_employees_by_ids(db: Any, employee_ids: list[str]) -> list[Any]:
    """``employee_ids`` 안의 직원 일괄 조회 — 통계 ``in_`` 패턴.

    COMPAT: ``api.py:1552`` (``models.Employee.id.in_(emp_ids)``) 의 query 정합.
    빈 리스트면 빈 결과 반환 (caller 가 ``in_([])`` 호출하지 않도록 분기).
    """
    from app.models import models as _m

    if not employee_ids:
        return []
    return (
        db.query(_m.Employee)
        .filter(_m.Employee.id.in_(employee_ids))
        .all()
    )


def count_employees_by_role(db: Any, role: str) -> int:
    """역할별 직원 개수 — sort_order 자동 부여 시 사용.

    COMPAT: ``api.py:create_employee`` (line 1038~1040) 의
    ``models.Employee.role == p.role`` count 정합.
    """
    from app.models import models as _m

    return db.query(_m.Employee).filter(_m.Employee.role == role).count()


__all__ = [
    "list_all_employees",
    "get_employee_by_id",
    "list_therapists",
    "list_doctors",
    "list_therapists_for_manual_scheduler",
    "list_active_therapists",
    "get_employees_by_ids",
    "count_employees_by_role",
]
