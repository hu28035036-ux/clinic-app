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


# ──────────────────────── 7) 외부 SDK 호출 차단 (18-0) ────────────────────────
#
# 의도: 어떤 테스트도 실제 OpenAI/Anthropic API 를 호출하면 안 된다.
# ``app.services.ai.{openai_client,anthropic_client}`` 가 lazy import 로
# SDK 클래스를 사용하므로, SDK 모듈의 진입점 클래스를 즉시 RuntimeError 로
# 교체한다. ``app.routers.ai._check_sdk`` 는 importlib.import_module 만
# 시도하므로 이 monkeypatch 의 영향을 받지 않는다 (import 가능 + 인스턴스화 차단).
#
# 18-0 정책 (``docs/ai_harness_overview.md`` §4-1, ``docs/ai_rag_test_plan.md`` §3-8):
#   - FakeProvider/FakeEmbeddingProvider + 본 monkeypatch 로 외부 호출 차단.
#   - 실제 외부 API 호출이 발생하면 테스트 실패.
#   - 18-5 직전 ``pytest-socket`` 등 강화 도구 도입은 별도 ADR.

def _raise_external_call(*_args, **_kwargs):
    raise RuntimeError(
        "[하네스 안전망] 테스트에서 실제 외부 LLM/Embedding API 호출이 시도되었습니다. "
        "FakeProvider 또는 monkeypatch 를 사용하세요."
    )


def _block_sdk_modules() -> None:
    """openai/anthropic 의 client 클래스를 즉시 fail 하는 stub 으로 교체.

    SDK 가 설치되어 있으면 import 후 클래스를 patch.
    설치되어 있지 않으면 (= ``_check_sdk`` 가 false 처리) 아무 것도 하지 않는다.
    """
    for mod_name, attrs in (
        ("openai", ("OpenAI", "Client", "AsyncOpenAI")),
        ("anthropic", ("Anthropic", "Client", "AsyncAnthropic")),
    ):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for attr in attrs:
            if hasattr(mod, attr):
                try:
                    setattr(mod, attr, _raise_external_call)
                except Exception:
                    # frozen 또는 read-only 속성이면 패스 (테스트가 실제 호출
                    # 하지 않는 한 영향 없음).
                    pass


import importlib  # noqa: E402, I001

_block_sdk_modules()


# ──────────────────────── 8) AI 라우터 통합 테스트용 fixture (18-0) ────────────────────────
#
# manual/ask 라우터 흐름 (``app/routers/ai.py:603-750``) 은
#   ``ai_provider.get_provider(...)`` 로 매번 새 인스턴스를 만든다.
# 통합 테스트에서 FakeProvider 호출 카운트를 관찰하려면
#   (1) ``AiSetting`` 을 enabled=True 로 활성화하고
#   (2) ``ai_provider.get_provider`` 를 monkeypatch 로 FakeProvider 반환하게 한다.
# (``docs/ai_rag_current_state.md`` §1-5-2 의 권장 경로 (b))


@pytest.fixture
def ai_disabled_setting():
    """AiSetting 을 disabled 상태로 강제 (manual/ask 503 케이스용).

    세션 시작 시 ``init_db`` 의 자동 시드로 enabled=False 로 만들어지지만,
    다른 테스트가 변경했을 가능성을 대비해 명시적으로 reset.
    """
    from app.database import SessionLocal
    from app.models import models as _models

    db = SessionLocal()
    try:
        s = db.query(_models.AiSetting).filter(_models.AiSetting.id == 1).first()
        if s is None:
            s = _models.AiSetting(id=1)
            db.add(s)
        s.enabled = False
        s.api_key = ""
        s.model = ""
        db.commit()
        yield s
    finally:
        db.close()


@pytest.fixture
def ai_enabled_with_fake(monkeypatch):
    """AiSetting 을 enabled+key+model 로 활성화하고
    ``ai_provider.get_provider`` 를 FakeProvider 로 monkeypatch.

    Returns: ``FakeProvider`` 인스턴스 (테스트가 ``len(.calls)`` 단언에 사용).
    """
    from app.database import SessionLocal
    from app.models import models as _models
    from app.routers import ai as _ai_router

    db = SessionLocal()
    try:
        s = db.query(_models.AiSetting).filter(_models.AiSetting.id == 1).first()
        if s is None:
            s = _models.AiSetting(id=1)
            db.add(s)
        s.enabled = True
        s.provider = "openai"
        s.model = "test-model"
        s.api_key = "test-fake-key"
        db.commit()
    finally:
        db.close()

    fake = FakeProvider(
        return_text="발췌에 따르면 예약 문자 탭에서 작성합니다.\n\n참고: sms_compose.md"
    )
    # 라우터가 ``from ..services.ai import provider as ai_provider`` 후
    # ``ai_provider.get_provider(...)`` 로 호출하므로 모듈의 attribute 를 patch.
    monkeypatch.setattr(_ai_router.ai_provider, "get_provider",
                        lambda *a, **kw: fake)

    yield fake

    # 정리 — 다른 테스트에 영향이 가지 않도록 disabled 로 reset.
    db = SessionLocal()
    try:
        s = db.query(_models.AiSetting).filter(_models.AiSetting.id == 1).first()
        if s is not None:
            s.enabled = False
            s.api_key = ""
            s.model = ""
            db.commit()
    finally:
        db.close()
