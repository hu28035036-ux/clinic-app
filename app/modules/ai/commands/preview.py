"""AI commands Preview 응답 dict 빌더 (19-13 신규).

services/ai/action_leave.py 의 ``ParseResult`` / ``PreviewResult`` →
``app/routers/ai.py:_serialize_parse_result`` / ``_serialize_preview_result`` 를
*byte-equivalent* helper 로 노출. 라우터 무수정.

# COMPAT: 본 모듈의 모든 ``build_*`` / ``serialize_*`` 함수는 ``app/routers/ai.py``
#         의 ``_serialize_parse_result`` / ``_serialize_preview_result`` 와
#         *byte-equivalent*. 응답 key / 타입 보존.

# SAFETY: 본 모듈은 *읽기 / dataclass → dict 변환* 만 — DB 변경 ⊥, LLM 호출 ⊥,
#         외부 API 호출 ⊥, SMS 발송 ⊥.

# RISK: Preview 단계 = read-only — ``preview_token`` (HMAC, TTL 120s) 만 발급,
#       실제 ``EmployeeLeave`` upsert ⊥. 본 19-13 가 정책 변경 ⊥.

# NOTE: AI 예약 / AI SMS 일괄 발송 흐름 Preview 응답 빌더는 *현재 미구현* —
#       후속 19-x. ``schemas.INTENT_NAMES_TODO`` 마커 참고.
"""
from __future__ import annotations

from typing import Any


# ──────────────── Action Parse Preview (services/ai/action_leave.py:ParseResult) ────────────────

def build_parse_response(
    *,
    ok: bool,
    outcome: str,
    parsed: dict | None,
    warnings: list[str],
    safe_to_continue: bool,
    message: str = "",
) -> dict[str, Any]:
    """``POST /api/ai/action/parse`` 응답 dict — ``app/routers/ai.py:
    _serialize_parse_result`` byte-equivalent.

    NOTE: parse 응답은 *디버깅 / 투명성용 read-only*. preview / execute 가 다시
    검증한다 (services/ai/action_leave.py 정책 단일 원천).
    """
    return {
        "ok": bool(ok),
        "outcome": outcome,
        "parsed": parsed,
        "warnings": list(warnings),
        "safe_to_continue": bool(safe_to_continue),
        "message": message,
    }


def serialize_parse_result(result: Any) -> dict[str, Any]:
    """``ParseResult`` dataclass → dict — ``app/routers/ai.py:_serialize_parse_result``
    byte-equivalent.

    NOTE: ``result`` 는 ``services.ai.action_leave.ParseResult`` 인스턴스 (또는
    동일 속성을 가진 객체).
    """
    return build_parse_response(
        ok=result.ok,
        outcome=result.outcome,
        parsed=result.parsed,
        warnings=result.warnings,
        safe_to_continue=result.safe_to_continue,
        message=getattr(result, "message", ""),
    )


# ──────────────── Action Preview (services/ai/action_leave.py:PreviewResult) ────────────────

def build_preview_response(
    *,
    ok: bool,
    outcome: str,
    candidate: dict | None,
    mode: str | None,
    existing: dict | None,
    appointments_count: int,
    warnings: list[str],
    safe_to_execute: bool,
    preview_token: str | None,
    preview_token_exp: int | None,
    message: str = "",
) -> dict[str, Any]:
    """``POST /api/ai/action/preview`` 응답 dict — ``app/routers/ai.py:
    _serialize_preview_result`` byte-equivalent.

    RISK: ``preview_token`` 은 HMAC 서명된 짧은 TTL 토큰 (120s). 본 응답에 포함
    되지만 audit log / 응답 외 위치에는 원문 노출 ⊥ (``commands.safety.
    SECRET_KEYS_FORBIDDEN_IN_LOG``).

    RISK: ``mode`` 는 ``"create"`` / ``"overwrite"`` / ``"noop"`` / ``None``.
    overwrite 모드 → execute 시 ``overwrite_acknowledged=True`` 필요.
    """
    return {
        "ok": bool(ok),
        "outcome": outcome,
        "candidate": candidate,
        "mode": mode,
        "existing": existing,
        "appointments_count": int(appointments_count),
        "warnings": list(warnings),
        "safe_to_execute": bool(safe_to_execute),
        "preview_token": preview_token,
        "preview_token_exp": preview_token_exp,
        "message": message,
    }


def serialize_preview_result(result: Any) -> dict[str, Any]:
    """``PreviewResult`` dataclass → dict — ``app/routers/ai.py:
    _serialize_preview_result`` byte-equivalent.
    """
    return build_preview_response(
        ok=result.ok,
        outcome=result.outcome,
        candidate=result.candidate,
        mode=result.mode,
        existing=result.existing,
        appointments_count=result.appointments_count,
        warnings=result.warnings,
        safe_to_execute=result.safe_to_execute,
        preview_token=result.preview_token,
        preview_token_exp=result.preview_token_exp,
        message=getattr(result, "message", ""),
    )


# ──────────────── SMS Draft Preview ────────────────

def build_sms_draft_response_public(
    *,
    draft: str,
    warnings: list[str],
    missing_fields: list[str],
    context_used: dict[str, Any],
    needs_user_confirm: bool,
    skipped: bool,
    skip_reason: str,
    blocked: bool = False,
    blocked_reason: str = "",
    guard_hits: int = 0,
) -> dict[str, Any]:
    """``POST /api/ai/sms/draft`` 응답 dict (라우터 응답 키 — prompt_text /
    response_text 제거 후) — ``app/routers/ai.py:sms_draft`` 의 ``out = {k: v ...
    if k not in ("prompt_text", "response_text")}`` byte-equivalent.

    SAFETY: ``prompt_text`` / ``response_text`` (LLM 입력/출력 원문) 은 본 응답에
    *부재 보장* — schemas.py:SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS 가 정책 단일 원천.

    RISK: ``needs_user_confirm=True`` → 사용자 승인 후 별도 SMS 발송 필요. 본
    응답 자체로 외부 SMS 발송 ⊥. blocked=True → 발송 ⊥.
    """
    return {
        "draft": draft,
        "warnings": list(warnings),
        "missing_fields": list(missing_fields),
        "context_used": dict(context_used),
        "needs_user_confirm": bool(needs_user_confirm),
        "skipped": bool(skipped),
        "skip_reason": skip_reason,
        "blocked": bool(blocked),
        "blocked_reason": blocked_reason,
        "guard_hits": int(guard_hits),
    }
