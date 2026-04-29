"""테스트 DB 경로 안전 검증.

3중 안전망 중 2차. tests/conftest.py 가 import-time 에 한 번 호출하고,
session-scoped autouse fixture 에서 다시 한 번 호출한다.

규칙:
1. DB 경로 문자열에 'temp' 또는 'test' 가 포함되어야 한다.
2. 경로에 'appdata/roaming/도수치료예약/clinic.db' 패턴이 있는데
   '/tests/' 가 없으면 운영 경로로 간주하고 차단.
3. 위 둘 모두 통과하면 안전한 테스트 경로로 간주.
"""
from __future__ import annotations


def _normalize(p: str) -> str:
    return p.lower().replace("\\", "/")


def _is_production_pattern(p_norm: str) -> bool:
    """운영 DB 경로 패턴 감지.

    Windows: %APPDATA%\\도수치료예약\\clinic.db
       → C:/Users/<user>/AppData/Roaming/도수치료예약/clinic.db

    이 패턴이 보이는데 '/tests/' 가 경로에 없으면 운영 경로다.
    """
    return (
        "appdata/roaming/도수치료예약" in p_norm
        and "clinic.db" in p_norm
        and "/tests/" not in p_norm
    )


def assert_safe_db_path() -> str:
    """현재 app.config.get_db_path() 가 안전한 테스트 경로인지 검증.

    Returns: 검증된 DB 경로 문자열.
    Raises: RuntimeError — 운영 경로 또는 미격리 경로 감지 시.
    """
    from app.config import get_db_path

    raw = str(get_db_path())
    norm = _normalize(raw)

    if _is_production_pattern(norm):
        raise RuntimeError(
            f"[하네스 안전망] 실제 운영 DB 경로가 감지되었습니다. 테스트 중단.\n"
            f"  경로: {raw}\n"
            f"  conftest.py 의 APPDATA / DOSU_DB_PATH 격리 코드를 확인하세요."
        )

    if "temp" not in norm and "test" not in norm:
        raise RuntimeError(
            f"[하네스 안전망] 테스트 DB 경로에 'temp' 또는 'test' 가 포함되어야 합니다.\n"
            f"  경로: {raw}\n"
            f"  conftest.py 가 정상적으로 격리되었는지 확인하세요."
        )

    return raw
