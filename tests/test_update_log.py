"""GET /api/about/update-log 엔드포인트 테스트.

자동업데이트가 멈췄을 때 사용자/지원자가 어디서 멈췄는지 확인하기 위한 진단 엔드포인트.
"""
from __future__ import annotations

from pathlib import Path

from app.routers import api as api_module


def _admin_token(client) -> str:
    """관리자 로그인 토큰 — conftest 시드의 기본 비번 사용."""
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json().get("token", "")


def test_update_log_requires_admin(client):
    """관리자 토큰 없이 호출하면 401."""
    resp = client.get("/api/about/update-log")
    assert resp.status_code == 401


def test_update_log_returns_exists_false_when_no_file(client, tmp_path, monkeypatch):
    """로그 파일이 없을 때 — 200 + exists:False (에러 아님)."""
    fake_log = tmp_path / "도수치료예약_updater.log"
    monkeypatch.setattr(api_module, "_get_updater_log_path", lambda: str(fake_log))

    token = _admin_token(client)
    resp = client.get("/api/about/update-log", headers={"x-admin-token": token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["exists"] is False
    assert body["lines"] == []
    assert body["size_bytes"] == 0
    assert body["mtime"] is None
    assert str(fake_log) in body["path"]


def test_update_log_returns_tail_lines(client, tmp_path, monkeypatch):
    """로그 파일이 있을 때 — 마지막 N 줄 + 메타데이터 반환."""
    fake_log = tmp_path / "도수치료예약_updater.log"
    # bat 출력 인코딩이 cp949 일 수도 utf-8 일 수도 있어 양쪽 모두 처리해야 함.
    content = "\n".join(f"line {i}" for i in range(1, 51)) + "\n"
    fake_log.write_text(content, encoding="utf-8")

    monkeypatch.setattr(api_module, "_get_updater_log_path", lambda: str(fake_log))

    token = _admin_token(client)
    resp = client.get(
        "/api/about/update-log",
        headers={"x-admin-token": token},
        params={"tail": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["exists"] is True
    assert body["total_lines"] == 50
    assert len(body["lines"]) == 10
    # 마지막 10줄이 line 41 ~ line 50 인지 확인
    assert body["lines"][0] == "line 41"
    assert body["lines"][-1] == "line 50"
    assert body["size_bytes"] > 0
    assert body["mtime"] is not None


def test_update_log_handles_cp949_encoding(client, tmp_path, monkeypatch):
    """bat 이 cp949 (Windows 한국어 콘솔 기본) 으로 출력해도 깨지지 않게 디코딩."""
    fake_log = tmp_path / "도수치료예약_updater.log"
    fake_log.write_bytes("[1/5] 기존 프로그램 종료 대기...\n완료\n".encode("cp949"))

    monkeypatch.setattr(api_module, "_get_updater_log_path", lambda: str(fake_log))

    token = _admin_token(client)
    resp = client.get("/api/about/update-log", headers={"x-admin-token": token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["exists"] is True
    # 한글이 깨지지 않고 반환되어야 함 (utf-8 우선 → 실패 시 cp949 폴백)
    joined = "\n".join(body["lines"])
    assert "기존 프로그램" in joined or "프로그램" in joined


def test_update_log_tail_param_validation(client, monkeypatch, tmp_path):
    """tail 파라미터 범위 검증 — 1 미만이면 422, 2000 초과면 422."""
    fake_log = tmp_path / "도수치료예약_updater.log"
    monkeypatch.setattr(api_module, "_get_updater_log_path", lambda: str(fake_log))
    token = _admin_token(client)

    resp = client.get(
        "/api/about/update-log",
        headers={"x-admin-token": token},
        params={"tail": 0},
    )
    assert resp.status_code == 422

    resp = client.get(
        "/api/about/update-log",
        headers={"x-admin-token": token},
        params={"tail": 5000},
    )
    assert resp.status_code == 422


def test_get_updater_log_path_points_to_temp_dir():
    """_get_updater_log_path() 가 tempfile.gettempdir() 하위 파일 경로를 반환하는지."""
    import tempfile
    path = Path(api_module._get_updater_log_path())
    assert path.name == "도수치료예약_updater.log"
    # parent 가 tempdir 아래여야 함 (Windows: C:\Users\<user>\AppData\Local\Temp 등)
    assert str(path.parent).lower().startswith(tempfile.gettempdir().lower())
