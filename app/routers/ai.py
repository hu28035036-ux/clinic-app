"""AI / RAG 라우터 (v1.3 단계 1+2 통합본 + 세션 09 보강).

분리 원칙:
  - 기존 app/routers/api.py 에 AI 코드를 섞지 않는다.
  - AI 는 DB 변경/SMS 발송을 직접 하지 않는다 (라우터에서 그런 동작 금지).

세션 09 보강:
  - 모든 호출 endpoint 에 AiUsageLog insert (마스킹 후 해시만, 본문 미저장).
  - PUT /api/ai/settings 변경에 AuditLog insert (값 자체 저장 금지, 변경 사실만).
  - PII / 할루시네이션 / disabled / no key 차단 시 AiUsageLog outcome=blocked +
    AuditLog 로 사실 기록.

이 단계에 포함:
  단계 1 (Provider 골격, admin 전용):
    - GET  /api/ai/health           : SDK 가능 여부, 설정 상태 (로그 안 남김 — 폴링 다수)
    - GET  /api/ai/providers        : 선택 가능한 provider 목록
    - GET  /api/ai/settings         : 현재 설정 (api_key 마스킹, 로그 안 남김)
    - PUT  /api/ai/settings         : 설정 저장 (AuditLog 만 기록)
  단계 2 (SMS 검증, 일반 — 기존 POST /api/sms/send 와 권한 일관):
    - POST /api/ai/sms/validate     : 예약문자 발송 전 BLOCKER/WARNING 검증
                                      (LLM 미사용, AiUsageLog 기록)
"""
from __future__ import annotations
import importlib
import time
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import models
from ..services import auth
from ..services.ai import action_leave as ai_action_leave
from ..services.ai import ai_logging as ai_log
from ..services.ai import manual_qa as ai_manual_qa
from ..services.ai import provider as ai_provider
from ..services.ai import sms_draft as ai_sms_draft
from ..services.ai import validators
from ..services.rag.search import _load_index as _load_kb_index


router = APIRouter(prefix="/api/ai")


# ──────────────── 공통 (단계 1) ────────────────

def require_admin(x_admin_token: str = Header(default="")):
    if not auth.is_valid(x_admin_token):
        raise HTTPException(401, "관리자 인증이 필요합니다.")
    return True


def _get_or_create_setting(db: Session) -> models.AiSetting:
    obj = db.query(models.AiSetting).filter(models.AiSetting.id == 1).first()
    if obj is None:
        obj = models.AiSetting(id=1)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj


def _mask_api_key(key: str) -> str:
    """API key 평문 노출 금지 — 앞 4자 + ****.

    SmsSetting.munjanara_key 마스킹 패턴과 동일.
    """
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return key[:4] + "****"


def _serialize_setting(obj: models.AiSetting) -> dict:
    return {
        "enabled": bool(obj.enabled),
        "provider": obj.provider or "openai",
        "model": obj.model or "",
        "api_key_masked": _mask_api_key(obj.api_key or ""),
        "api_key_set": bool(obj.api_key),
        "base_url": obj.base_url or "",
        "max_tokens": int(obj.max_tokens or 512),
        "temperature": float(obj.temperature or 0.3),
        "pii_guard_enabled": bool(obj.pii_guard_enabled),
    }


# provider → (ok, error_message). health 엔드포인트가 폴링되므로 결과 캐시.
# 서버 재시작 시 초기화 → pip install 후 정상 반영.
_sdk_check_cache: dict[str, tuple[bool, str | None]] = {}


def _check_sdk(name: str) -> tuple[bool, str | None]:
    """SDK import 점검 → (ok, error_message). 실패 사유를 짧게 보존해 admin 화면 진단용."""
    cached = _sdk_check_cache.get(name)
    if cached is not None:
        return cached
    if name not in ("openai", "anthropic"):
        # local 등 — v2 보류, 실패 사유 없음
        result: tuple[bool, str | None] = (False, None)
        _sdk_check_cache[name] = result
        return result
    try:
        importlib.import_module(name)
        result = (True, None)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        if len(msg) > 200:
            msg = msg[:200] + "..."
        result = (False, msg)
    _sdk_check_cache[name] = result
    return result


