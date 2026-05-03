"""modules.health — 관리자 health / 상태 조회 facade (19-2 후보 구조).

본 패키지는 19-2 시점에 *신설* 되며, ``/api/ai/health`` (admin 9키) +
``/api/ai/health/public`` (4키) + ``/api/ai/status`` (18-7) 의 *상태 조회 helper*
재사용 진입점이다.

19-2 본 세션 범위:
  - ``app.services.ai.health`` 의 ``build_admin_status`` / ``derive_*`` 를 *re-export*
    하는 facade — ``app/core/config.py`` wrapper 와 동일 패턴.
  - 신규 라우터 추가 ⊥. ``/api/health`` (서버 상태) 신설은 post-19-P 후속 (M-28).
  - 기존 ``/api/ai/health`` / ``/api/ai/health/public`` / ``/api/ai/status``
    응답 키 / URL / 인증 정책 100% 보존.

# COMPAT: ``from app.services.ai.health import build_admin_status`` 기존 경로는
#         그대로 동작. ``from app.modules.health import build_admin_status`` 신규
#         경로도 동시 지원.

# NOTE: ``/api/health`` (서버 전체 상태) 신설은 post-19-P (M-28) — 본 19-2 는
#       *분류 / 후속 검토 명시만*. 새 endpoint / 새 응답 키 ⊥.
"""

from app.services.ai.health import (  # noqa: F401 — re-export
    AI_MODE_AI_ASSIST,
    AI_MODE_LOCAL_FIRST,
    AI_MODE_LOCAL_ONLY,
    DEFAULT_RECENT_HOURS,
    DEFAULT_RECENT_LIMIT,
    ERROR_DETAIL_DISPLAY_LIMIT,
    MAX_RECENT_LIMIT,
    SEARCH_MODE_DISABLED,
    SEARCH_MODE_HYBRID,
    SEARCH_MODE_KEYWORD,
    SEARCH_MODE_VECTOR,
    LastReindex,
    RecentLogEntry,
    build_admin_status,
    count_chunks,
    count_documents,
    count_vectors,
    derive_ai_mode,
    derive_external_api_status,
    derive_search_mode,
    derive_vector_status,
    get_last_reindex,
    get_prompt_versions,
    get_recent_logs,
)

__all__ = [
    "AI_MODE_AI_ASSIST",
    "AI_MODE_LOCAL_FIRST",
    "AI_MODE_LOCAL_ONLY",
    "DEFAULT_RECENT_HOURS",
    "DEFAULT_RECENT_LIMIT",
    "ERROR_DETAIL_DISPLAY_LIMIT",
    "MAX_RECENT_LIMIT",
    "SEARCH_MODE_DISABLED",
    "SEARCH_MODE_HYBRID",
    "SEARCH_MODE_KEYWORD",
    "SEARCH_MODE_VECTOR",
    "LastReindex",
    "RecentLogEntry",
    "build_admin_status",
    "count_chunks",
    "count_documents",
    "count_vectors",
    "derive_ai_mode",
    "derive_external_api_status",
    "derive_search_mode",
    "derive_vector_status",
    "get_last_reindex",
    "get_prompt_versions",
    "get_recent_logs",
]
