from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import load_config
from app.database import Base, SessionLocal
from app.models import models
from app.services import sync as sync_mod


def _session_factory(db_path: Path):
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _patient_payload(patient_id: str, name: str, ts: datetime) -> dict:
    return {
        "id": patient_id,
        "name": name,
        "birth_date": "",
        "phone": "",
        "chart_no": patient_id,
        "gender": "",
        "memo": "",
        "created_at": ts.isoformat(),
        "updated_at": ts.isoformat(),
    }


def _patient_row(patient_id: str, name: str, ts: datetime) -> dict:
    row = _patient_payload(patient_id, name, ts)
    row["created_at"] = ts
    row["updated_at"] = ts
    return row


def _add_patient_with_op(Session, *, node_id: str, patient_id: str, name: str, ts: datetime):
    db = Session()
    try:
        payload = _patient_payload(patient_id, name, ts)
        db.add(models.Patient(**_patient_row(patient_id, name, ts)))
        db.add(
            models.SyncOp(
                id=f"{node_id}:{patient_id}",
                node_id=node_id,
                entity="patient",
                entity_id=patient_id,
                op="upsert",
                payload=json.dumps(payload, ensure_ascii=False),
                ts=ts,
            )
        )
        db.commit()
    finally:
        db.close()


def _op_dict(op: models.SyncOp) -> dict:
    return {
        "id": op.id,
        "node_id": op.node_id,
        "entity": op.entity,
        "entity_id": op.entity_id,
        "op": op.op,
        "payload": op.payload,
        "ts": op.ts.isoformat(),
    }


def test_sync_with_peer_pulls_remote_ops_even_when_local_has_newer_ops(tmp_path, monkeypatch):
    MainSession = _session_factory(tmp_path / "main.db")
    SubSession = _session_factory(tmp_path / "sub.db")

    main_ts = datetime(2026, 6, 8, 9, 0, 0)
    sub_ts = datetime(2026, 6, 8, 9, 5, 0)
    _add_patient_with_op(MainSession, node_id="main-node", patient_id="patient-main", name="main", ts=main_ts)
    _add_patient_with_op(SubSession, node_id="sub-node", patient_id="patient-sub", name="sub", ts=sub_ts)

    monkeypatch.setattr(sync_mod, "SessionLocal", SubSession)
    monkeypatch.setattr(sync_mod, "load_config", lambda: {"node_id": "sub-node", "sync_secret": "shared-secret"})

    def fake_http_json(url: str, payload=None, timeout=4, headers=None):
        parsed = urlparse(url)
        if parsed.path.endswith("/api/sync/pull"):
            params = parse_qs(parsed.query)
            since = sync_mod._parse_ts(params["since"][0])
            exclude_node = params.get("exclude_node", [""])[0]
            db = MainSession()
            try:
                q = db.query(models.SyncOp).filter(models.SyncOp.ts > since)
                if exclude_node:
                    q = q.filter(models.SyncOp.node_id != exclude_node)
                ops = q.order_by(models.SyncOp.ts.asc()).limit(1000).all()
                return {"ops": [_op_dict(op) for op in ops]}
            finally:
                db.close()

        if parsed.path.endswith("/api/sync/push"):
            db = MainSession()
            try:
                applied = 0
                for op in payload["ops"]:
                    if sync_mod.apply_op(db, op):
                        applied += 1
                db.commit()
                return {"applied": applied, "failed": 0, "failures": []}
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        raise AssertionError(f"unexpected sync url: {url}")

    monkeypatch.setattr(sync_mod, "_http_json", fake_http_json)

    assert sync_mod.sync_with_peer("http://main.local") == "OK pulled=1 pushed=1"

    sub_db = SubSession()
    main_db = MainSession()
    try:
        assert sub_db.get(models.Patient, "patient-main").name == "main"
        assert main_db.get(models.Patient, "patient-sub").name == "sub"
    finally:
        sub_db.close()
        main_db.close()


def test_apply_op_does_not_delete_newer_local_row(tmp_path):
    Session = _session_factory(tmp_path / "local.db")
    local_ts = datetime(2026, 6, 8, 10, 0, 0)
    delete_ts = datetime(2026, 6, 8, 9, 50, 0)

    db = Session()
    try:
        db.add(models.Patient(**_patient_row("newer-local", "kept", local_ts)))
        db.commit()

        assert sync_mod.apply_op(
            db,
            {
                "id": "remote-node:delete-old",
                "node_id": "remote-node",
                "entity": "patient",
                "entity_id": "newer-local",
                "op": "delete",
                "payload": {},
                "ts": delete_ts.isoformat(),
            },
        )
        db.commit()

        assert db.get(models.Patient, "newer-local").name == "kept"
        assert db.get(models.SyncOp, "remote-node:delete-old") is not None
    finally:
        db.close()


