"""modules.appointments.service — 예약 응답 dict 빌더 service helper (19-9 신규).

본 모듈은 ``api.py`` 의 모든 예약 핸들러 응답 dict 의 *byte-equivalent* 빌더를
제공한다. 라우터 무수정 — 19-10+ 시점 채택 후보.

19-9 본 세션 범위:
  - create / update / approve / revert / cancel / delete 응답 dict.
  - split (no-split + real) 응답 dict.
  - assign 응답 dict.
  - list_appointments / last_appointments 응답 빌드 helper.
  - patient_manual_history_summary / patient_history 응답 dict.
  - 라우터 미채택 (라우터 본체 무수정).

# COMPAT: ``api.py:create_appointment`` (line 1661) / ``update_appointment``
#         (line 1744) / ``approve_appointment`` (line 1979) / ``revert_approve``
#         (line 2003) / ``cancel_appointment`` (line 2021) / ``delete_appointment``
#         (line 2038) / ``split_appointment_code`` (line 1877 / 1925) /
#         ``change_assignment`` (line 1791) / ``last_appointments`` (line 1495) /
#         ``patient_manual_history_summary`` (line 1516) / ``patient_history``
#         (line 1597) 의 응답 dict 와 byte-equivalent.

# SAFETY: 본 helper 는 *기존 응답 dict 그대로* — UI / SMS / 통계 / AI 흐름이
#         의존. 본 19-9 가 응답 키 / 타입 변경 ⊥. 환자 PII 응답 *기존 동작* 보존
#         (UI 가 평문 PII 필요 — 마스킹은 19-7 patients.rules 의 로그 / AI prompt
#         전용 helper 별도).

# RISK: 응답 dict 키 변경 ⊥ — UI / SMS / 통계 / AI 모두 의존. ``schemas.py`` 의
#       contract 상수와 19-9 contract 테스트가 회귀 검출.
"""
from __future__ import annotations

from typing import Any

from app.modules.appointments import rules as _rules


# ─── create / update / approve / revert / cancel / delete 응답 ────────────────


def build_create_response(*, appointment_id: str, status: str | None) -> dict:
    """``POST /appointments`` 응답 dict — 2키.

    COMPAT: ``api.py:create_appointment`` (line 1661) ``{"id": obj.id, "status":
    obj.status}`` 와 byte-equivalent.
    """
    return {"id": appointment_id, "status": status}


def build_update_response(*, version: int | None) -> dict:
    """``PUT /appointments/{aid}`` 응답 dict — 2키.

    COMPAT: ``api.py:update_appointment`` (line 1744) /
    ``change_assignment`` (line 1791) ``{"ok": True, "version": int(obj.version
    or 0)}`` 와 byte-equivalent.
    """
    return {"ok": True, "version": int(version or 0)}


def build_approve_response(*, status: str | None, version: int | None) -> dict:
    """``POST /appointments/{aid}/approve`` 응답 dict — 3키.

    COMPAT: ``api.py:approve_appointment`` (line 1979) ``{"ok": True, "status":
    obj.status, "version": int(obj.version or 0)}`` 와 byte-equivalent.
    """
    return {"ok": True, "status": status, "version": int(version or 0)}


def build_revert_response(*, version: int | None) -> dict:
    """``POST /appointments/{aid}/revert-approve`` 응답 dict — 2키.

    COMPAT: ``api.py:revert_approve`` (line 2003) ``{"ok": True, "version":
    int(obj.version or 0)}`` 와 byte-equivalent.
    """
    return {"ok": True, "version": int(version or 0)}


def build_cancel_response(*, version: int | None) -> dict:
    """``POST /appointments/{aid}/cancel`` 응답 dict — 2키.

    COMPAT: ``api.py:cancel_appointment`` (line 2021) ``{"ok": True, "version":
    int(obj.version or 0)}`` 와 byte-equivalent.
    """
    return {"ok": True, "version": int(version or 0)}


def build_delete_response() -> dict:
    """``DELETE /appointments/{aid}`` 응답 dict — 1키.

    COMPAT: ``api.py:delete_appointment`` (line 2038) ``{"ok": True}`` 와
    byte-equivalent.
    """
    return {"ok": True}


# ─── split-code 응답 (no-split + real) ───────────────────────────────────────


