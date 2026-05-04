"""modules.health — 관리자 health / 상태 조회 facade (19-2 후보 구조 + 20-2 F-13).

본 패키지는 19-2 시점에 *신설* 되며, ``/api/ai/health`` (admin 9키) +
``/api/ai/health/public`` (4키) + ``/api/ai/status`` (18-7) 의 *상태 조회 helper*
재사용 진입점이다.

20-2 (post-19-P / F-13) 시점에 ``/api/health`` (서버 전체 진단) 신설 — 사용자
§4-B 권장값 6개 키 (db_ok / migration_version / backup_age / disk_free / version /
uptime). ``service.py`` + ``router.py`` 신규.

# COMPAT: ``from app.services.ai.health import build_admin_status`` 기존 경로는
#         그대로 동작. ``from app.modules.health import build_admin_status`` 신규
#         경로도 동시 지원.
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
    # 20-2 F-13 — /api/health 신설
    "collect_health_snapshot",
    "set_startup_time",
    "router",
    "HEALTH_SNAPSHOT_KEYS",
]

# 20-2 F-13 — /api/health 라우터 + service
from app.modules.health.router import router  # noqa: E402, F401
from app.modules.health.service import (  # noqa: E402, F401
    HEALTH_SNAPSHOT_KEYS,
    collect_health_snapshot,
    set_startup_time,
)