def _sdk_available(name: str) -> bool:
    """기존 호출자용 — bool 만 필요할 때."""
    return _check_sdk(name)[0]


def _commit_silent(db: Session) -> None:
    """로그 insert 후 commit. 실패해도 본 흐름을 막지 않음."""
    try:
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


# ──────────────── 단계 1 엔드포인트 (admin 전용) ────────────────

@router.get("/health")
def ai_health(db: Session = Depends(get_db),
              _: bool = Depends(require_admin)):
    """AI 기능 상태 점검 — 관리자 전용. 로그 안 남김 (폴링 다수)."""
    s = _get_or_create_setting(db)
    sdk_results = {p: _check_sdk(p) for p in ai_provider.list_known_providers()}
    sdk_status = {p: ok for p, (ok, _err) in sdk_results.items()}
    # admin 전용: SDK import 실패 사유 — public health 엔드포인트에는 노출 X
    sdk_errors = {p: err for p, (ok, err) in sdk_results.items() if (not ok) and err}
    ready = bool(
        s.enabled and s.api_key and s.model and sdk_status.get(s.provider or "")
    )
    try:
        knowledge_doc_count = len(_load_kb_index().get("documents", []))
    except Exception:
        knowledge_doc_count = 0
    return {
        "enabled": bool(s.enabled),
        "provider": s.provider or "openai",
        "model": s.model or "",
        "api_key_set": bool(s.api_key),
        "sdk_installed": sdk_status,
        "sdk_errors": sdk_errors,
        "knowledge_doc_count": knowledge_doc_count,
        "ready": ready,
        "version": "v1.3-stage1",
    }


@router.get("/health/public")
def ai_health_public(db: Session = Depends(get_db)):
    """AI 기능 상태 — 일반 사용자 노출용 4 필드. 인증 불필요.

    의도적으로 admin 전용 정보(model 명, sdk 상세, knowledge_doc_count, version)는 제외.
    api_key_set 은 boolean 이므로 키 자체 누출 없음 — UI 흐름 제어용.
    """
    s = _get_or_create_setting(db)
    sdk_status = {p: _sdk_available(p) for p in ai_provider.list_known_providers()}
    ready = bool(
        s.enabled and s.api_key and s.model and sdk_status.get(s.provider or "")
    )
    return {
        "enabled": bool(s.enabled),
        "ready": ready,
        "provider": s.provider or "openai",
        "api_key_set": bool(s.api_key),
    }


@router.get("/providers")
def ai_providers(_: bool = Depends(require_admin)):
    """선택 가능한 provider 목록 + 설치 상태."""
    items = []
    for p in ai_provider.list_known_providers():
        items.append({
            "name": p,
            "label": {"openai": "OpenAI", "anthropic": "Anthropic (Claude)",
                      "local": "Local (v2 예정)"}.get(p, p),
            "sdk_installed": _sdk_available(p),
            "available": p in ("openai", "anthropic"),
        })
    return {"providers": items}


@router.get("/settings")
def ai_settings_get(db: Session = Depends(get_db),
                    _: bool = Depends(require_admin)):
    s = _get_or_create_setting(db)
    return _serialize_setting(s)


