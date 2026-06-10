"""시한폭탄형 위험 수정 검증 (v1.3.23).

대상:
  1. SyncOp 보존 기간 정리 (prune_sync_ops)
  2. 증분 push (peer last-ts 기반 + 실패 시 전체 push 폴백)
  3. 모르는 entity op 수신 시 SyncOp 행 저장 (pull/push 커서 영구 멈춤 방지)
  4. make_backup 이 SQLite backup API 로 정합성 있는 백업 생성
  5. config.json 원자적 저장 + 손상 시 .broken_* 보존 후 재생성
  6. WAL + busy_timeout PRAGMA 적용
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_config_path, load_config, save_config
from app.database import Base, SessionLocal, engine
from app.models import models
from app.services import backup as backup_mod
from app.services import sync as sync_mod


def _session_factory(db_path: Path):
    eng = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng, autoflush=False, autocommit=False)


def _own_op(node_id: str, op_id: str, ts: datetime) -> models.SyncOp:
    return models.SyncOp(
        id=f"{node_id}:{op_id}",
        node_id=node_id,
        entity="patient",
        entity_id=op_id,
        op="upsert",
        payload=json.dumps({"id": op_id}),
        ts=ts,
    )


# ──────────────── 6. WAL + busy_timeout ────────────────


def test_engine_uses_wal_and_busy_timeout():
    with engine.connect() as conn:
        raw = conn.connection.driver_connection
        cur = raw.cursor()
        assert cur.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert int(cur.execute("PRAGMA busy_timeout").fetchone()[0]) >= 5000
        cur.close()


# ──────────────── 4. 안전한 백업 ────────────────


def test_make_backup_produces_valid_sqlite_db():
    result = backup_mod.make_backup()
    assert result["ok"], result
    dest = backup_mod.get_backup_dir() / result["name"]
    try:
        conn = sqlite3.connect(str(dest))
        try:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            # 백업본에 실제 테이블이 들어 있는지 (빈 파일/부분 복사 방지)
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            assert "patients" in tables
        finally:
            conn.close()
    finally:
        dest.unlink(missing_ok=True)


def test_sqlite_safe_copy_roundtrip(tmp_path):
    src = tmp_path / "src.db"
    conn = sqlite3.connect(str(src))
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.execute("INSERT INTO t VALUES ('x')")
    conn.commit()
    conn.close()

    dst = tmp_path / "dst.db"
    backup_mod.sqlite_safe_copy(src, dst)
    out = sqlite3.connect(str(dst))
    try:
        assert out.execute("SELECT v FROM t").fetchone()[0] == "x"
    finally:
        out.close()


# ──────────────── 5. config 원자적 저장 + 손상 복구 ────────────────


def test_save_config_leaves_no_tmp_file():
    cfg = load_config()
    save_config(cfg)
    p = get_config_path()
    assert p.exists()
    assert not p.with_name(p.name + ".tmp").exists()
    assert load_config()["node_id"] == cfg["node_id"]


def test_load_config_recovers_from_corrupt_file():
    p = get_config_path()
    original = p.read_text(encoding="utf-8")
    try:
        p.write_text('{"mode": "main", "node_id": "abc', encoding="utf-8")  # 잘린 JSON
        cfg = load_config()
        # 기본값으로 재생성 + node_id/sync_secret 자동 채움
        assert cfg.get("node_id")
        assert cfg.get("sync_secret")
        broken = list(p.parent.glob("config.json.broken_*"))
        assert broken, "손상 원본이 .broken_* 으로 보존되어야 함"
    finally:
        p.write_text(original, encoding="utf-8")
        for b in p.parent.glob("config.json.broken_*"):
            b.unlink(missing_ok=True)


# ──────────────── 1. SyncOp 보존 기간 정리 ────────────────


def test_prune_sync_ops_deletes_only_expired():
    now = datetime.utcnow()
    old_id = "prune-test:old"
    fresh_id = "prune-test:fresh"
    db = SessionLocal()
    try:
        db.add(_own_op("prune-test", "old", now - timedelta(days=200)))
        db.add(_own_op("prune-test", "fresh", now - timedelta(days=1)))
        db.commit()

        deleted = sync_mod.prune_sync_ops(db, retention_days=180)

        assert deleted >= 1
        assert db.get(models.SyncOp, old_id) is None
        assert db.get(models.SyncOp, fresh_id) is not None
    finally:
        db.query(models.SyncOp).filter(
            models.SyncOp.node_id == "prune-test"
        ).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_prune_sync_ops_disabled_with_zero_retention():
    db = SessionLocal()
    try:
        assert sync_mod.prune_sync_ops(db, retention_days=0) == 0
    finally:
        db.close()


# ──────────────── 3. 모르는 entity → SyncOp 행 저장 (커서 전진) ────────────────


def test_apply_op_unknown_entity_stores_op_row(tmp_path):
    Session = _session_factory(tmp_path / "local.db")
    op = {
        "id": "future-node:unknown-1",
        "node_id": "future-node",
        "entity": "entity_from_future_version",
        "entity_id": "x1",
        "op": "upsert",
        "payload": {"id": "x1"},
        "ts": datetime(2026, 6, 10, 9, 0, 0).isoformat(),
    }
    db = Session()
    try:
        assert sync_mod.apply_op(db, op) is True  # op 행 기록됨
        db.commit()
        assert db.get(models.SyncOp, "future-node:unknown-1") is not None
        # 같은 op 재수신 → 중복으로 무시 (커서가 전진했음을 의미)
        assert sync_mod.apply_op(db, op) is False
    finally:
        db.close()


def test_sync_push_endpoint_stores_unknown_entity_op(client):
    token = load_config()["sync_secret"]
    now = datetime(2026, 6, 10, 9, 30, 0)
    payload = {
        "ops": [
            {
                "id": "future-node:known-1",
                "node_id": "future-node",
                "entity": "patient",
                "entity_id": "sync-unknown-known",
                "op": "upsert",
                "payload": {
                    "id": "sync-unknown-known", "name": "known", "birth_date": "",
                    "phone": "", "chart_no": "sync-unknown-known", "gender": "",
                    "memo": "", "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                "ts": now.isoformat(),
            },
            {
                "id": "future-node:unknown-2",
                "node_id": "future-node",
                "entity": "entity_from_future_version",
                "entity_id": "x2",
                "op": "upsert",
                "payload": {"id": "x2"},
                "ts": now.isoformat(),
            },
        ]
    }

    resp = client.post("/api/sync/push", json=payload, headers={"X-Sync-Token": token})

    assert resp.status_code == 200
    body = resp.json()
    assert body["applied"] == 1
    assert body["skipped_unknown"] == 1
    assert body["failed"] == 0

    db = SessionLocal()
    try:
        # 모르는 entity 도 SyncOp 행은 저장 → 발신측 last-ts 커서가 전진
        assert db.get(models.SyncOp, "future-node:unknown-2") is not None
        assert db.get(models.Patient, "sync-unknown-known") is not None
    finally:
        db.close()


# ──────────────── 2. 증분 push ────────────────


def _run_push_with_fake_peer(tmp_path, monkeypatch, *, last_ts_response):
    """sub 노드에 own op 2개(old/new)를 만들고 push — 전송된 op id 목록 반환.

    last_ts_response: dict 면 last-ts 엔드포인트 응답, Exception 이면 조회 실패 시뮬레이션.
    """
    Session = _session_factory(tmp_path / "sub.db")
    old_ts = datetime(2026, 6, 1, 9, 0, 0)
    new_ts = datetime(2026, 6, 9, 9, 0, 0)
    db = Session()
    try:
        db.add(_own_op("sub-node", "old", old_ts))
        db.add(_own_op("sub-node", "new", new_ts))
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(sync_mod, "SessionLocal", Session)
    monkeypatch.setattr(sync_mod, "load_config",
                        lambda: {"node_id": "sub-node", "sync_secret": "s"})

    pushed_ids: list[str] = []

    def fake_http_json(url: str, payload=None, timeout=4, headers=None):
        parsed = urlparse(url)
        if parsed.path.endswith("/api/sync/pull"):
            return {"ops": []}
        if parsed.path.endswith("/api/sync/last-ts"):
            assert parse_qs(parsed.query)["node_id"] == ["sub-node"]
            if isinstance(last_ts_response, Exception):
                raise last_ts_response
            return last_ts_response
        if parsed.path.endswith("/api/sync/push"):
            pushed_ids.extend(op["id"] for op in payload["ops"])
            return {"applied": len(payload["ops"]), "failed": 0, "failures": []}
        raise AssertionError(f"unexpected sync url: {url}")

    monkeypatch.setattr(sync_mod, "_http_json", fake_http_json)
    result = sync_mod.sync_with_peer("http://main.local")
    return pushed_ids, result


def test_incremental_push_sends_only_ops_after_peer_last_ts(tmp_path, monkeypatch):
    pushed, result = _run_push_with_fake_peer(
        tmp_path, monkeypatch,
        last_ts_response={"node_id": "sub-node",
                          "last_ts": datetime(2026, 6, 5, 0, 0, 0).isoformat()},
    )
    assert pushed == ["sub-node:new"]
    assert result == "OK pulled=0 pushed=1"


def test_incremental_push_falls_back_to_full_push_on_last_ts_failure(tmp_path, monkeypatch):
    pushed, result = _run_push_with_fake_peer(
        tmp_path, monkeypatch,
        last_ts_response=RuntimeError("404 not found"),
    )
    assert pushed == ["sub-node:old", "sub-node:new"]
    assert result == "OK pulled=0 pushed=2"


def test_sync_last_ts_endpoint(client):
    token = load_config()["sync_secret"]
    ts = datetime(2026, 6, 10, 10, 0, 0)
    db = SessionLocal()
    try:
        db.add(_own_op("lastts-node", "a", ts))
        db.commit()

        resp = client.get("/api/sync/last-ts?node_id=lastts-node",
                          headers={"X-Sync-Token": token})
        assert resp.status_code == 200
        assert sync_mod._parse_ts(resp.json()["last_ts"]) == ts

        # 모르는 노드 → epoch 반환 (전체 push 유도)
        resp2 = client.get("/api/sync/last-ts?node_id=never-seen-node",
                           headers={"X-Sync-Token": token})
        assert resp2.json()["last_ts"] == "1970-01-01T00:00:00"
    finally:
        db.query(models.SyncOp).filter(
            models.SyncOp.node_id == "lastts-node"
        ).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_sync_last_ts_requires_auth(client):
    resp = client.get("/api/sync/last-ts?node_id=x")
    assert resp.status_code == 401
