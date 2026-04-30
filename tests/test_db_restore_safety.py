"""DB 복원 (POST /api/restore) 안전성 회귀 방지.

검증 포인트:
  1. 손상된 / 이상한 DB 파일 업로드 시 운영 DB 가 그대로 유지된다 (400 + 운영 DB 무변경).
  2. 정상 SQLite DB 업로드 시 atomic 교체가 성공하고 200 응답.
  3. 함수 시그니처에 db: Session 의존성이 남아있지 않음 — 남으면 Windows 파일 잠금 위험.
  4. engine.dispose() 가 tmp.replace(dst) 보다 먼저 호출됨 — 순서 회귀 방지.
"""
from __future__ import annotations

import hashlib
import inspect
import sqlite3
from pathlib import Path

from app.config import get_db_path
from app.routers import api as api_mod


def _admin_token(client) -> str:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def _hash_db() -> str:
    return hashlib.sha256(Path(get_db_path()).read_bytes()).hexdigest()


# ─────────────────────────────────────────────────────────
# (1) 손상된 업로드 → 400 + 운영 DB 무변경
# ─────────────────────────────────────────────────────────


def test_restore_corrupted_upload_keeps_operational_db_intact(client):
    before = _hash_db()
    token = _admin_token(client)

    # 진짜 SQLite 시그니처가 아닌 임의 바이트 (sqlite3.connect 가 열어보면 IntegrityError)
    garbage = b"NOT_A_SQLITE_DB_HEADER_" + (b"\x00" * 4096)
    resp = client.post(
        "/api/restore",
        headers={"x-admin-token": token},
        files={"file": ("garbage.db", garbage, "application/octet-stream")},
    )
    assert resp.status_code == 400, resp.text
    after = _hash_db()
    assert before == after, (
        "손상된 업로드가 거부되긴 했으나 운영 DB 가 변경되었습니다 — "
        "tmp 파일 검증 전에 dst 를 건드리는 회귀."
    )


def test_restore_requires_admin(client):
    """관리자 토큰 없이 호출하면 401."""
    resp = client.post(
        "/api/restore",
        files={"file": ("anything.db", b"x", "application/octet-stream")},
    )
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────
# (2) 정상 DB 업로드 → 200 + atomic 교체 성공
# ─────────────────────────────────────────────────────────


def test_restore_valid_db_upload_succeeds(client):
    """현재 운영 DB 자체를 업로드 → atomic 교체 후에도 정상 동작.

    self-restore 이므로 데이터는 동일하게 유지됨 — 다른 테스트에 영향 안 미침.
    """
    token = _admin_token(client)
    current_bytes = Path(get_db_path()).read_bytes()
    # 빈 DB 도 아닌, 시드된 운영 DB 가 들어있어야 의미가 있음
    assert len(current_bytes) > 0

    resp = client.post(
        "/api/restore",
        headers={"x-admin-token": token},
        files={"file": ("self_backup.db", current_bytes, "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True

    # 교체된 파일이 정상 SQLite 로 열리고 무결성 ok
    new_path = Path(get_db_path())
    assert new_path.exists()
    con = sqlite3.connect(str(new_path))
    try:
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        con.close()
    assert ok == "ok"


def test_restore_works_after_dispose_for_subsequent_requests(client):
    """restore 후 (engine.dispose 거친 뒤) 일반 GET 요청도 정상 — connection lazy-reconnect 검증."""
    token = _admin_token(client)
    current_bytes = Path(get_db_path()).read_bytes()
    client.post(
        "/api/restore",
        headers={"x-admin-token": token},
        files={"file": ("self.db", current_bytes, "application/octet-stream")},
    )
    # restore 직후 일반 endpoint 가 200 으로 응답해야 함 (engine 이 새 connection 으로 lazy 재접속)
    resp = client.get("/api/treatments")
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────
# (3) 함수 시그니처 / 본문 회귀 방지
# ─────────────────────────────────────────────────────────


def test_restore_does_not_take_db_session_dependency():
    """restore 시그니처에 db: Session 의존성이 없어야 함.

    있으면 endpoint 호출 시 SQLAlchemy 가 connection 을 잡고 들어와
    Windows 에서 tmp.replace(dst) 가 파일 잠금으로 실패할 위험이 있음.
    """
    sig = inspect.signature(api_mod.restore)
    suspect = []
    for name, param in sig.parameters.items():
        annot = str(param.annotation)
        if name == "db" or "Session" in annot:
            suspect.append((name, annot))
    assert not suspect, (
        f"restore() 가 db/Session 의존성을 가지고 있습니다: {suspect} — "
        "Windows 파일 잠금 위험으로 회귀."
    )


def test_restore_calls_engine_dispose_before_replace():
    """소스 본문에서 engine.dispose() 가 tmp.replace(dst) 보다 먼저 등장.

    docstring 에도 'tmp.replace(dst)' 가 설명용으로 들어있을 수 있어,
    docstring 블록을 제거한 뒤 실제 코드 부분만 검사한다.
    """
    src = inspect.getsource(api_mod.restore)
    # docstring 제거 — """ ... """ 사이를 빈 문자열로 치환
    import re
    code_only = re.sub(r'""".*?"""', '', src, count=1, flags=re.DOTALL)

    assert "engine.dispose()" in code_only, "engine.dispose() 호출이 restore 에서 사라짐 — 회귀."
    dispose_idx = code_only.index("engine.dispose()")
    replace_idx = code_only.index("tmp.replace(")
    assert dispose_idx < replace_idx, (
        "engine.dispose() 가 tmp.replace() 보다 뒤에 있음 — Windows 파일 잠금 위험."
    )
