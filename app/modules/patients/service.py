"""modules.patients.service — 환자 직렬화 service helper (19-7 신규).

본 모듈은 ``api.py:_patient_to_dict`` / ``_patient_counts_dict`` /
``_serialize_patients_bulk`` 의 *동등 helper* 를 제공한다. 라우터 무수정 — 19-9
시점 채택 후보.

19-7 본 세션 범위:
  - 환자 응답 dict 빌더 (8키 + counts + counts_show) — byte-equivalent.
  - light 응답 (counts 제외 7키) 빌더.
  - 검색 결과 dict 빌더.
  - 라우터 미채택 (라우터 본체 무수정).

# COMPAT: ``api.py:_patient_to_dict`` (line 1235) / ``_patient_counts_dict`` (line 1213) /
#         ``_serialize_patients_bulk`` (line 1357) / ``list_patients(light=1)`` (line 1290)
#         과 byte-equivalent.

# SAFETY: 본 helper 는 *기존 PII 평문 응답 그대로* — 환자 모달 / 검색 / 편집 흐름이
#         평문 PII 필요. 본 19-7 이 마스킹 정책 변경 ⊥. 마스킹은 ``rules.py`` 의
#         ``patient_summary_for_log`` 가 *로그 / AI prompt* 전용으로 별도 제공.

# NOTE: ``counts_show`` 는 ``show_in_patient=True AND active=True`` 인 항목만 — 환자
#       관리 표 축약용 (api.py:1238 정합).

# RISK: 응답 dict 키 변경 ⊥ — UI / SMS 발송 / 검색 모두 의존.
"""
from __future__ import annotations

from typing import Any


# ─── PatientTreatmentCount → counts dict (api.py:_patient_counts_dict 동등) ──


def build_patient_counts_dict(
    *,
    treatments_sorted: list,
    counts_rows: list,
) -> dict:
    """환자별 치료항목 처방/완료 카운트 dict.

    COMPAT: ``api.py:_patient_counts_dict`` (line 1213~1232) 와 byte-equivalent.
    caller 가 ``Treatment`` (sort_order 정렬) + ``PatientTreatmentCount`` row 주입.

    반환: ``{treatment_id: {treatment_id, code, name, short, role, show, active,
    rx_count, done_count}}`` (9키 per item).
    """
    by_id = {x.treatment_id: x for x in counts_rows}
    counts = {}
    for t in treatments_sorted:
        c = by_id.get(t.id)
        counts[t.id] = {
            "treatment_id": t.id,
            "code": t.code,
            "name": t.name,
            "short": t.short,
            "role": t.role,
            "show": t.show_in_patient,
            "active": t.active,
            "rx_count": c.rx_count if c else 0,
            "done_count": c.done_count if c else 0,
        }
    return counts


# ─── 환자 단건 응답 dict (api.py:_patient_to_dict 동등) ───────────────────


def build_patient_dict(
    patient: Any,
    *,
    counts: dict,
) -> dict:
    """``Patient`` ORM + counts dict → 9키 응답 dict.

    COMPAT: ``api.py:_patient_to_dict`` (line 1235~1247) 와 byte-equivalent.
    9키: ``id / name / birth_date / phone / chart_no / gender / memo / counts /
    counts_show``.
    ``counts_show`` = ``show=True AND active=True`` 인 counts.values() 를 ``code`` 순.
    """
    show_items = [c for c in counts.values() if c["show"] and c["active"]]
    show_items.sort(key=lambda x: x["code"])
    return {
        "id": patient.id,
        "name": patient.name,
        "birth_date": patient.birth_date,
        "phone": patient.phone,
        "chart_no": patient.chart_no,
        "gender": getattr(patient, "gender", "") or "",
        "memo": patient.memo or "",
        "counts": counts,
        "counts_show": show_items,
    }


# ─── 환자 light 응답 dict (counts 제외) ────────────────────────────────────


def build_patient_light_dict(patient: Any) -> dict:
    """``Patient`` ORM → 7키 light 응답 (counts 제외).

    COMPAT: ``api.py:list_patients`` (line 1291~1296) ``light=1`` 응답 정합.
    7키: ``id / name / chart_no / phone / birth_date / gender / memo``.

    NOTE: 검색 결과 (``search_patients`` 의 items) 도 동일 7키.
    """
    return {
        "id": patient.id,
        "name": patient.name,
        "chart_no": patient.chart_no,
        "phone": patient.phone,
        "birth_date": patient.birth_date,
        "gender": getattr(patient, "gender", "") or "",
        "memo": patient.memo or "",
    }


# ─── 검색 응답 envelope (api.py:search_patients 동등) ─────────────────────


def build_patient_search_response(
    *,
    items: list[dict],
    total: int,
    limit: int,
    offset: int,
    q: str,
) -> dict:
    """검색 응답 envelope — 6키.

    COMPAT: ``api.py:search_patients`` (line 1341~1345) 와 byte-equivalent.
    6키: ``items / total / limit / offset / q / has_more``.
    """
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "q": q,
        "has_more": (offset + len(items)) < total,
    }


# ─── 신환 체크 응답 (api.py:patient_manual_history_summary 동등) ──────────


def build_manual_history_summary(
    *,
    patient_id: str,
    manual_appointment_ids: list[str],
    has_new_patient_flag: bool,
) -> dict:
    """신환 체크 + 도수치료 이력 응답 dict — 4키.

    COMPAT: ``api.py:patient_manual_history_summary`` (line 1516~1522) 와 byte-equivalent.
    4키: ``patient_id / has_manual_history / manual_count / has_new_patient_flag /
    manual_appointment_ids``.
    """
    return {
        "patient_id": patient_id,
        "has_manual_history": len(manual_appointment_ids) > 0,
        "manual_count": len(manual_appointment_ids),
        "has_new_patient_flag": has_new_patient_flag,
        "manual_appointment_ids": manual_appointment_ids,
    }


__all__ = [
    "build_patient_counts_dict",
    "build_patient_dict",
    "build_patient_light_dict",
    "build_patient_search_response",
    "build_manual_history_summary",
]