@router.put("/settings")
def ai_settings_put(payload: dict = Body(...),
                    db: Session = Depends(get_db),
                    _: bool = Depends(require_admin)):
    """AI 설정 저장.

    api_key 는 빈 문자열로 들어오면 기존 값 유지 (SmsSetting 패턴과 동일).
    명시적으로 "" 로 지우려면 클라이언트가 "clear_api_key": true 를 보낸다.

    세션 09: 변경 사실(전/후 값 자체 X)만 AuditLog 에 기록.
    """
    s = _get_or_create_setting(db)
    # 변경 추적용 — 값 자체는 저장 금지, "변경됨" 사실만 기록
    changes: list = []
    prev_provider = s.provider or ""

    if "enabled" in payload:
        new_enabled = bool(payload.get("enabled"))
        if new_enabled != bool(s.enabled):
            changes.append(f"ai.enabled changed: {bool(s.enabled)} -> {new_enabled}")
        s.enabled = new_enabled

    if "provider" in payload:
        prov = (payload.get("provider") or "").strip().lower()
        if prov and prov not in ai_provider.list_known_providers():
            raise HTTPException(400, f"알 수 없는 provider: {prov!r}")
        if prov and prov != prev_provider:
            changes.append(f"ai.provider changed: {prev_provider} -> {prov}")
        if prov:
            s.provider = prov

    if "model" in payload:
        new_model = (payload.get("model") or "").strip()[:100]
        if new_model != (s.model or ""):
            # 모델명은 식별 정보가 아니므로 그대로 기록 가능
            changes.append(f"ai.model changed: {s.model or ''} -> {new_model}")
        s.model = new_model

    if payload.get("clear_api_key") is True:
        if s.api_key:
            changes.append("ai.api_key cleared")
        s.api_key = ""
    elif "api_key" in payload:
        new_key = payload.get("api_key")
        if isinstance(new_key, str) and new_key.strip():
            # 키 값 자체는 절대 detail 에 안 들어감 — "updated" 사실만
            changes.append("ai.api_key updated")
            s.api_key = new_key.strip()
        # 빈 문자열 / None 이면 기존 값 유지

    if "base_url" in payload:
        new_base = (payload.get("base_url") or "").strip()[:500]
        if new_base != (s.base_url or ""):
            changes.append("ai.base_url updated")
        s.base_url = new_base

    if "max_tokens" in payload:
        try:
            v = int(payload.get("max_tokens"))
        except (TypeError, ValueError):
            raise HTTPException(400, "max_tokens 는 정수여야 합니다.")
        if v < 1 or v > 8000:
            raise HTTPException(400, "max_tokens 범위: 1~8000")
        if v != int(s.max_tokens or 0):
            changes.append(f"ai.max_tokens changed: {s.max_tokens} -> {v}")
        s.max_tokens = v

    if "temperature" in payload:
        try:
            v = float(payload.get("temperature"))
        except (TypeError, ValueError):
            raise HTTPException(400, "temperature 는 숫자여야 합니다.")
        if v < 0 or v > 2:
            raise HTTPException(400, "temperature 범위: 0.0~2.0")
        if abs(v - float(s.temperature or 0.0)) > 1e-9:
            changes.append(f"ai.temperature changed: {s.temperature} -> {v}")
        s.temperature = v

    if "pii_guard_enabled" in payload:
        new_pii = bool(payload.get("pii_guard_enabled"))
        if new_pii != bool(s.pii_guard_enabled):
            changes.append(f"ai.pii_guard_enabled changed: {bool(s.pii_guard_enabled)} -> {new_pii}")
        s.pii_guard_enabled = new_pii

    # AuditLog — 변경된 항목들을 한 줄 detail 로 기록 (값 자체 X, key 원문 X)
    if changes:
        ai_log.log_ai_setting_change(
            db,
            action="ai.settings_update",
            detail=" | ".join(changes),
            entity_id="ai_settings",
            actor="admin",
        )

    db.commit()
    db.refresh(s)
    return _serialize_setting(s)


# ──────────────── 단계 2 엔드포인트 (SMS 검증) ────────────────
#
# 기존 POST /api/sms/send 와 권한 일관: admin gate 없음.
# LLM 미사용 — validators 모듈의 결정론적 로직만 호출.

class SmsValidateItem(BaseModel):
    appointment_id: Optional[str] = None
    body: str = ""
    phone: Optional[str] = None
    patient_id: Optional[str] = None


class SmsValidateRequest(BaseModel):
    items: List[SmsValidateItem] = Field(default_factory=list)
    dup_window_minutes: int = validators.DEFAULT_DUP_WINDOW_MIN


