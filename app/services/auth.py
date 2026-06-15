"""관리자 인증 - PBKDF2 해싱 + 인메모리 세션 토큰"""
import os, hmac, hashlib, secrets, time
from typing import Optional

from ..config import load_config, save_config

DEFAULT_PASSWORD = "admin1234"
SESSION_TTL_SEC = 8 * 3600  # 8시간

# {token: expires_at_epoch}
_sessions: dict[str, float] = {}

# 로그인 실패 추적 — 클라이언트(PC=IP)별로 분리.
#   과거엔 전역 스칼라 카운터라, 한 PC 가 비밀번호를 5회 틀리면 5분간
#   *모든 PC* 로그인이 잠겼다(전 PC 공용 잠금). LAN 내부용 도구에서 한 사람의
#   오타가 전 직원을 막는 건 과도 → IP 별로 추적해 다른 PC 는 영향받지 않게 하고,
#   임계도 완화(5→10회, 5분→1분).
_failed_count: dict[str, int] = {}
_lock_until: dict[str, float] = {}
MAX_FAILURES = 10
LOCK_DURATION_SEC = 60  # 1분


def _client_key(client_key=None) -> str:
    return client_key or "default"


def _record_failure(client_key=None):
    k = _client_key(client_key)
    n = _failed_count.get(k, 0) + 1
    if n >= MAX_FAILURES:
        _lock_until[k] = time.time() + LOCK_DURATION_SEC
        _failed_count[k] = 0
    else:
        _failed_count[k] = n
    _prune_locks()


def _reset_failures(client_key=None):
    """client_key 지정 시 해당 PC 만, 미지정 시 default 키만 초기화."""
    k = _client_key(client_key)
    _failed_count.pop(k, None)
    _lock_until.pop(k, None)


def _prune_locks():
    """만료된 잠금 + 0 카운트 엔트리 정리 — 장기 운영 시 dict 무한 증가 방지."""
    now = time.time()
    for k in list(_lock_until.keys()):
        if _lock_until.get(k, 0.0) <= now and not _failed_count.get(k):
            _lock_until.pop(k, None)
            _failed_count.pop(k, None)


def _hash(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${dk.hex()}"


def hash_password(password: str) -> str:
    return _hash(password, os.urandom(16))


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, dk_hex = stored.split("$")
        if algo != "pbkdf2_sha256": return False
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def get_admin_hash() -> str:
    """저장된 해시. 없으면 기본 비밀번호로 초기화."""
    cfg = load_config()
    h = cfg.get("admin_password_hash")
    if not h:
        h = hash_password(DEFAULT_PASSWORD)
        cfg["admin_password_hash"] = h
        cfg["admin_password_changed"] = False
        save_config(cfg)
    return h


def set_admin_password(new_password: str) -> None:
    if len(new_password) < 4:
        raise ValueError("비밀번호는 4자 이상이어야 합니다.")
    cfg = load_config()
    cfg["admin_password_hash"] = hash_password(new_password)
    cfg["admin_password_changed"] = True
    save_config(cfg)
    # 기존 세션 모두 무효화
    _sessions.clear()


def is_default_password() -> bool:
    """첫 실행 후 비밀번호가 한 번도 변경되지 않았는지"""
    return not load_config().get("admin_password_changed", False)


def login(password: str, client_key: Optional[str] = None) -> Optional[str]:
    # 레이트 리미트: MAX_FAILURES 회 연속 실패 시 LOCK_DURATION_SEC 잠금 (PC=IP 별).
    k = _client_key(client_key)
    now = time.time()
    if _lock_until.get(k, 0.0) > now:
        return None
    if not verify_password(password, get_admin_hash()):
        _record_failure(k)
        return None
    _reset_failures(k)
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_TTL_SEC
    _gc()
    return token


def get_lock_remaining(client_key: Optional[str] = None) -> int:
    """이 PC(client_key)의 잠금 남은 초. 0이면 잠금 안 됨."""
    k = _client_key(client_key)
    rem = int(_lock_until.get(k, 0.0) - time.time())
    return max(0, rem)


def is_valid(token: Optional[str]) -> bool:
    if not token: return False
    exp = _sessions.get(token)
    if not exp: return False
    if time.time() > exp:
        _sessions.pop(token, None); return False
    return True


def logout(token: Optional[str]) -> None:
    if token: _sessions.pop(token, None)


def _gc():
    now = time.time()
    expired = [t for t, exp in _sessions.items() if exp < now]
    for t in expired: _sessions.pop(t, None)
