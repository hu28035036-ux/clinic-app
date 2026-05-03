"""core.database — ``app.database`` re-export wrapper.

19-1 단위화 리팩토링 1단계: 기존 ``app/database.py`` 의 공개 API
(SCHEMA_VERSION / DB_URL / engine / SessionLocal / Base / get_db / init_db) 를
``app.core.database`` 경로로도 접근 가능하게 한다.

# COMPAT: 기존 ``from app.database import ...`` 경로는 그대로 동작.
#         ``from app.core.database import ...`` 신규 경로도 동시 지원.
#         실제 본체 이동은 19-x 후속 (TODO(19-x): wrapper 제거 + 본체 이동).

# SAFETY: ``init_db()`` 가 호출하는 ``get_db_path()`` 는 DOSU_DB_PATH 환경변수
#         우선 — 테스트/하네스에서 운영 DB 경로 미접근. m001~m013 마이그레이션
#         자동 적용 정책 보존.

# RISK: 본 wrapper 가 import 되는 시점에 ``app.database`` 가 같이 import 되므로
#       SQLAlchemy engine 이 즉시 생성된다. core/database 를 import 하기만 해도
#       엔진이 생성되는 건 ``app.database`` 의 기존 동작과 동일.
"""
from app.database import (  # noqa: F401 — re-export
    SCHEMA_VERSION,
    DB_URL,
    engine,
    SessionLocal,
    Base,
    get_db,
    init_db,
)

__all__ = [
    "SCHEMA_VERSION",
    "DB_URL",
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "init_db",
]