@router.post("/sms/validate")
def sms_validate(
    payload: SmsValidateRequest,
    db: Session = Depends(get_db),
) -> dict:
    """예약문자 발송 전 누락정보·오류 검증.

    blocker 가 1개라도 있으면 발송 불가, warning 은 사용자 확인 후 발송 가능.
    """
    t0 = time.monotonic()
    items = [it.model_dump() for it in payload.items]
    try:
        results = validators.validate_sms_batch(
            db, items, dup_window_minutes=payload.dup_window_minutes,
        )
    except Exception as e:
        ai_log.log_ai_error(
            db, feature="sms_validate", error_kind=type(e).__name__,
        )
        _commit_silent(db)
        raise

    latency_ms = int((time.monotonic() - t0) * 1000)
    ai_log.log_ai_usage(
        db,
        feature="sms_validate",
        provider="",
        model="",
        outcome="success",
        latency_ms=latency_ms,
        error_detail=f"items={len(items)}",
    )
    _commit_silent(db)
    return {"results": results}


# ──────────────── 단계 4 엔드포인트 (SMS 초안 생성, LLM 호출) ────────────────
#
# 정책 (절대 위반 X):
#   - 발송 / DB 쓰기 금지 — 초안만 반환, 사용자 확인 후 사람이 발송
#   - PII (전화/생년월일/차트번호/메모/직원개인정보) LLM 미전송
#   - 환자명은 토큰('환자A') 으로 LLM 에 전달, 응답에서 실명 복원
#   - 취소 예약은 LLM 호출 없이 안내 문구만 반환

class SmsDraftRequest(BaseModel):
    appointment_id: str
    tone: str = "friendly"        # friendly | formal
    extra_note: Optional[str] = ""


