"""core.config — ``app.config`` re-export wrapper.

19-1 단위화 리팩토링 1단계: 기존 ``app/config.py`` 의 모든 공개 API
(APP_NAME / APP_VERSION / APP_BUILD_DATE / get_appdata_dir / get_db_path /
get_config_path / get_backup_dir / DEFAULT_CONFIG / load_config / save_config /
resource_path) 를 ``app.core.config`` 경로로도 접근 가능하게 한다.

# COMPAT: 기존 ``from app.config import ...`` 경로는 그대로 동작.
#         ``from app.core.config import ...`` 신규 경로도 동시 지원.
#         실제 본체 이동은 19-x 후속 (TODO(19-x): wrapper 제거 + 본체 이동).

# SAFETY: ``get_db_path()`` 의 ``DOSU_DB_PATH`` 환경변수 우선 정책 보존 —
#         테스트/하네스에서 운영 DB 경로 (%APPDATA%\\도수치료예약\\clinic.db) 미접근.
"""
from app.config import (  # noqa: F401 — re-export
    APP_NAME,
    APP_VERSION,
    APP_BUILD_DATE,
    DEFAULT_CONFIG,
    get_appdata_dir,
    get_db_path,
    get_config_path,
    get_backup_dir,
    load_config,
    save_config,
    resource_path,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "APP_BUILD_DATE",
    "DEFAULT_CONFIG",
    "get_appdata_dir",
    "get_db_path",
    "get_config_path",
    "get_backup_dir",
    "load_config",
    "save_config",
    "resource_path",
]