def test_apply_op_merges_revenue_rows_by_date_when_peer_ids_differ(tmp_path):
    Session = _session_factory(tmp_path / "revenue-sync.db")
    local_ts = datetime(2026, 6, 8, 9, 0, 0)
    remote_ts = datetime(2026, 6, 8, 9, 10, 0)

    db = Session()
    try:
        db.add(models.RevenueRecord(
            id="local-revenue-id",
            record_date="2099-12-01",
            category_id="",
            total_medical_fee=1000,
            updated_at=local_ts,
        ))
        db.add(models.DailyWorkReport(
            id="local-report-id",
            report_date="2099-12-01",
            selected_treatment_codes_json='["old"]',
            custom_fields_json='[{"id":"a","sort_order":0}]',
            updated_at=local_ts,
        ))
        db.commit()

        assert sync_mod.apply_op(db, {
            "id": "remote-node:revenue-upsert",
            "node_id": "remote-node",
            "entity": "revenue_record",
            "entity_id": "remote-revenue-id",
            "op": "upsert",
            "payload": {
                "id": "remote-revenue-id",
                "record_date": "2099-12-01",
                "category_id": "",
                "total_medical_fee": 9000,
                "nhis_burden_total": 3000,
                "cash_amount": 6000,
                "cash_counts_json": "{}",
                "updated_at": remote_ts.isoformat(),
            },
            "ts": remote_ts.isoformat(),
        })
        assert sync_mod.apply_op(db, {
            "id": "remote-node:report-upsert",
            "node_id": "remote-node",
            "entity": "daily_work_report",
            "entity_id": "remote-report-id",
            "op": "upsert",
            "payload": {
                "id": "remote-report-id",
                "report_date": "2099-12-01",
                "selected_treatment_codes_json": '["new"]',
                "custom_fields_json": '[{"id":"b","sort_order":0},{"id":"a","sort_order":1}]',
                "updated_at": remote_ts.isoformat(),
            },
            "ts": remote_ts.isoformat(),
        })
        db.commit()

        rows = db.query(models.RevenueRecord).filter(
            models.RevenueRecord.record_date == "2099-12-01",
            models.RevenueRecord.category_id == "",
        ).all()
        assert len(rows) == 1
        assert rows[0].id == "local-revenue-id"
        assert rows[0].total_medical_fee == 9000
        assert rows[0].cash_amount == 6000

        report = db.query(models.DailyWorkReport).filter(
            models.DailyWorkReport.report_date == "2099-12-01",
        ).one()
        assert report.id == "local-report-id"
        assert report.selected_treatment_codes_json == '["new"]'
        assert json.loads(report.custom_fields_json)[0]["id"] == "b"
    finally:
        db.close()


def test_apply_op_deletes_revenue_row_by_natural_key_payload(tmp_path):
    Session = _session_factory(tmp_path / "revenue-delete-sync.db")
    local_ts = datetime(2026, 6, 8, 9, 0, 0)
    remote_ts = datetime(2026, 6, 8, 9, 10, 0)

    db = Session()
    try:
        db.add(models.RevenueRecord(
            id="local-revenue-delete-id",
            record_date="2099-12-02",
            category_id="",
            total_medical_fee=1000,
            updated_at=local_ts,
        ))
        db.commit()

        assert sync_mod.apply_op(db, {
            "id": "remote-node:revenue-delete",
            "node_id": "remote-node",
            "entity": "revenue_record",
            "entity_id": "remote-revenue-delete-id",
            "op": "delete",
            "payload": {
                "id": "remote-revenue-delete-id",
                "record_date": "2099-12-02",
                "category_id": "",
                "updated_at": remote_ts.isoformat(),
            },
            "ts": remote_ts.isoformat(),
        })
        db.commit()

        assert db.query(models.RevenueRecord).filter(
            models.RevenueRecord.record_date == "2099-12-02",
            models.RevenueRecord.category_id == "",
        ).count() == 0
    finally:
        db.close()


def test_sync_push_commits_successful_ops_even_if_later_op_fails(client):
    token = load_config()["sync_secret"]
    now = datetime(2026, 6, 8, 11, 0, 0)
    payload = {
        "ops": [
            {
                "id": "remote-node:partial-a",
                "node_id": "remote-node",
                "entity": "patient",
                "entity_id": "sync-partial-a",
                "op": "upsert",
                "payload": _patient_payload("sync-partial-a", "partial a", now),
                "ts": now.isoformat(),
            },
            {
                "id": "remote-node:partial-bad",
                "node_id": "remote-node",
                "entity": "patient",
                "entity_id": "sync-partial-bad",
                "op": "upsert",
                "payload": {"id": "sync-partial-bad", "updated_at": now.isoformat()},
                "ts": now.isoformat(),
            },
            {
                "id": "remote-node:partial-b",
                "node_id": "remote-node",
                "entity": "patient",
                "entity_id": "sync-partial-b",
                "op": "upsert",
                "payload": _patient_payload("sync-partial-b", "partial b", now),
                "ts": now.isoformat(),
            },
        ]
    }

    resp = client.post("/api/sync/push", json=payload, headers={"X-Sync-Token": token})

    assert resp.status_code == 200
    body = resp.json()
    assert body["applied"] == 2
    assert body["failed"] == 1
    assert body["failures"][0]["op_id"] == "remote-node:partial-bad"

    db = SessionLocal()
    try:
        assert db.get(models.Patient, "sync-partial-a") is not None
        assert db.get(models.Patient, "sync-partial-b") is not None
        assert db.get(models.Patient, "sync-partial-bad") is None
    finally:
        db.close()


def test_sync_entity_map_covers_all_logged_entities():
    root = Path(__file__).resolve().parents[1]
    files = [root / "app" / "routers" / "api.py", *sorted((root / "app" / "modules").glob("**/*.py"))]
    logged_entities = set()
    for file in files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        logged_entities.update(re.findall(r"_log\s*\(\s*db\s*,\s*[\"']([^\"']+)[\"']", text))

    missing = sorted(entity for entity in logged_entities if entity not in sync_mod.ENTITY_MAP)

    assert missing == []
