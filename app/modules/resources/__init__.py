"""modules.resources — 자원 도메인 (post-19-P / 20-3-5 / F-3 (a) 치료실만).

사용자 §7-7 결정 정합:
  - (a) v1 = type='room' 만 사용 (장비 후속).
  - (i) F-1 Room 과 별개 도메인.
  - (i) capacity=1 — 같은 자원 동시 예약 ⊥.
  - (i) 인력 자원 미도입.
  - (i) F-2 시리즈 + F-3 자원 충돌 검사 통합 — 시리즈 등록 시 자원 충돌도 검사.

# SAFETY: 자원 변경은 admin 권한 (require_admin). 자원 충돌 검사는 응답에 PII 부재.
"""

from app.modules.resources.router import router
from app.modules.resources.schemas import (
    RESOURCE_RESPONSE_KEYS,
    ResourceIn,
)
from app.modules.resources.service import (
    check_resource_conflict,
    serialize_resource,
    serialize_resources,
)

__all__ = [
    "RESOURCE_RESPONSE_KEYS",
    "ResourceIn",
    "check_resource_conflict",
    "router",
    "serialize_resource",
    "serialize_resources",
]
