"""AI/RAG 로깅 헬퍼 (세션 09).

원칙 (절대 위반 X):
  - prompt 원문 / response 원문은 저장하지 않는다 — sha256 해시만.
  - API Key 값은 어떤 컬럼에도 저장하지 않는다.
  - 환자 전화번호 / 생년월일 / 차트번호 / 메모 / 예약 메모 / SMS 본문 전문은 저장하지 않는다.
  - PII 마스킹을 거친 후의 텍스트만 해시 계산에 사용한다.
  - 로깅 자체가 본 흐름을 깨지 않도록 모든 함수는 예외를 흡수한다.
  - db.commit() 은 호출지가 처리 (audit() 패턴 동일).
  - db 가 None 이면 silent skip (테스트/스텁 안전망).

사용 위치:
  - app/routers/ai.py 의 모든 엔드포인트 핸들러
  - app/services/ai/sms_draft.py / manual_qa.py 의 차단 지점
"""
from __future__ import annotations
import hashlib
from typing import Optional

from . import pii as pii_mod


def hash_text(s: Optional[str]) -> str:
    """sha256 hex. 빈/None 은 빈 문자열 반환."""
    if not s:
        return ""
    try:
        return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()
    except Exception:
        return ""


def _safe_hash(text: Optional[str]) -> str:
    """PII 마스킹 후 sha256. 마스킹 실패 시에도 절대 원문 해시 안 함."""
    if not text:
        return ""
    try:
        masked = pii_mod.scan(text).cleaned
        return hash_text(masked)
    except Exception:
        # 마스킹조차 실패하면 해시 자체를 포기 (원문 해시 금지)
        return ""


def _truncate(s: Optional[str], n: int = 500) -> str:
    if not s:
        return ""
    return s[:n]


def _node_id_safe() -> str:
    try:
        from ...config import load_config
        cfg = load_config() or {}
        return cfg.get("node_id") or ""
    except Exception:
        return ""


def log_ai_usage(
    db,
    *,
    feature: str,
    provider: str = "",
    model: str = "",
    outcome: str = "success",
    prompt_text: str = "",
    response_text: str = "",
    prompt_chars: int = 0,
    completion_chars: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    error_detail: str = "",
    pii_filter_hits: int = 0,
    hallucination_guard_hits: int = 0,
    actor: str = "system",
) -> None:
    """AiUsageLog 1행 추가. db.commit() 은 호출지가 처리.

    prompt_text / response_text 는 헬퍼 안에서 PII 마스킹 후 sha256 만 계산하고
    원문은 즉시 버린다. 본문 컬럼은 모델에 없으므로 들어갈 수도 없음.
    """
    if db is None:
        return
    try:
        # late import — 순환 회피 + 테스트 격리에 안전
        from ...models import models as _m

        if prompt_chars == 0 and prompt_text:
            prompt_chars = len(prompt_text)
        if completion_chars == 0 and response_text:
            completion_chars = len(response_text)

        row = _m.AiUsageLog(
            provider=(provider or "")[:20],
            model=(model or "")[:100],
            feature=(feature or "")[:50],
            prompt_chars=int(prompt_chars or 0),
            completion_chars=int(completion_chars or 0),
            prompt_tokens=int(prompt_tokens or 0),
            completion_tokens=int(completion_tokens or 0),
            latency_ms=int(latency_ms or 0),
            status=(outcome or "")[:20],          # legacy mirror
            error_kind=(_truncate(error_detail, 50)),  # legacy mirror (짧게)
            actor=(actor or "")[:50],
            outcome=(outcome or "")[:50],
            error_detail=_truncate(error_detail, 500),
            prompt_hash=_safe_hash(prompt_text),
            response_hash=_safe_hash(response_text),
            pii_filter_hits=int(pii_filter_hits or 0),
            hallucination_guard_hits=int(hallucination_guard_hits or 0),
            response_used=0,
            sms_sent=0,    # AI 가 직접 발송하지 않으므로 항상 0
        )
        db.add(row)
    except Exception:
        # 로깅 실패가 본 흐름을 깨지 않도록 흡수
        pass


def log_ai_blocked(
    db,
    *,
    feature: str,
    reason: str,
    provider: str = "",
    model: str = "",
    prompt_text: str = "",
    pii_filter_hits: int = 0,
    hallucination_guard_hits: int = 0,
    actor: str = "system",
) -> None:
    log_ai_usage(
        db,
        feature=feature,
        provider=provider,
        model=model,
        outcome="blocked",
        prompt_text=prompt_text,
        response_text="",
        error_detail=reason,
        pii_filter_hits=pii_filter_hits,
        hallucination_guard_hits=hallucination_guard_hits,
        actor=actor,
    )


def log_ai_error(
    db,
    *,
    feature: str,
    error_kind: str,
    provider: str = "",
    model: str = "",
    prompt_text: str = "",
    actor: str = "system",
) -> None:
    log_ai_usage(
        db,
        feature=feature,
        provider=provider,
        model=model,
        outcome="error",
        prompt_text=prompt_text,
        error_detail=error_kind,
        actor=actor,
    )


def log_ai_warning(
    db,
    *,
    feature: str,
    reason: str,
    provider: str = "",
    model: str = "",
    prompt_text: str = "",
    response_text: str = "",
    pii_filter_hits: int = 0,
    hallucination_guard_hits: int = 0,
    actor: str = "system",
) -> None:
    log_ai_usage(
        db,
        feature=feature,
        provider=provider,
        model=model,
        outcome="warning",
        prompt_text=prompt_text,
        response_text=response_text,
        error_detail=reason,
        pii_filter_hits=pii_filter_hits,
        hallucination_guard_hits=hallucination_guard_hits,
        actor=actor,
    )


def log_ai_setting_change(
    db,
    *,
    action: str,
    detail: str = "",
    entity_id: str = "",
    actor: str = "system",
) -> None:
    """AuditLog 에 AI 설정 변경 기록.

    detail 에는 절대 API Key 원문 / 환자 PII 가 들어가지 않도록 호출지가 책임진다.
    이 헬퍼는 한 번 더 500자 컷.
    """
    if db is None:
        return
    try:
        from ...models import models as _m
        row = _m.AuditLog(
            node_id=_node_id_safe(),
            actor=(actor or "system")[:50],
            action=(action or "")[:50],
            entity_id=(entity_id or "")[:32],
            detail=_truncate(detail, 500),
        )
        db.add(row)
    except Exception:
        pass
