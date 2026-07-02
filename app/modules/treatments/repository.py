"""modules.treatments.repository — 치료항목 read-only 조회 helper (19-6 신규).

본 모듈은 ``Treatment`` 테이블의 *조회 전용* 함수만 제공한다. 실제 변경 (create /
update / delete) 은 라우터 책임 (19-9 / 19-11 시점에 service 가 채택).

19-6 본 세션 범위:
  - 모든 치료항목 / 활성만 / 도수만 / role 별 조회 helper.
  - DB 세션은 호출자 주입 — 운영 DB 직접 open ⊥.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:_all_treatments`` (line 139) / ``_get_manual_treatment_rows``
#         (line 3732) / ``_build_treatment_meta`` (line 816) 의 query 패턴 정합.

# SAFETY: 운영 DB 직접 접근 ⊥ — caller dependency 의 격리 세션만 사용. 환자 PII
#         미참조 (Treatment 테이블은 환자 데이터 부재).
"""
from __future__ import annotations

from typing import Any


def list_all_treatments(db: Any) -> list:
    """모든 치료항목 (활성+비활성) 조회.

    COMPAT: ``api.py:_all_treatments`` (line 139) 와 동등.
    """
    from app.models import models as _m

    return db.query(_m.Treatment).all()


def list_treatments_sorted(db: Any) -> list:
    """모든 치료항목을 sort_order 정렬로 조회.

    COMPAT: ``api.py:_build_treatment_meta`` (line 818) 의 query 패턴 정합.
    """
    from app.models import models as _m

    return db.query(_m.Treatment).order_by(_m.Treatment.sort_order).all()


def list_active_manual_treatments(
    db: Any,
    *,
    eswt_code: str = "eswt",
) -> list:
    """*활성* 도수치료 항목 — ``role="therapist" AND code != eswt_code AND active=True``.

    COMPAT: ``api.py:_get_manual_treatment_rows`` 와 byte-equivalent. sort_order 정렬.
    v1.3.37+: requires_record(기록 필요) 항목은 도수치료에서 제외.
    """
    from app.models import models as _m

    return (
        db.query(_m.Treatment)
        .filter(
            _m.Treatment.role == "therapist",
            _m.Treatment.code != eswt_code,
            _m.Treatment.requires_record == False,  # noqa: E712 — 기록필요 제외
            _m.Treatment.active == True,  # noqa: E712 — SQLAlchemy 정합
        )
        .order_by(_m.Treatment.sort_order)
        .all()
    )


def get_treatment_by_code(db: Any, code: str) -> Any | None:
    """code 로 단일 치료항목 조회.

    COMPAT: ``api.py:_bump_patient_count`` (line 1938) 의 ``filter_by(code=...)`` 정합.
    """
    from app.models import models as _m

    return db.query(_m.Treatment).filter_by(code=code).first()


def get_treatment_by_id(db: Any, treatment_id: str) -> Any | None:
    """ID 로 단일 치료항목 조회.

    COMPAT: ``api.py:update_treatment`` 의 ``db.get(Treatment, tid)`` 와 동등.
    """
    from app.models import models as _m

    return db.get(_m.Treatment, treatment_id)


__all__ = [
    "list_all_treatments",
    "list_treatments_sorted",
    "list_active_manual_treatments",
    "get_treatment_by_code",
    "get_treatment_by_id",
]
