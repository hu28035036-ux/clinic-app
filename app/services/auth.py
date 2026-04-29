"""관리자 인증 - PBKDF2 해싱 + 인메모리 세션 토큰"""
import os, hmac, hashlib, secrets, time
from typing import Optional

from ..config import load_config, save_config

DEFAULT_PASSWORD = "admin1234"
SESSION_TTL_SEC = 8 * 3600  # 8시간

# {token: expires_at_epoch}
_sessions: dict[str, float] = {}

# 로그인 실패 추적
_failed_count: int = 0
_lock_until: float = 0.0
MAX_FAILURES = 5
LOCK_DURATION_SEC = 300  # 5분


def _record_failure():
    global _failed_count, _lock_until
    _failed_count += 1
    if _failed_count >= MAX_FAILURES:
        _lock_until = time.time() + LOCK_DURATION_SEC
        _failed_count = 0


def _reset_failures():
    global _failed_count, _lock_until
    _failed_count = 0
    _lock_until = 0.0


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


def login(password: str) -> Optional[str]:
    # 간단한 레이트 리미트: 5회 연속 실패 시 5분 잠금
    now = time.time()
    if _lock_until > now:
        return None
    if not verify_password(password, get_admin_hash()):
        _record_failure()
        return None
    _reset_failures()
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_TTL_SEC
    _gc()
    return token


def get_lock_remaining() -> int:
    """잠금 남은 초. 0이면 잠금 안 됨."""
    rem = int(_lock_until - time.time())
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