@router.post("/sms/draft")
def sms_draft(
    payload: SmsDraftRequest,
    db: Session = Depends(get_db),
) -> dict:
    """예약 정보 기반 SMS 본문 초안 생성.

    503: AI 비활성 / API key 미설정 / 모델 미지정 / provider 사용 불가
    400: tone 값 오류 / PII 가드 차단
    200: 초안 생성 성공 또는 정책상 skip (예: 취소 예약)
    """
    s = _get_or_create_setting(db)

    if not s.enabled:
        ai_log.log_ai_blocked(
            db, feature="sms_draft",
            reason="ai request blocked because ai disabled",
            provider=s.provider or "", model=s.model or "",
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked because ai disabled",
            entity_id=str(payload.appointment_id),
        )
        _commit_silent(db)
        raise HTTPException(
            503,
            "AI 기능이 꺼져 있습니다. 관리자 → AI 설정에서 활성화해 주세요.",
        )
    if not (s.api_key or "").strip():
        ai_log.log_ai_blocked(
            db, feature="sms_draft",
            reason="ai request blocked because api key missing",
            provider=s.provider or "", model=s.model or "",
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked because api key missing",
            entity_id=str(payload.appointment_id),
        )
        _commit_silent(db)
        raise HTTPException(
            503,
            "AI API key 가 설정되지 않았습니다. 관리자 → AI 설정에서 입력해 주세요.",
        )
    if not (s.model or "").strip():
        ai_log.log_ai_blocked(
            db, feature="sms_draft",
            reason="ai request blocked because model missing",
            provider=s.provider or "", model="",
        )
        _commit_silent(db)
        raise HTTPException(
            503,
            "AI 모델이 지정되지 않았습니다. 관리자 → AI 설정에서 모델명을 입력해 주세요.",
        )

    if payload.tone not in ("friendly", "formal"):
        raise HTTPException(400, "tone 값은 'friendly' 또는 'formal' 이어야 합니다.")

    try:
        prov = ai_provider.get_provider(
            s.provider or "openai",
            model=s.model,
            api_key=s.api_key,
            base_url=s.base_url or "",
            max_tokens=int(s.max_tokens or 512),
            temperature=float(s.temperature or 0.3),
        )
    except ai_provider.AiUnavailable as e:
        ai_log.log_ai_error(
            db, feature="sms_draft",
            error_kind=f"AiUnavailable:{e.kind}",
            provider=s.provider or "", model=s.model or "",
        )
        _commit_silent(db)
        raise HTTPException(503, f"AI provider 사용 불가: {e} (kind={e.kind})")

    t0 = time.monotonic()
    try:
        result = ai_sms_draft.make_draft(
            db,
            appointment_id=payload.appointment_id,
            tone=payload.tone,
            extra_note=payload.extra_note or "",
            provider_override=prov,
        )
    except ai_provider.AiUnavailable as e:
        ai_log.log_ai_error(
            db, feature="sms_draft",
            error_kind=f"AiUnavailable:{e.kind}",
            provider=s.provider or "", model=s.model or "",
        )
        _commit_silent(db)
        raise HTTPException(503, f"AI 호출 불가: {e} (kind={e.kind})")
    except ai_provider.AiPiiBlocked as e:
        ai_log.log_ai_blocked(
            db, feature="sms_draft",
            reason="ai request blocked by pii guard",
            provider=s.provider or "", model=s.model or "",
            pii_filter_hits=len(getattr(e, "fields", []) or []),
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked by pii guard",
            entity_id=str(payload.appointment_id),
        )
        _commit_silent(db)
        raise HTTPException(400, f"PII 가드: {e}")
    except ValueError as e:
        # PII 가드 (extra_note / safe_ctx) 또는 기타 검증 실패
        msg = str(e)
        if "PII" in msg:
            ai_log.log_ai_blocked(
                db, feature="sms_draft",
                reason="ai request blocked by pii guard",
                provider=s.provider or "", model=s.model or "",
                pii_filter_hits=1,
            )
            ai_log.log_ai_setting_change(
                db, action="ai.blocked",
                detail="ai request blocked by pii guard",
                entity_id=str(payload.appointment_id),
            )
        else:
            ai_log.log_ai_error(
                db, feature="sms_draft",
                error_kind="ValueError",
                provider=s.provider or "", model=s.model or "",
            )
        _commit_silent(db)
        raise HTTPException(400, msg)

    latency_ms = int((time.monotonic() - t0) * 1000)
    blocked = bool(result.get("blocked"))
    skipped = bool(result.get("skipped"))
    blocked_reason = result.get("blocked_reason") or ""

    if blocked:
        ai_log.log_ai_blocked(
            db, feature="sms_draft",
            reason=blocked_reason or "ai request blocked by hallucination guard",
            provider=s.provider or "", model=s.model or "",
            prompt_text=result.get("prompt_text", ""),
            hallucination_guard_hits=int(result.get("guard_hits", 0)),
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked by hallucination guard: " + blocked_reason,
            entity_id=str(payload.appointment_id),
        )
    elif skipped:
        ai_log.log_ai_warning(
            db, feature="sms_draft",
            reason=f"skipped:{result.get('skip_reason', '')}",
            provider=s.provider or "", model=s.model or "",
            latency_ms=latency_ms,
        )
    else:
        ai_log.log_ai_usage(
            db,
            feature="sms_draft",
            provider=s.provider or "",
            model=s.model or "",
            outcome="success",
            prompt_text=result.get("prompt_text", ""),
            response_text=result.get("response_text", ""),
            latency_ms=latency_ms,
            hallucination_guard_hits=int(result.get("guard_hits", 0)),
        )
    _commit_silent(db)

    # 응답에서 prompt_text/response_text 는 라우터 응답에 노출하지 않음 (내부 키)
    out = {k: v for k, v in result.items() if k not in ("prompt_text", "response_text")}
    return out


