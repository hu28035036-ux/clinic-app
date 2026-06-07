"""Background peer-to-peer database synchronization service."""

import json
import threading
import time
import urllib.request
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..config import load_config
from ..database import SessionLocal
from ..models import models


ENTITY_MAP = {
    "doctor": models.Doctor,
    "employee": models.Employee,
    "employee_category": models.EmployeeCategory,
    "employee_treatment": models.EmployeeTreatment,
    "resource": models.Resource,
    "patient": models.Patient,
    "appointment": models.Appointment,
    "employee_leave": models.EmployeeLeave,
    "treatment_assignment": models.TreatmentAssignment,
    "treatment": models.Treatment,
    "settlement_record": models.SettlementRecord,
    "revenue_record": models.RevenueRecord,
    "inventory_category_state": models.InventoryCategoryState,
    "inventory_item": models.InventoryItem,
    "inventory_field": models.InventoryField,
    "inventory_value": models.InventoryValue,
    "patient_treatment_count": models.PatientTreatmentCount,
    "system_setting": models.SystemSetting,
    "sms_template": models.SmsTemplate,
}


def _ulid_like() -> str:
    return f"{int(time.time()*1000):013x}{int.from_bytes(__import__('os').urandom(6),'big'):012x}"


def _serialize(obj) -> dict:
    out = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        out[c.name] = v
    return out


def record_op(db: Session, entity: str, entity_id: str, op: str, payload: dict):
    cfg = load_config()
    so = models.SyncOp(
        id=f"{cfg['node_id']}:{_ulid_like()}",
        node_id=cfg["node_id"],
        entity=entity,
        entity_id=entity_id,
        op=op,
        payload=json.dumps(payload, ensure_ascii=False, default=str),
        ts=datetime.utcnow(),
    )
    db.add(so)


def _parse_ts(value) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    text = str(value or "")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _coerce_payload_value(key: str, value):
    if key.endswith("_at") and isinstance(value, str):
        try:
            return _parse_ts(value)
        except Exception:
            return value
    return value


def _existing_is_newer(existing, op_ts: datetime) -> bool:
    current_ts = getattr(existing, "updated_at", None)
    if isinstance(current_ts, str):
        try:
            current_ts = _parse_ts(current_ts)
        except Exception:
            return False
    return bool(current_ts and current_ts > op_ts)


def apply_op(db: Session, op_dict: dict) -> bool:
    """Apply one operation from a peer. Duplicate op ids are ignored."""
    if db.get(models.SyncOp, op_dict["id"]):
        return False

    Model = ENTITY_MAP.get(op_dict["entity"])
    if not Model:
        return False

    eid = op_dict["entity_id"]
    payload = op_dict.get("payload") or {}
    if isinstance(payload, str):
        payload = json.loads(payload)
    op_ts = _parse_ts(op_dict["ts"])

    existing = db.get(Model, eid)
    if op_dict["op"] == "delete":
        if existing and not _existing_is_newer(existing, op_ts):
            db.delete(existing)
    else:
        if existing:
            if not _existing_is_newer(existing, op_ts):
                for k, v in payload.items():
                    if k in ("id",):
                        continue
                    if hasattr(existing, k):
                        setattr(existing, k, _coerce_payload_value(k, v))
        else:
            row = {}
            for c in Model.__table__.columns:
                if c.name in payload:
                    row[c.name] = _coerce_payload_value(c.name, payload[c.name])
            row["id"] = eid
            db.add(Model(**row))

    db.add(
        models.SyncOp(
            id=op_dict["id"],
            node_id=op_dict["node_id"],
            entity=op_dict["entity"],
            entity_id=eid,
            op=op_dict["op"],
            payload=json.dumps(payload, ensure_ascii=False, default=str),
            ts=op_ts,
        )
    )
    return True


def _http_json(url: str, payload=None, timeout=4, headers=None):
    """Call a peer HTTP endpoint and decode JSON."""
    data = json.dumps(payload).encode() if payload is not None else None
    base_headers = {"Content-Type": "application/json"}
    if headers:
        base_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=data,
        headers=base_headers,
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def sync_with_peer(peer_url: str):
    """Run one synchronization cycle against a peer."""
    cfg = load_config()
    auth_headers = {}
    secret = (cfg.get("sync_secret") or "").strip()
    if secret:
        auth_headers["X-Sync-Token"] = secret

    db = SessionLocal()
    try:
        last_remote = (
            db.query(models.SyncOp.ts)
            .filter(models.SyncOp.node_id != cfg["node_id"])
            .order_by(models.SyncOp.ts.desc())
            .first()
        )
        since = last_remote[0].isoformat() if last_remote else "1970-01-01T00:00:00"
        pulled = 0

        while True:
            try:
                remote_ops = _http_json(
                    f"{peer_url}/api/sync/pull?since={since}&exclude_node={cfg['node_id']}",
                    headers=auth_headers,
                )
            except Exception as e:
                db.rollback()
                return f"PULL fail: {e}"

            ops = remote_ops.get("ops", [])
            if not ops:
                break

            try:
                for op in ops:
                    apply_op(db, op)
                db.commit()
            except Exception as e:
                db.rollback()
                return f"PULL fail: {e}"

            pulled += len(ops)
            next_since = max(_parse_ts(op["ts"]) for op in ops).isoformat()
            if next_since == since or len(ops) < 1000:
                break
            since = next_since

        my_ops = (
            db.query(models.SyncOp)
            .filter(models.SyncOp.node_id == cfg["node_id"])
            .order_by(models.SyncOp.ts.asc())
            .all()
        )
        payload = {
            "ops": [
                {
                    "id": o.id,
                    "node_id": o.node_id,
                    "entity": o.entity,
                    "entity_id": o.entity_id,
                    "op": o.op,
                    "payload": o.payload,
                    "ts": o.ts.isoformat(),
                }
                for o in my_ops
            ]
        }
        try:
            _http_json(f"{peer_url}/api/sync/push", payload, headers=auth_headers)
        except Exception as e:
            return f"PUSH fail: {e}"
        return f"OK pulled={pulled} pushed={len(my_ops)}"
    finally:
        db.close()


_worker_started = False
_stop_flag = threading.Event()
_worker_thread = None


def start_sync_worker():
    """Start the background sync worker once."""
    global _worker_started, _worker_thread
    if _worker_started:
        return
    _worker_started = True
    _stop_flag.clear()

    def loop():
        while not _stop_flag.is_set():
            try:
                cfg = load_config()
                interval = max(5, int(cfg.get("sync_interval_sec", 15)))
                peers = []
                if cfg.get("mode") == "sub" and cfg.get("main_url"):
                    peers.append(cfg["main_url"].rstrip("/"))
                peers += [p.rstrip("/") for p in (cfg.get("peers") or [])]
                for url in peers:
                    if _stop_flag.is_set():
                        break
                    try:
                        sync_with_peer(url)
                    except Exception:
                        pass
                if _stop_flag.wait(interval):
                    break
            except Exception:
                if _stop_flag.wait(15):
                    break

    _worker_thread = threading.Thread(target=loop, daemon=True, name="sync-worker")
    _worker_thread.start()


def stop_sync_worker(timeout: float = 2.0) -> bool:
    """Stop the background sync worker gracefully."""
    global _worker_started
    _stop_flag.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=timeout)
    _worker_started = False
    return not (_worker_thread and _worker_thread.is_alive())
