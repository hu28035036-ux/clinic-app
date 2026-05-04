"""AI commands Execute 응답 dict 빌더 + HTTP 상태 코드 매핑 (19-13 신규).

services/ai/action_leave.py 의 ``ExecuteResult`` →
``app/routers/ai.py:action_execute`` 의 분기 응답 + HTTP 상태 코드 매핑을
*byte-equivalent* helper 로 노출. 라우터 무수정.

# COMPAT: 본 모듈의 ``build_execute_response`` / ``http_status_for_outcome`` 는
#         ``app/routers/ai.py:action_execute`` 의 분기와 *byte-equivalent*.
#         라우터 채택 ⊥.

# SAFETY: 본 모듈은 *읽기 / 응답 dict 변환 / 상태 코드 매핑* 만 — DB 변경 ⊥,
#         실제 ``EmployeeLeave`` upsert ⊥. 실제 upsert 는 ``services/ai/
#         action_leave.py:_do_upsert`` 가 단일 원천.

# RISK: Execute 단계 = ``confirm=True`` + HMAC 토큰 검증 + TOCTOU 재조회 통과
#       시에만 DB write. 본 19-13 가 정책 변경 ⊥.

# RISK: Approval 가드 — ``not_confirmed`` / ``overwrite_not_acknowledged`` /
#       ``token_*`` 분기는 모두 400 (DB write ⊥). ``conflict_changed`` /
#       ``therapist_changed`` 는 409 (동시성). ``db_error`` 는 500. 본 19-13 가
#       정책 변경 ⊥.

# NOTE: AI 예약 / AI SMS 일괄 발송 흐름 Execute 응답 빌더는 *현재 미구현* —
#       후속 19-x. ``schemas.INTENT_NAMES_TODO`` 마커 참고.
"""
from __future__ import annotations

from typing import Any

from .schemas import ACTION_EXECUTE_OUTCOME_HTTP_STATUS


# ──────────────── Action Execute (services/ai/action_leave.py:ExecuteResult) ────────────────

def build_execute_response(
    *,
    ok: bool,
    outcome: str,
    leave_id: str | None,
    mode: str | None,
    message: str,
) -> dict[str, Any]:
    """``POST /api/ai/action/execute`` 응답 dict — ``app/routers/ai.py:
    action_execute`` 의 ``body`` byte-equivalent.

    응답 key 5개 (``ok`` / ``outcome`` / ``leave_id`` / ``mode`` / ``message``).
    """
    return {
        "ok": bool(ok),
        "outcome": outcome,
        "leave_id": leave_id,
        "mode": mode,
        "message": message,
    }


def serialize_execute_result(result: Any) -> dict[str, Any]:
    """``ExecuteResult`` dataclass → dict — byte-equivalent."""
    return build_execute_response(
        ok=result.ok,
        outcome=result.outcome,
        leave_id=result.leave_id,
        mode=result.mode,
        message=getattr(result, "message", ""),
    )


# ──────────────── HTTP 상태 코드 매핑 ────────────────

def http_status_for_execute(*, ok: bool, outcome: str) -> int:
    """``action/execute`` outcome → HTTP 상태 코드 매핑 — ``app/routers/ai.py:
    action_execute`` byte-equivalent.

    - ok=True → 200
    - outcome ∈ {conflict_changed, therapist_changed} → 409
    - outcome == db_error → 500
    - 그 외 → 400 (default)

    RISK: ``not_confirmed`` / ``overwrite_not_acknowledged`` / ``token_*`` 는
    400 (DB write ⊥, 사용자에게 재시도 요청).
    """
    if ok:
        return 200
    return ACTION_EXECUTE_OUTCOME_HTTP_STATUS.get(outcome, 400)
