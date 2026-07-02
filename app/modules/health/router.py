"""F-13 /api/health 라우터 (post-19-P / 20-2 그룹 B).

# NOTE: 새 endpoint = /api/health (서버 전체 진단). 기존 /api/admin/status /
# /api/ai/status / /api/ai/health/public 보존.
# SAFETY: 인증 ⊥ — public health check (외부 모니터링 호환). API key /
# PII 원문 미포함.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import APP_VERSION
from app.modules.health.service import collect_health_snapshot

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def get_health() -> dict:
    """서버 전체 진단 — 6개 키 (사용자 §4-B 권장값)."""
    return collect_health_snapshot()


@router.get("/version")
def get_version() -> JSONResponse:
    """현재 서버 버전만 돌려주는 초경량 endpoint.

    서브 PC(브라우저)가 주기적으로 폴링해 페이지 로드 버전과 비교 →
    다르면 "새 버전" 배너를 띄운다. /health 와 달리 DB/디스크 접근이 없어
    잦은 폴링에 적합하다. 인증 ⊥ (public). 항상 최신값을 받도록 no-cache.
    """
    return JSONResponse(
        {"version": APP_VERSION},
        headers={"Cache-Control": "no-cache"},
    )