# ──────────────── 단계 5 엔드포인트 (업무 매뉴얼 Q&A) ────────────────
#
# 정책:
#   - 환자 DB 접근 금지 — knowledge/manuals/ 만 검색.
#   - 사용자 질문에 PII 가 섞여 들어와도 마스킹 후 검색·LLM 전달.
#   - 매뉴얼 검색 결과 없으면 LLM 호출 0회.
#   - 매뉴얼에 없는 내용을 추측해서 답하지 않음 (system 프롬프트로 강제).

class ManualSearchRequest(BaseModel):
    question: str = ""


class ManualAskRequest(BaseModel):
    question: str = ""


@router.post("/manual/search")
def manual_search_endpoint(
    payload: ManualSearchRequest,
    db: Session = Depends(get_db),
) -> dict:
    """매뉴얼 키워드 검색만 — LLM 호출 없음.

    AI 비활성/Key 미설정 상태에서도 200. 검색 결과 자체는 LLM 의존이 아니므로.
    """
    if not (payload.question or "").strip():
        raise HTTPException(400, "질문(question)을 입력하세요.")

    t0 = time.monotonic()
    try:
        result = ai_manual_qa.manual_search(payload.question)
    except Exception as e:
        ai_log.log_ai_error(db, feature="manual_search",
                            error_kind=type(e).__name__)
        _commit_silent(db)
        raise

    latency_ms = int((time.monotonic() - t0) * 1000)
    hits = len(result.get("sources", []))
    ai_log.log_ai_usage(
        db,
        feature="manual_search",
        outcome="success" if hits > 0 else "warning",
        prompt_text=result.get("masked_question", ""),
        latency_ms=latency_ms,
        error_detail=f"hits={hits}, top_score={result.get('top_score', 0)}",
    )
    _commit_silent(db)
    # top_score 는 응답에 포함 (UI 노출 가능 — 디버깅용)
    return result


