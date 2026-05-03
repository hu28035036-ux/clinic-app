"""modules.leaves.repository — 휴무 row 조회 read-only helper (19-5 신규).

본 모듈은 ``EmployeeLeave`` 테이블의 *조회 전용* 함수만 제공한다. 실제 변경
(create / update / delete) 은 ``leaves.service`` 또는 라우터 책임.

19-5 본 세션 범위:
  - 같은 날짜 / 같은 직원 / availability 가 호출 가능한 read-only helper.
  - DB 세션은 호출자가 주입 — 운영 DB 직접 open ⊥.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:list_employee_leaves`` (line 1082) / ``list_therapist_leaves_alias``
#         (line 1184) 의 조회 패턴과 동등. 응답 dict 빌드는 ``leaves.service`` 가 담당.

# SAFETY: 운영 DB 직접 접근 ⊥ — caller dependency 의 격리 세션만 사용. 환자 PII
#         미참조 (employee_id / leave_date / leave_type / leave_kind / memo 만).
"""
from __future__ import annotations

from typing import Any


def list_leaves_for_date(db: Any, leave_date: str | None) -> list[Any]:
    """주어진 날짜의 휴무 row 조회 (date 미지정 시 전체).

    COMPAT: ``api.py:list_employee_leaves`` (line 1083~1087) 의 query 패턴 정합 —
    ``leave_date asc`` 정렬.
    """
    from app.models import models as _m

    q = db.query(_m.EmployeeLeave)
    if leave_date:
        q = q.filter(_m.EmployeeLeave.leave_date == leave_date)
    return q.order_by(_m.EmployeeLeave.leave_date.asc()).all()


def get_leave_for_employee_date(
    db: Any,
    *,
    employee_id: str,
    leave_date: str,
) -> Any | None:
    """특정 직원 + 날짜의 휴무 row (UNIQUE 제약).

    COMPAT: ``api.py:_upsert_employee_leave_core`` (line 1104~1107) 의 ``filter`` 와 동등.
    m011 ``(employee_id, leave_date)`` UNIQUE 정합.
    """
    from app.models import models as _m

    return (
        db.query(_m.EmployeeLeave)
        .filter(
            _m.EmployeeLeave.employee_id == employee_id,
            _m.EmployeeLeave.leave_date == leave_date,
        )
        .first()
    )


def get_leave_by_id(db: Any, leave_id: str) -> Any | None:
    """ID 로 휴무 row 조회.

    COMPAT: ``api.py:delete_employee_leave`` (line 1135) 의 ``db.get(EmployeeLeave, lid)`` 와 동등.
    """
    from app.models import models as _m

    return db.get(_m.EmployeeLeave, leave_id)


def list_leaves_for_employee_date_range(
    db: Any,
    *,
    employee_id: str,
    start_date: str,
    end_date: str,
) -> list[Any]:
    """특정 직원 + 날짜 범위의 휴무 row.

    NOTE: availability 검사 시 같은 날짜 한 건만 매치되지만, 향후 다일 휴무 (m014+)
    도입 시점에 확장 자리. 현재는 ``leave_date == today`` 단일 매치로 충분.
    """
    from app.models import models as _m

    return (
        db.query(_m.EmployeeLeave)
        .filter(
            _m.EmployeeLeave.employee_id == employee_id,
            _m.EmployeeLeave.leave_date >= start_date,
            _m.EmployeeLeave.leave_date <= end_date,
        )
        .order_by(_m.EmployeeLeave.leave_date.asc())
        .all()
    )


__all__ = [
    "list_leaves_for_date",
    "get_leave_for_employee_date",
    "get_leave_by_id",
    "list_leaves_for_employee_date_range",
]