def build_split_no_split_response(
    *, appointment_id: str, version: int | None
) -> dict:
    """``POST /appointments/{aid}/split-code`` 의 *원본만 업데이트* 분기 응답 — 4키.

    COMPAT: ``api.py:split_appointment_code`` (line 1877) ``{"ok": True, "split":
    False, "id": obj.id, "version": int(obj.version or 0)}`` 와 byte-equivalent.
    """
    return {
        "ok": True,
        "split": False,
        "id": appointment_id,
        "version": int(version or 0),
    }


def build_split_real_response(
    *,
    original_id: str,
    new_id: str,
    version: int | None,
) -> dict:
    """``POST /appointments/{aid}/split-code`` 의 *실제 분리* 분기 응답 — 5키.

    COMPAT: ``api.py:split_appointment_code`` (line 1925~1931) ``{"ok": True,
    "split": True, "original_id": obj.id, "new_id": new_appt.id, "version":
    int(obj.version or 0)}`` 와 byte-equivalent.
    """
    return {
        "ok": True,
        "split": True,
        "original_id": original_id,
        "new_id": new_id,
        "version": int(version or 0),
    }


# ─── 마지막 예약 응답 (last_appointments) ─────────────────────────────────────


def build_last_appointments_response(
    rows: list[tuple[str, Any]],
) -> dict[str, str | None]:
    """환자별 마지막 예약 시각 dict — 키=patient_id, 값=ISO8601 (없으면 None).

    COMPAT: ``api.py:last_appointments`` (line 1495) ``{r[0]: r[1].isoformat()
    if r[1] else None for r in rows}`` 와 byte-equivalent.
    """
    return {pid: (last.isoformat() if last else None) for pid, last in rows}


# ─── 도수치료 이력 요약 (patient_manual_history_summary) ─────────────────────


def build_manual_history_summary(
    *,
    patient_id: str,
    manual_appointment_ids: list[str],
    has_new_patient_flag: bool,
) -> dict:
    """``GET /patients/{pid}/manual-history-summary`` 응답 dict — 5키.

    COMPAT: ``api.py:patient_manual_history_summary`` (line 1516~1522) 와
    byte-equivalent. 5키: ``patient_id / has_manual_history / manual_count /
    has_new_patient_flag / manual_appointment_ids``.

    NOTE: 19-7 ``patients.service.build_manual_history_summary`` 와 동일 결과 —
    환자 / 예약 도메인 경계가 같은 dict 를 공유. 19-9 시점은 *예약 도메인 관점*
    helper 로 별도 노출 (라우터 가독성 향상).
    """
    return {
        "patient_id": patient_id,
        "has_manual_history": len(manual_appointment_ids) > 0,
        "manual_count": len(manual_appointment_ids),
        "has_new_patient_flag": has_new_patient_flag,
        "manual_appointment_ids": manual_appointment_ids,
    }


# ─── 환자 치료이력 응답 (patient_history) ────────────────────────────────────


def build_patient_history_envelope(
    *,
    total_days: int,
    offset: int,
    limit: int,
    days: list[dict],
    legacy_items: list[dict],
) -> dict:
    """``GET /patients/{pid}/history`` 응답 envelope — 5키.

    COMPAT: ``api.py:patient_history`` (line 1597~1603) ``{"total": total_days,
    "offset": offset, "limit": limit, "days": days, "items": legacy_items}`` 와
    byte-equivalent.

    NOTE: ``items`` 는 하위 호환 (fetchLastManualTherapist 등 평면 리스트 의존).
    제거 ⊥ — 프론트가 의존.
    """
    return {
        "total": total_days,
        "offset": offset,
        "limit": limit,
        "days": days,
        "items": legacy_items,
    }


# ─── 취소 메모 빌더 (api.py:cancel_appointment line 2016 정합) ───────────────


def append_cancel_memo(existing_memo: str | None, new_memo: str | None) -> str:
    """기존 메모 + 취소 prefix + 사용자 입력 합산 — ``rules.append_cancel_memo`` 와 동일.

    COMPAT: ``api.py:cancel_appointment`` (line 2016) 인라인 패턴 정합.

    NOTE: 본 service helper 는 ``rules`` 를 *re-export* 형태로 노출 — 호출자
    가독성 향상. 정책 변경 시 ``rules.append_cancel_memo`` 한 곳만 수정.
    """
    return _rules.append_cancel_memo(existing_memo, new_memo)


__all__ = [
    "build_create_response",
    "build_update_response",
    "build_approve_response",
    "build_revert_response",
    "build_cancel_response",
    "build_delete_response",
    "build_split_no_split_response",
    "build_split_real_response",
    "build_last_appointments_response",
    "build_manual_history_summary",
    "build_patient_history_envelope",
    "append_cancel_memo",
]
