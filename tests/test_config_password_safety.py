"""config.json 동시 저장/손상 시 관리자 비밀번호 보존 회귀 테스트.

배경 (v1.3.31): 요청 스레드풀 + sync/backup 백그라운드 스레드가 동시에
``save_config`` 를 호출하면, 과거엔 고정 tmp 파일명을 공유해 서로의 쓰기를
덮어써 ``config.json`` 이 깨졌다. 다음 ``load_config`` 가 이를 손상으로 보고
기본값(비번 ``admin1234``)으로 재생성 → 변경한 관리자 비밀번호가 "틀렸다"고
거부되던 간헐적 문제가 있었다.

수정:
  ① save_config: 호출별 고유 tmp 이름 + Lock 으로 동시 쓰기 직렬화 (손상 방지)
  ② load_config: 손상 시에도 비번 해시 등 핵심 비밀값을 건져 보존 (salvage)
"""
from __future__ import annotations

import threading

import pytest

from app import config as cfgmod
from app.services import auth


@pytest.fixture
def isolated_appdata(tmp_path, monkeypatch):
    """APPDATA 를 격리 디렉터리로 — 운영 config.json 미접근."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("DOSU_DB_PATH", raising=False)
    # auth 모듈 인메모리 상태 초기화 (다른 테스트 누수 차단)
    auth._sessions.clear()
    auth._reset_failures()
    return tmp_path


def test_corrupted_config_preserves_changed_password(isolated_appdata):
    """손상된 config.json 이어도 변경된 관리자 비밀번호 해시를 건져 보존한다."""
    auth.set_admin_password("mysecret99")
    cfg_path = cfgmod.get_config_path()
    hash_val = cfgmod.load_config()["admin_password_hash"]
    assert auth.verify_password("mysecret99", hash_val)

    # 동시 쓰기로 인한 손상 모사: 유효 JSON 이 아니지만 해시 라인은 남아있는 상태
    broken = (
        '{\n  "admin_password_hash": "%s",\n'
        '  "admin_password_changed": true,\n  "node_id": "keepme",\n  GARBAGE'
        % hash_val
    )
    cfg_path.write_text(broken, encoding="utf-8")

    recovered = cfgmod.load_config()

    # 비번 해시 / 변경 플래그 / node_id 보존
    assert recovered["admin_password_hash"] == hash_val
    assert recovered["admin_password_changed"] is True
    assert recovered["node_id"] == "keepme"
    # 변경했던 실제 비밀번호로 검증 성공 (admin1234 로 초기화되지 않음)
    assert auth.verify_password("mysecret99", recovered["admin_password_hash"])
    assert not auth.verify_password("admin1234", recovered["admin_password_hash"])
    # 손상 원본은 .broken_* 으로 보존
    assert list(cfg_path.parent.glob("config.json.broken_*"))


def test_concurrent_save_config_does_not_corrupt(isolated_appdata):
    """다수 스레드가 동시에 save_config 해도 config.json 이 깨지지 않는다."""
    base = cfgmod.load_config()
    base["admin_password_hash"] = "pbkdf2_sha256$200000$aabbccdd$eeff0011"

    errors: list[Exception] = []

    def worker(i: int):
        try:
            c = dict(base)
            for n in range(30):
                c["update_last_seen_version"] = f"{i}-{n}"
                cfgmod.save_config(c)
        except Exception as e:  # pragma: no cover - 실패 시 진단용
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"동시 save_config 중 예외: {errors}"

    final = cfgmod.load_config()
    # 비번 해시 보존 + config.json 유효 (load 가 salvage 경로로 빠지지 않음)
    assert final["admin_password_hash"] == "pbkdf2_sha256$200000$aabbccdd$eeff0011"
    parent = cfgmod.get_config_path().parent
    # 임시파일 잔재 없음 / 손상 재생성 흔적 없음
    assert not list(parent.glob("config.json.*.tmp"))
    assert not list(parent.glob("config.json.broken_*"))


def test_concurrent_save_keeps_login_working(isolated_appdata):
    """비번 변경 후 동시 저장 부하를 줘도 변경한 비번으로 로그인 성공."""
    auth.set_admin_password("clinicPW2026")

    def churn(i: int):
        for _ in range(25):
            cfg = cfgmod.load_config()
            cfg["update_last_seen_version"] = str(i)
            cfgmod.save_config(cfg)

    threads = [threading.Thread(target=churn, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    auth._reset_failures()
    token = auth.login("clinicPW2026")
    assert token, "변경한 비밀번호로 로그인 실패 — config 동시 저장이 비번을 손상시킴"
    assert not auth.login("admin1234"), "기본 비번이 통과되면 안 됨 (초기화 발생)"
