"""pytest 공통 설정 — DB 격리 + TestClient + 시드.

⚠️ 가장 중요한 부분은 **module-level (import-time) 코드** 다.
   pytest 가 어떤 테스트 파일이든 import 하기 전에 가장 먼저 실행되어야
   app.config / app.database 의 module-load 시점 DB_URL 결정 전에 환경을 격리할 수 있다.

격리 흐름:
  1) APPDATA 환경변수를 tests/temp/appdata_<uuid>/ 로 강제 (Phase A)
     → app.config.get_appdata_dir() 가 그 경로 반환
     → app.database 의 DB_URL 이 임시 경로로 결정
  2) tests.harness.db_guard.assert_safe_db_path() 로 즉시 검증
  3) app.services.sync.start_sync_worker / app.services.backup.start_auto_backup 무력화
     (백그라운드 스레드가 테스트 중 동작하지 않도록)
  4) app.main import → init_db() 가 임시 DB 에서 실행 (마이그레이션 + 자동 시드)
  5) session-scoped fixture 가 추가 테스트 시드 (직원/환자/휴무) 멱등 적용
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# ──────────────────────── 1) APPDATA + DOSU_DB_PATH 격리 ────────────────────────
#
# 두 환경변수를 모두 임시 폴더로 강제:
#   APPDATA       → tests/temp/appdata_<uuid>/  (config.json, schema_version.txt, backups/)
#   DOSU_DB_PATH  → tests/temp/test_clinic_<uuid>.db  (DB 파일 — 'clinic.db' 이름 직접 사용 안 함)
#
# DOSU_DB_PATH 는 app/config.py::get_db_path() 가 우선적으로 참조한다 (Phase C).

_TESTS_DIR = Path(__file__).resolve().parent
_TEMP_DIR = _TESTS_DIR / "temp"
_TEMP_DIR.mkdir(exist_ok=True)

_SESSION_TAG = uuid.uuid4().hex[:8]

# APPDATA 격리 (config.json, schema_version.txt, backups/ 가 운영 환경에 생성되는 것 방지)
_ISOLATED_APPDATA = _TEMP_DIR / f"appdata_{_SESSION_TAG}"
_ISOLATED_APPDATA.mkdir()
os.environ["APPDATA"] = str(_ISOLATED_APPDATA)

# DOSU_DB_PATH 격리 — DB 파일명에 'test_clinic_' 사용 (clinic.db 이름 직접 사용 금지)
_ISOLATED_DB = _TEMP_DIR / f"test_clinic_{_SESSION_TAG}.db"
os.environ["DOSU_DB_PATH"] = str(_ISOLATED_DB)

# 프로젝트 루트를 sys.path 에 (run_tests.bat 외 다양한 호출 경로 대응)
_PROJECT_ROOT = _TESTS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ──────────────────────── 2) 안전 검증 (1차) ────────────────────────

from tests.harness.db_guard import assert_safe_db_path  # noqa: E402

_VERIFIED_DB_PATH = assert_safe_db_path()
print(f"[하네스] 테스트 DB 경로: {_VERIFIED_DB_PATH}")

# ──────────────────────── 3) 백그라운드 워커 무력화 ────────────────────────

# app.main 이 import 되면 create_app() 안에서 start_sync_worker/start_auto_backup 호출됨.
# from-import 직전에 함수 객체를 no-op 으로 교체.
# fmt: off — 의도적 import 순서 (격리 → 워커 무력화 → app 본체).
import app.services.sync as _sync_mod  # noqa: I001, E402
import app.services.backup as _backup_mod  # noqa: I001, E402

_sync_mod.start_sync_worker = lambda: None
_backup_mod.start_auto_backup = lambda *a, **kw: None

# ──────────────────────── 4) app import (init_db 자동 실행) ────────────────────────

import pytest  # noqa: I001, E402
from fastapi.testclient import TestClient  # noqa: I001, E402
from app.main import app as _fastapi_app  # noqa: I001, E402
# fmt: on

# ──────────────────────── 5) Pytest fixtures ────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _harness_session_setup():
    """세션 시작 시 한 번 — DB 안전 재검증 + 테스트 시드 멱등 적용."""
    # 2차 안전망 — fixture 단계에서 다시 한 번 검증
    assert_safe_db_path()

    from tests.harness.seed_data import seed_test_data
    seed_test_data()
    yield


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient (세션 동안 재사용)."""
    with TestClient(_fastapi_app) as c:
        yield c


@pytest.fixture(scope="session")
def db_path() -> str:
    """검증된 임시 DB 경로 (smoke 테스트가 출력 확인용)."""
    return _VERIFIED_DB_PATH


# ──────────────────────── 6) 공용 FakeProvider (LLM mock) ────────────────────────
#
# 세션 13: AI 자연어 휴무 등록 테스트 + 기존 SMS draft 테스트가 공유.
# 외부 LLM 호출 절대 금지 — 테스트는 항상 이 클래스로 stub.

from app.services.ai import provider as _ai_provider  # noqa: E402, I001


class FakeProvider(_ai_provider.AiProvider):
    """결정적 LLM stub. 호출 인자 기록.

    return_text: 고정 응답. callable 이면 호출 시 prompt 를 인자로 받아 동적 결정.
    """
    name = "fake"

    def __init__(self, return_text="안녕하세요 환자A님, ㅇㅇ의원입니다."):
        super().__init__(model="fake-1", api_key="fake-key")
        self.return_text = return_text
        self.calls: list = []

    def is_ready(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "") -> _ai_provider.AiResult:
        self.calls.append({"prompt": prompt, "system": system})
        text = self.return_text
        if callable(text):
            text = text(prompt)
        return _ai_provider.AiResult(text=text)


def make_fake_provider(returns: str = "") -> FakeProvider:
    """팩토리 — return_text 기본값을 명시적으로 지정하고 싶을 때."""
    return FakeProvider(return_text=returns or "안녕하세요 환자A님, ㅇㅇ의원입니다.")
