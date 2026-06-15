"""관리자 로그인 잠금 정책 회귀 테스트 (v1.3.33).

변경:
  - 완화: 5회/5분 → 10회/1분 (LAN 내부 도구 — 직원 오타로 인한 과잉 잠금 방지)
  - 분리: 전역 스칼라 카운터 → PC(IP=client_key)별 추적.
    한 PC 의 연속 실패가 다른 PC 로그인을 막지 않는다.
"""
from __future__ import annotations

import tempfile

import pytest

from app.services import auth


@pytest.fixture
def isolated_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", tempfile.mkdtemp())
    monkeypatch.delenv("DOSU_DB_PATH", raising=False)
    auth._sessions.clear()
    auth._failed_count.clear()
    auth._lock_until.clear()
    return True


def test_lockout_policy_relaxed():
    """완화된 임계 정책 가드: 10회 / 1분."""
    assert auth.MAX_FAILURES == 10
    assert auth.LOCK_DURATION_SEC == 60


def test_lock_triggers_only_after_max_failures(isolated_appdata):
    auth.set_admin_password("pwX12345")
    key = "192.168.0.5"
    # MAX_FAILURES-1 실패 → 아직 잠기지 않음
    for _ in range(auth.MAX_FAILURES - 1):
        assert auth.login("nope", client_key=key) is None
    assert auth.get_lock_remaining(key) == 0
    # 잠기기 전엔 올바른 비밀번호 정상 로그인 (+ 카운터 리셋)
    assert auth.login("pwX12345", client_key=key)
    assert auth.get_lock_remaining(key) == 0


def test_lockout_is_per_client_pc(isolated_appdata):
    """PC-A 가 잠겨도 PC-B 는 영향 없음 (전 PC 공용 잠금 회귀 방지)."""
    auth.set_admin_password("pwCorrect1")
    a, b = "10.0.0.1", "10.0.0.2"

    # PC-A: MAX_FAILURES 회 실패 → 잠김
    for _ in range(auth.MAX_FAILURES):
        assert auth.login("wrong", client_key=a) is None
    assert auth.get_lock_remaining(a) > 0
    # PC-A: 잠긴 동안 올바른 비밀번호도 거부 (의도된 잠금)
    assert auth.login("pwCorrect1", client_key=a) is None

    # PC-B: 다른 IP → 잠기지 않았고 올바른 비밀번호로 정상 로그인
    assert auth.get_lock_remaining(b) == 0
    assert auth.login("pwCorrect1", client_key=b)


def test_default_key_backward_compatible(isolated_appdata):
    """client_key 미지정(기존 호출 방식) 도 동작 — default 키 사용."""
    auth.set_admin_password("pwDefault9")
    assert auth.login("pwDefault9")  # 키 없이도 성공
    for _ in range(auth.MAX_FAILURES):
        auth.login("bad")
    assert auth.get_lock_remaining() > 0  # default 키 잠김
