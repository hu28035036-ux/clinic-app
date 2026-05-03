"""core.security — ``app.services.auth`` re-export wrapper.

19-1 단위화 리팩토링 1단계: 기존 ``app/services/auth.py`` 의 공개 API
(DEFAULT_PASSWORD / SESSION_TTL_SEC / MAX_FAILURES / LOCK_DURATION_SEC /
hash_password / verify_password / get_admin_hash / set_admin_password /
is_default_password / login / get_lock_remaining / is_valid / logout) 를
``app.core.security`` 경로로도 접근 가능하게 한다.

# COMPAT: 기존 ``from app.services.auth import ...`` 경로는 그대로 동작.
#         ``from app.core.security import ...`` 신규 경로도 동시 지원.
#         실제 본체 이동은 19-x 후속 (TODO(19-x): wrapper 제거 + 본체 이동).

# SAFETY: PBKDF2-SHA256 (200,000 iterations) + 인메모리 세션 토큰 + 5회 실패
#         시 5분 잠금 정책 보존. ``set_admin_password`` 는 기존 세션 모두 무효화
#         정책 보존. 비밀번호 원문 / 토큰은 로그/응답에 노출 ⊥.
"""
from app.services.auth import (  # noqa: F401 — re-export
    DEFAULT_PASSWORD,
    SESSION_TTL_SEC,
    MAX_FAILURES,
    LOCK_DURATION_SEC,
    hash_password,
    verify_password,
    get_admin_hash,
    set_admin_password,
    is_default_password,
    login,
    get_lock_remaining,
    is_valid,
    logout,
)

__all__ = [
    "DEFAULT_PASSWORD",
    "SESSION_TTL_SEC",
    "MAX_FAILURES",
    "LOCK_DURATION_SEC",
    "hash_password",
    "verify_password",
    "get_admin_hash",
    "set_admin_password",
    "is_default_password",
    "login",
    "get_lock_remaining",
    "is_valid",
    "logout",
]