@router.post("/manual/ask")
def manual_ask_endpoint(
    payload: ManualAskRequest,
    db: Session = Depends(get_db),
) -> dict:
    """업무 매뉴얼 Q&A — 검색 + LLM 답변 (sms/draft 와 동일 패턴의 에러 처리).

    503: AI 비활성 / API key 미설정 / 모델 미지정 / provider 사용 불가
    400: 빈 질문
    200: 답변 또는 "매뉴얼에서 답을 찾지 못했습니다."
    """
    if not (payload.question or "").strip():
        raise HTTPException(400, "질문(question)을 입력하세요.")

    s = _get_or_create_setting(db)

    if not s.enabled:
        ai_log.log_ai_blocked(
            db, feature="manual_ask",
            reason="ai request blocked because ai disabled",
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked because ai disabled",
        )
        _commit_silent(db)
        raise HTTPException(
            503,
            "AI 기능이 꺼져 있습니다. 관리자 → AI 설정에서 활성화해 주세요.",
        )
    if not (s.api_key or "").strip():
        ai_log.log_ai_blocked(
            db, feature="manual_ask",
            reason="ai request blocked because api key missing",
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked because api key missing",
        )
        _commit_silent(db)
        raise HTTPException(
            503,
            "AI API key 가 설정되지 않았습니다. 관리자 → AI 설정에서 입력해 주세요.",
        )
    if not (s.model or "").strip():
        ai_log.log_ai_blocked(
            db, feature="manual_ask",
            reason="ai request blocked because model missing",
        )
        _commit_silent(db)
        raise HTTPException(
            503,
            "AI 모델이 지정되지 않았습니다. 관리자 → AI 설정에서 모델명을 입력해 주세요.",
        )

    try:
        prov = ai_provider.get_provider(
            s.provider or "openai",
            model=s.model,
            api_key=s.api_key,
            base_url=s.base_url or "",
            max_tokens=int(s.max_tokens or 512),
            temperature=float(s.temperature or 0.3),
        )
    except ai_provider.AiUnavailable as e:
        ai_log.log_ai_error(
            db, feature="manual_ask",
            error_kind=f"AiUnavailable:{e.kind}",
            provider=s.provider or "", model=s.model or "",
        )
        _commit_silent(db)
        raise HTTPException(503, f"AI provider 사용 불가: {e} (kind={e.kind})")

    t0 = time.monotonic()
    try:
        result = ai_manual_qa.ask_manual_question(
            db,
            payload.question,
            provider_override=prov,
        )
    except ai_provider.AiUnavailable as e:
        ai_log.log_ai_error(
            db, feature="manual_ask",
            error_kind=f"AiUnavailable:{e.kind}",
            provider=s.provider or "", model=s.model or "",
        )
        _commit_silent(db)
        raise HTTPException(503, f"AI 호출 불가: {e} (kind={e.kind})")
    except ai_provider.AiPiiBlocked as e:
        ai_log.log_ai_blocked(
            db, feature="manual_ask",
            reason="ai request blocked by pii guard",
            provider=s.provider or "", model=s.model or "",
            pii_filter_hits=len(getattr(e, "fields", []) or []),
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked by pii guard",
        )
        _commit_silent(db)
        raise HTTPException(400, f"PII 가드: {e}")
    except ValueError as e:
        ai_log.log_ai_error(
            db, feature="manual_ask", error_kind="ValueError",
            provider=s.provider or "", model=s.model or "",
        )
        _commit_silent(db)
        raise HTTPException(400, str(e))

    latency_ms = int((time.monotonic() - t0) * 1000)
    blocked = bool(result.get("blocked"))
    not_found = bool(result.get("not_found"))
    blocked_reason = result.get("blocked_reason") or ""

    if blocked:
        ai_log.log_ai_blocked(
            db, feature="manual_ask",
            reason="ai request blocked by hallucination guard: " + blocked_reason,
            provider=s.provider or "", model=s.model or "",
            prompt_text=result.get("masked_question", ""),
            hallucination_guard_hits=int(result.get("guard_hits", 0)),
        )
        ai_log.log_ai_setting_change(
            db, action="ai.blocked",
            detail="ai request blocked by hallucination guard: " + blocked_reason,
        )
    elif not_found:
        ai_log.log_ai_warning(
            db, feature="manual_ask",
            reason=blocked_reason or "not_found",
            provider=s.provider or "", model=s.model or "",
            prompt_text=result.get("masked_question", ""),
            latency_ms=latency_ms,
        )
    else:
        ai_log.log_ai_usage(
            db,
            feature="manual_ask",
            provider=s.provider or "",
            model=s.model or "",
            outcome="success",
            prompt_text=result.get("masked_question", ""),
            response_text=result.get("answer", ""),
            latency_ms=latency_ms,
            hallucination_guard_hits=int(result.get("guard_hits", 0)),
        )
    _commit_silent(db)
    return result


# ──────────── 단계 6 엔드포인트 (AI 자연어 휴무 등록, 세션 13) ────────────
#
# 정책 (절대 위반 X):
#   - parse / preview 는 DB 수정 안 함. execute 만 (employee_leaves) 에 1행 upsert.
#   - execute 는 confirm=True + HMAC 토큰 검증 통과 시에만 실행.
#   - 기존 휴무 헬퍼 (_upsert_employee_leave_core) 를 재사용 — 단일 진실원천.
#   - 자세한 spec: docs/specs/04_ai_action_leave.md

class ActionParseIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


class ActionPreviewIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


class ActionExecuteIn(BaseModel):
    preview_token: str
    confirm: bool = False
    overwrite_acknowledged: bool = False
    memo: str = Field(default="", max_length=200)


