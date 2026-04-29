"""AI / RAG 라우터 (v1.3 단계 1+2 통합본).

분리 원칙:
  - 기존 app/routers/api.py 에 AI 코드를 섞지 않는다.
  - AI 는 DB 변경/SMS 발송을 직접 하지 않는다 (라우터에서 그런 동작 금지).
  - 외부 LLM 호출은 다음 세션에서 추가 — 지금은 health/설정 골격 + sms 검증만.

이 단계에 포함:
  단계 1 (Provider 골격, admin 전용):
    - GET  /api/ai/health           : SDK 가능 여부, 설정 상태
    - GET  /api/ai/providers        : 선택 가능한 provider 목록
    - GET  /api/ai/settings         : 현재 설정 (api_key 마스킹)
    - PUT  /api/ai/settings         : 설정 저장
  단계 2 (SMS 검증, 일반 — 기존 POST /api/sms/send 와 권한 일관):
    - POST /api/ai/sms/validate     : 예약문자 발송 전 BLOCKER/WARNING 검증
                                      (LLM 미사용, 결정론적 로직)
"""
from __future__ import annotations
import importlib
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import models
from ..services import auth
from ..services.ai import provider as ai_provider
from ..services.ai import validators


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


def _sdk_available(name: str) -> bool:
    """SDK import 가 실제로 가능한지. import 실패해도 예외 throw 안 함."""
    if name == "openai":
        try:
            importlib.import_module("openai")
            return True
        except Exception:
            return False
    if name == "anthropic":
        try:
            importlib.import_module("anthropic")
            return True
        except Exception:
            return False
    if name == "local":
        return False  # v2 보류
    return False


# ──────────────── 단계 1 엔드포인트 (admin 전용) ────────────────

@router.get("/health")
def ai_health(db: Session = Depends(get_db),
              _: bool = Depends(require_admin)):
    """AI 기능 상태 점검 — 관리자 전용.

    응답:
      {
        "enabled": False,
        "provider": "openai",
        "model": "",
        "api_key_set": False,
        "sdk_installed": {"openai": False, "anthropic": False, "local": False},
        "ready": False,           # enabled + key + model + sdk 다 갖춰졌는지
        "version": "v1.3-stage1"
      }
    """
    s = _get_or_create_setting(db)
    sdk_status = {p: _sdk_available(p) for p in ai_provider.list_known_providers()}
    ready = bool(
        s.enabled and s.api_key and s.model and sdk_status.get(s.provider or "")
    )
    return {
        "enabled": bool(s.enabled),
        "provider": s.provider or "openai",
        "model": s.model or "",
        "api_key_set": bool(s.api_key),
        "sdk_installed": sdk_status,
        "ready": ready,
        "version": "v1.3-stage1",
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
    """
    s = _get_or_create_setting(db)

    if "enabled" in payload:
        s.enabled = bool(payload.get("enabled"))

    if "provider" in payload:
        prov = (payload.get("provider") or "").strip().lower()
        if prov and prov not in ai_provider.list_known_providers():
            raise HTTPException(400, f"알 수 없는 provider: {prov!r}")
        if prov:
            s.provider = prov

    if "model" in payload:
        s.model = (payload.get("model") or "").strip()[:100]

    if payload.get("clear_api_key") is True:
        s.api_key = ""
    elif "api_key" in payload:
        new_key = payload.get("api_key")
        if isinstance(new_key, str) and new_key.strip():
            s.api_key = new_key.strip()
        # 빈 문자열 / None 이면 기존 값 유지

    if "base_url" in payload:
        s.base_url = (payload.get("base_url") or "").strip()[:500]

    if "max_tokens" in payload:
        try:
            v = int(payload.get("max_tokens"))
        except (TypeError, ValueError):
            raise HTTPException(400, "max_tokens 는 정수여야 합니다.")
        if v < 1 or v > 8000:
            raise HTTPException(400, "max_tokens 범위: 1~8000")
        s.max_tokens = v

    if "temperature" in payload:
        try:
            v = float(payload.get("temperature"))
        except (TypeError, ValueError):
            raise HTTPException(400, "temperature 는 숫자여야 합니다.")
        if v < 0 or v > 2:
            raise HTTPException(400, "temperature 범위: 0.0~2.0")
        s.temperature = v

    if "pii_guard_enabled" in payload:
        s.pii_guard_enabled = bool(payload.get("pii_guard_enabled"))

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
    items = [it.model_dump() for it in payload.items]
    results = validators.validate_sms_batch(
        db, items, dup_window_minutes=payload.dup_window_minutes,
    )
    return {"results": results}
