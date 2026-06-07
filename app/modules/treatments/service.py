"""modules.treatments.service — 치료항목 직렬화 / 메타 빌드 service helper (19-6 신규).

본 모듈은 ``api.py:_serialize_treatment`` / ``_normalize_incentive`` /
``_build_treatment_meta`` 의 *동등 service helper* 를 제공한다. 라우터 무수정 — 19-9
/ 19-11 시점 채택 후보.

19-6 본 세션 범위:
  - 직렬화 helper — 응답 dict byte-equivalent.
  - 인센티브 정규화 — 입력 검증 시 ``raise`` ⊥ (호출자가 ValueError → HTTPException 변환).
  - treatment_meta dict 빌드 — 13키 응답 정합.

# COMPAT: ``api.py:_serialize_treatment`` (line 767~783) 12키 +
#         ``_build_treatment_meta`` (line 837~855) 13키 byte-equivalent.

# SAFETY: 본 helper 는 *직렬화 / 검증* 만 — DB 변경 ⊥. 환자 PII 미참조.

# RISK: ``count_increment`` 값을 그대로 노출 — 시간 가중치 합산 도입 시 통계 왜곡.
#       사용자 명시 "시간 가중치 방식으로 되돌리는 것 금지" — 현재 ``manual60``=1 정책
#       (CLAUDE.md) 을 시드/관리자 UI 가 책임짐. 본 helper 는 정책 결정 ⊥.
"""
from __future__ import annotations

from typing import Any

from app.modules.treatments import rules as _rules


# ─── 인센티브 정규화 검증 결과 ────────────────────────────────────────────────


class IncentiveValidationError(ValueError):
    """인센티브 정규화 실패 — 호출자가 ``raise HTTPException(400, ...)`` 으로 변환.

    NOTE: 본 모듈은 fastapi 의존 ⊥ — D-4 정합. 호출자가 변환 책임.
    """

    pass


def normalize_incentive(pct: Any, amount: Any) -> tuple[float | None, int | None]:
    """인센티브 XOR 정규화 + 검증.

    COMPAT: ``api.py:_normalize_incentive`` (line 786~813) 와 byte-equivalent.
    - 둘 다 값이 있으면 ``IncentiveValidationError``.
    - pct 는 0~100, amount 는 0 이상.
    - 빈값 / None / 0 이하는 None (DB ``NULL`` = "입력 안 함").

    NOTE: ``api.py`` 본체는 ``raise HTTPException(400, ...)`` — 본 helper 는 ValueError
    하위 클래스를 raise (D-4 정합 — fastapi 의존 ⊥). 호출자가 ``except IncentiveValidationError``
    으로 받아 HTTPException 으로 변환.
    """

    def _to_float(v: Any) -> float | None:
        try:
            if v is None or v == "":
                return None
            f = float(v)
            return f if f > 0 else None
        except Exception:
            return None

    def _to_int(v: Any) -> int | None:
        try:
            if v is None or v == "":
                return None
            i = int(v)
            return i if i > 0 else None
        except Exception:
            return None

    p = _to_float(pct)
    a = _to_int(amount)
    if p is not None and a is not None:
        raise IncentiveValidationError(
            "인센티브는 '퍼센티지' 또는 '고정 금액' 중 하나만 입력하세요."
        )
    if p is not None and (p < 0 or p > 100):
        raise IncentiveValidationError("인센티브 퍼센티지는 0~100 사이여야 합니다.")
    return p, a


# ─── 직렬화 helper ────────────────────────────────────────────────────────────


def serialize_treatment(t: Any) -> dict:
    """``Treatment`` ORM → 12키 응답 dict.

    COMPAT: ``api.py:_serialize_treatment`` (line 767~783) 와 byte-equivalent.
    12키: ``id / code / name / short / default_minutes / role / count_increment /
    show_in_patient / active / sort_order / price / incentive_pct / incentive_amount``.
    """
    return {
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "short": t.short,
        "category_id": getattr(t, "category_id", None),
        "category_name": getattr(getattr(t, "category", None), "name", None),
        "default_minutes": t.default_minutes,
        "role": t.role,
        "count_increment": t.count_increment,
        "show_in_patient": t.show_in_patient,
        "active": t.active,
        "sort_order": t.sort_order,
        "price": int(getattr(t, "price", 0) or 0),
        "incentive_pct": getattr(t, "incentive_pct", None),
        "incentive_amount": getattr(t, "incentive_amount", None),
    }


def build_treatment_meta(
    treatments: list,
    *,
    eswt_code: str = _rules.DEFAULT_ESWT_CODE,
) -> dict:
    """``treatments`` (sort_order 정렬) → 13키 메타 dict.

    COMPAT: ``api.py:_build_treatment_meta`` (line 816~855) 와 byte-equivalent.
    caller 가 sort_order 정렬된 list 주입 (``repository.list_treatments_sorted`` 결과).

    NOTE: 모든 항목별 ``count_increment`` 그대로 노출 — *시간 가중치 합산 ⊥*.
    UI / 통계는 *항목별 카운트* 만 사용.
    """
    treatment_codes_active = [t.code for t in treatments if t.active]
    treatment_names = {t.code: t.name for t in treatments}
    treatment_short = {t.code: t.short for t in treatments}
    treatment_category = {t.code: getattr(t, "category_id", None) for t in treatments}
    treatment_category_name = {
        t.code: getattr(getattr(t, "category", None), "name", None) or ""
        for t in treatments
    }
    doctor_treatments = [
        t.code for t in treatments if t.active and _rules.is_doctor_role(t)
    ]
    therapist_treatments = [
        t.code for t in treatments if t.active and _rules.is_therapist_role(t)
    ]
    manual_treatments = [
        t.code for t in treatments
        if t.active and _rules.is_manual_treatment(t, eswt_code=eswt_code)
    ]
    treatment_minutes = {t.code: t.default_minutes for t in treatments}
    count_increment = {t.code: t.count_increment for t in treatments}
    treatment_role = {t.code: t.role for t in treatments}
    treatment_show = {t.code: t.show_in_patient for t in treatments}
    treatment_price = {
        t.code: int(getattr(t, "price", 0) or 0) for t in treatments
    }
    treatment_incentive_pct = {
        t.code: getattr(t, "incentive_pct", None) for t in treatments
    }
    treatment_incentive_amount = {
        t.code: getattr(t, "incentive_amount", None) for t in treatments
    }

    return {
        "treatment_codes": treatment_codes_active,
        "treatment_names": treatment_names,
        "treatment_category": treatment_category,
        "treatment_category_name": treatment_category_name,
        "treatment_short": treatment_short,
        "treatment_minutes": treatment_minutes,
        "treatment_role": treatment_role,
        "treatment_show": treatment_show,
        "doctor_treatments": doctor_treatments,
        "therapist_treatments": therapist_treatments,
        "manual_treatments": manual_treatments,
        "count_increment": count_increment,
        "eswt_code": eswt_code,
        "treatment_price": treatment_price,
        "treatment_incentive_pct": treatment_incentive_pct,
        "treatment_incentive_amount": treatment_incentive_amount,
        "employee_categories": [],
        "all_treatments": [serialize_treatment(t) for t in treatments],
    }


__all__ = [
    "IncentiveValidationError",
    "normalize_incentive",
    "serialize_treatment",
    "build_treatment_meta",
]
