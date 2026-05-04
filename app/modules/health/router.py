"""F-13 /api/health 라우터 (post-19-P / 20-2 그룹 B).

# NOTE: 새 endpoint = /api/health (서버 전체 진단). 기존 /api/admin/status /
# /api/ai/status / /api/ai/health/public 보존.
# SAFETY: 인증 ⊥ — public health check (외부 모니터링 호환). API key /
# PII 원문 미포함.
"""
from fastapi import APIRouter

from app.modules.health.service import collect_health_snapshot

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def get_health() -> dict:
    """서버 전체 진단 — 6개 키 (사용자 §4-B 권장값)."""
    return collect_health_snapshot()
