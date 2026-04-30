"""Sync / backup worker 의 graceful shutdown 회귀 방지 테스트.

apply_update 가 os._exit(0) 로 강제종료하기 전에 백그라운드 워커들을
정상 정지시켜 mid-operation IO 가 잘리지 않게 해야 함.

이 테스트가 깨지면:
  - sync.stop_sync_worker / backup.stop_auto_backup 의 시그니처가 바뀌었거나
  - apply_update 안에서 두 정지 호출이 누락된 것
"""
from __future__ import annotations

import threading
import time

from app.services import backup as backup_mod
from app.services import sync as sync_mod

# ─────────────────────────────────────────────────────────
# (1) 정지 함수 자체의 동작 — stop_flag set 여부
# ─────────────────────────────────────────────────────────


def test_sync_stop_flag_signals_loop_to_exit():
    """sync 모듈 내부 _stop_flag 를 set 하면 loop 가 빠져나오도록 설계되어 있어야 함."""
    # conftest 가 start_sync_worker 를 no-op 로 패치했으므로,
    # 직접 mini loop 를 돌려서 stop_flag 응답성 확인
    sync_mod._stop_flag.clear()
    cycles = []

    def mini_loop():
        while not sync_mod._stop_flag.is_set():
            cycles.append(1)
            if sync_mod._stop_flag.wait(10.0):  # interruptible sleep
                break

    t = threading.Thread(target=mini_loop, daemon=True)
    t.start()
    time.sleep(0.05)  # 한 사이클 정도 돌게
    sync_mod._stop_flag.set()
    t.join(timeout=1.0)

    assert not t.is_alive(), "stop_flag set 후에도 loop 가 안 끝남 — wait() 가 인터럽트 가능해야 함"
    assert len(cycles) >= 1


def test_stop_sync_worker_function_exists_and_returns_bool():
    """stop_sync_worker(timeout=...) 시그니처 + bool 반환 확인."""
    assert callable(getattr(sync_mod, "stop_sync_worker", None))
    # 워커가 안 떠있을 때(테스트 환경) 호출해도 안전해야 하고 True 반환
    result = sync_mod.stop_sync_worker(timeout=0.1)
    assert isinstance(result, bool)


def test_stop_auto_backup_sets_flag():
    """backup.stop_auto_backup() 호출 후 _stop_flag.is_set() 가 True 여야 함."""
    backup_mod._stop_flag.clear()
    assert not backup_mod._stop_flag.is_set()
    backup_mod.stop_auto_backup()
    assert backup_mod._stop_flag.is_set()


# ─────────────────────────────────────────────────────────
# (2) apply_update 가 stop 함수들을 호출하는지 — 코드 검증
# ─────────────────────────────────────────────────────────


def test_apply_update_imports_stop_functions():
    """api.py 의 apply_update 가 stop_auto_backup / stop_sync_worker 를 호출해야 함.

    런타임으로 호출 자체를 검증하기 어려운 이유: apply_update 는 _is_frozen() 체크가 있어
    개발 환경에선 즉시 400 으로 거부됨. 따라서 소스 단위 검증 — 두 정지 함수 import 가
    존재하는지 직접 텍스트로 확인.
    """
    import inspect

    from app.routers import api as api_mod
    src = inspect.getsource(api_mod.apply_update)
    assert "stop_auto_backup" in src, (
        "apply_update 가 stop_auto_backup 을 호출해야 합니다 — "
        "graceful shutdown 누락 시 백업 daemon thread 가 mid-copy 에서 죽어 부분 백업 파일이 남음."
    )
    assert "stop_sync_worker" in src, (
        "apply_update 가 stop_sync_worker 를 호출해야 합니다 — "
        "graceful shutdown 누락 시 sync HTTP 요청이 중간에 끊겨 부분 적용 op 가 잔존할 수 있음."
    )
