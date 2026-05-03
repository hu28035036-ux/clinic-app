"""modules.leaves.service — 휴무 등록 / 직렬화 service helper (19-5 신규).

본 모듈은 ``app/routers/api.py:_upsert_employee_leave_core`` (line 1098) 의
*동등 service helper* + 휴무 응답 dict 빌더 (employee / therapist alias) 를 제공한다.

19-5 본 세션 범위:
  - ``upsert_employee_leave`` : ``_upsert_employee_leave_core`` 와 byte-equivalent.
    sync 로깅 (``_log``) 은 호출자가 주입 — 본 모듈 자체는 외부 부수효과 ⊥.
  - 응답 dict 빌더 (``serialize_employee_leave`` / ``serialize_therapist_leave_alias``)
    은 ``api.py:list_employee_leaves`` / ``list_therapist_leaves_alias`` 의 dict literal
    과 동등.
  - 라우터 미채택 (라우터 본체 무수정) — 19-9 시점 채택.

# COMPAT: ``api.py:_upsert_employee_leave_core`` 시그니처 / 동작 byte-equivalent.
#         라우터에서 본 helper 채택 ⊥ (19-9 시점). AI ``action_leave._do_upsert`` 가
#         계속 ``app.routers.api._upsert_employee_leave_core`` 를 import — 단일 진실원천
#         보존 (사용자 명시 "기존 휴무 AI 동작 변경 금지").

# SAFETY: 본 helper 가 *실제 DB 변경* 하지만, 라우터 / AI action_leave 가 미채택이므로
#         운영 흐름에 영향 ⊥. 19-9 시점 라우터가 채택할 때 commit / sync 로깅 정책
#         확인 필요. 환자 PII 미참조.

# NOTE: 본 helper 가 호출되면 ``db.flush()`` 까지만 수행 — commit 은 호출자 책임 (현재
#       라우터 패턴 정합). sync 로깅 (``_log``) 은 옵션 콜백 ``log_callback`` 으로 주입
#       가능 (라우터 채택 시 ``_log`` 호출 정합 보장).

# RISK: ``_upsert_employee_leave_core`` 는 휴무 등록의 *단일 진실원천* — 본 helper 가
#       19-9 시점 라우터 + AI action_leave 가 채택하기 전까지는 *parallel* 정의.
#       contract 테스트가 두 경로의 동등성을 검증.
"""
from __future__ import annotations

from typing import Any, Callable

from app.modules.leaves import rules as _rules


def upsert_employee_leave(
    db: Any,
    *,
    employee_id: str,
    leave_date: str,
    leave_type: str,
    leave_kind: str,
    memo: str = "",
    log_callback: Callable[[Any, str, str, str, Any], None] | None = None,
) -> Any:
    """동일 ``(employee_id, leave_date)`` 키면 update, 아니면 insert. ``commit`` ⊥.

    COMPAT: ``api.py:_upsert_employee_leave_core`` (line 1098) 와 byte-equivalent.
    sync 로깅은 ``log_callback`` 으로 주입 (라우터 채택 시 ``_log`` 호출 정합).

    인자:
      ``log_callback`` : ``_log(db, "employee_leave", obj.id, "upsert", obj)`` 와
                         같은 시그니처. None 이면 sync 로깅 ⊥ (라우터 미채택 시).

    NOTE: caller 가 ``commit`` / ``refresh`` 책임. 본 helper 는 ``flush`` 까지만.
    """
    from app.models import models as _m

    exists = (
        db.query(_m.EmployeeLeave)
        .filter(
            _m.EmployeeLeave.employee_id == employee_id,
            _m.EmployeeLeave.leave_date == leave_date,
        )
        .first()
    )
    if exists is not None:
        exists.leave_type = leave_type
        exists.leave_kind = leave_kind
        exists.memo = memo
        db.flush()
        if log_callback is not None:
            log_callback(db, "employee_leave", exists.id, "upsert", exists)
        return exists

    obj = _m.EmployeeLeave(
        employee_id=employee_id,
        leave_date=leave_date,
        leave_type=leave_type,
        leave_kind=leave_kind,
        memo=memo,
    )
    db.add(obj)
    db.flush()
    if log_callback is not None:
        log_callback(db, "employee_leave", obj.id, "upsert", obj)
    return obj


# ─── 응답 dict 빌더 (api.py 의 dict literal 과 동등) ─────────────────────────


def serialize_employee_leave(obj: Any) -> dict:
    """``EmployeeLeave`` ORM → 6키 응답 dict.

    COMPAT: ``api.py:list_employee_leaves`` (line 1088~1095) + ``create_employee_leave``
    (line 1125~1130) 의 dict literal 과 byte-equivalent. 6키:
    ``id / employee_id / leave_date / leave_type / leave_kind / memo``.
    leave_type / leave_kind 의 빈 값 fallback 정합 (full / annual).
    """
    return {
        "id": obj.id,
        "employee_id": obj.employee_id,
        "leave_date": obj.leave_date,
        "leave_type": _rules.normalize_leave_type(obj.leave_type),
        "leave_kind": _rules.normalize_leave_kind(obj.leave_kind),
        "memo": obj.memo or "",
    }


def serialize_therapist_leave_alias(obj: Any) -> dict:
    """``EmployeeLeave`` ORM → 7키 응답 dict (``therapist_id`` alias 포함).

    COMPAT: ``api.py:list_therapist_leaves_alias`` (line 1191~1199) 와 byte-equivalent.
    7키: ``id / therapist_id / employee_id / leave_date / leave_type / leave_kind / memo``.
    프론트 호환을 위해 ``therapist_id`` 가 ``employee_id`` 와 동일 값으로 이중 노출.
    """
    return {
        "id": obj.id,
        "therapist_id": obj.employee_id,
        "employee_id": obj.employee_id,
        "leave_date": obj.leave_date,
        "leave_type": _rules.normalize_leave_type(obj.leave_type),
        "leave_kind": _rules.normalize_leave_kind(obj.leave_kind),
        "memo": obj.memo or "",
    }


__all__ = [
    "upsert_employee_leave",
    "serialize_employee_leave",
    "serialize_therapist_leave_alias",
]