def _action_leave_provider(db: Session = Depends(get_db),
                           _: bool = Depends(require_admin)) -> ai_provider.AiProvider:
    """AI 자연어 휴무 엔드포인트의 provider dependency.

    설정·readiness 검증 + Provider 인스턴스 반환. 테스트는
    `app.dependency_overrides[_action_leave_provider] = lambda: FakeProvider(...)` 로 주입.

    503 에러는 라우터 함수 안에서 발생 — dependency 가 raise 하면 cleanup 어렵다.
    """
    s = _get_or_create_setting(db)
    if not s.enabled:
        raise HTTPException(503, "AI 기능이 꺼져 있습니다. 관리자 → AI 설정에서 활성화해 주세요.")
    if not (s.api_key or "").strip():
        raise HTTPException(503, "AI API key 가 설정되지 않았습니다.")
    if not (s.model or "").strip():
        raise HTTPException(503, "AI 모델이 지정되지 않았습니다.")
    try:
        return ai_provider.get_provider(
            s.provider or "openai",
            model=s.model,
            api_key=s.api_key,
            base_url=s.base_url or "",
            max_tokens=int(s.max_tokens or 512),
            temperature=float(s.temperature or 0.3),
        )
    except ai_provider.AiUnavailable as e:
        raise HTTPException(503, f"AI provider 사용 불가: {e}")


def _serialize_parse_result(r: ai_action_leave.ParseResult) -> dict:
    return {
        "ok": r.ok,
        "outcome": r.outcome,
        "parsed": r.parsed,
        "warnings": r.warnings,
        "safe_to_continue": r.safe_to_continue,
        "message": r.message,
    }


def _serialize_preview_result(r: ai_action_leave.PreviewResult) -> dict:
    return {
        "ok": r.ok,
        "outcome": r.outcome,
        "candidate": r.candidate,
        "mode": r.mode,
        "existing": r.existing,
        "appointments_count": r.appointments_count,
        "warnings": r.warnings,
        "safe_to_execute": r.safe_to_execute,
        "preview_token": r.preview_token,
        "preview_token_exp": r.preview_token_exp,
        "message": r.message,
    }


@router.post("/action/parse")
def action_parse(payload: ActionParseIn,
                 db: Session = Depends(get_db),
                 provider: ai_provider.AiProvider = Depends(_action_leave_provider),
                 _: bool = Depends(require_admin)):
    """자연어 → LLM JSON 추출 (DB 미접근, 토큰 발급 안 함).

    이 엔드포인트는 디버깅·투명성용이다. 실제 등록은 preview/execute 사용.
    parse 응답을 그대로 신뢰해서는 안 됨 — preview/execute 가 다시 검증한다.
    """
    s = _get_or_create_setting(db)
    r = ai_action_leave.parse(db, text=payload.text, provider=provider, settings=s)
    return _serialize_parse_result(r)


@router.post("/action/preview")
def action_preview(payload: ActionPreviewIn,
                   db: Session = Depends(get_db),
                   provider: ai_provider.AiProvider = Depends(_action_leave_provider),
                   _: bool = Depends(require_admin)):
    """LLM 추출 + DB 매칭/검증 + HMAC 토큰 발급. DB 수정 절대 없음."""
    s = _get_or_create_setting(db)
    r = ai_action_leave.preview(db, text=payload.text, provider=provider, settings=s)
    return _serialize_preview_result(r)


@router.post("/action/execute")
def action_execute(payload: ActionExecuteIn,
                   db: Session = Depends(get_db),
                   _: bool = Depends(require_admin)):
    """confirm + 토큰 검증 + TOCTOU 재조회 + EmployeeLeave upsert.

    이 엔드포인트는 Provider 의존성이 없다 (LLM 호출 없음).
    """
    r = ai_action_leave.execute(
        db,
        preview_token=payload.preview_token,
        confirm=payload.confirm,
        overwrite_acknowledged=payload.overwrite_acknowledged,
        memo=payload.memo,
    )
    body = {
        "ok": r.ok,
        "outcome": r.outcome,
        "leave_id": r.leave_id,
        "mode": r.mode,
        "message": r.message,
    }
    if r.ok:
        return body
    if r.outcome in ("conflict_changed", "therapist_changed"):
        return JSONResponse(content=body, status_code=409)
    if r.outcome == "db_error":
        return JSONResponse(content=body, status_code=500)
    # 그 외 (not_confirmed, overwrite_not_acknowledged, token_*) → 400
    return JSONResponse(content=body, status_code=400)
