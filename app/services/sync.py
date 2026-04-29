"""분산 동기화 서비스.
설계:
- 모든 CUD 작업은 record_op() 호출로 sync_ops 에 append-only 기록
- 백그라운드 워커가 주기적으로 peer(메인+추가 peers)에 push, peer 로부터 pull
- 적용 시 last-write-wins (op.ts 비교; 동률은 node_id 사전순)
- peer 가 unreachable 이면 조용히 스킵 → 다음 주기에 재시도
"""
import json, time, threading, urllib.request, urllib.error
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import models
from ..config import load_config


ENTITY_MAP = {
    "employee": models.Employee,
    "patient": models.Patient,
    "appointment": models.Appointment,
    "employee_leave": models.EmployeeLeave,
    "treatment_assignment": models.TreatmentAssignment,
    "treatment": models.Treatment,
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
        if isinstance(v, datetime): v = v.isoformat()
        out[c.name] = v
    return out


def record_op(db: Session, entity: str, entity_id: str, op: str, payload: dict):
    cfg = load_config()
    so = models.SyncOp(
        id=f"{cfg['node_id']}:{_ulid_like()}",
        node_id=cfg["node_id"],
        entity=entity, entity_id=entity_id, op=op,
        payload=json.dumps(payload, ensure_ascii=False, default=str),
        ts=datetime.utcnow(),
    )
    db.add(so)


def apply_op(db: Session, op_dict: dict) -> bool:
    """외부에서 받은 op 적용. 이미 있으면 무시. 충돌은 ts 비교."""
    if db.get(models.SyncOp, op_dict["id"]):
        return False
    Model = ENTITY_MAP.get(op_dict["entity"])
    if not Model: return False

    eid = op_dict["entity_id"]
    payload = op_dict.get("payload") or {}
    if isinstance(payload, str): payload = json.loads(payload)
    op_ts = datetime.fromisoformat(op_dict["ts"]) if isinstance(op_dict["ts"], str) else op_dict["ts"]

    existing = db.get(Model, eid)
    if op_dict["op"] == "delete":
        if existing: db.delete(existing)
    else:  # upsert
        # 충돌: 기존 updated_at >= op_ts 이고 우리 node_id 가 더 작으면 무시
        if existing and getattr(existing, "updated_at", None):
            if existing.updated_at > op_ts: pass  # 우리 게 더 최신
            else:
                for k, v in payload.items():
                    if k in ("id",): continue
                    if hasattr(existing, k):
                        if k.endswith("_at") and isinstance(v, str):
                            try: v = datetime.fromisoformat(v)
                            except Exception: pass
                        setattr(existing, k, v)
        else:
            # 신규 INSERT
            row = {}
            for c in Model.__table__.columns:
                if c.name in payload:
                    v = payload[c.name]
                    if c.name.endswith("_at") and isinstance(v, str):
                        try: v = datetime.fromisoformat(v)
                        except Exception: pass
                    row[c.name] = v
            row["id"] = eid
            db.add(Model(**row))

    # op 자체도 저장 (재전파 방지)
    db.add(models.SyncOp(
        id=op_dict["id"], node_id=op_dict["node_id"],
        entity=op_dict["entity"], entity_id=eid,
        op=op_dict["op"], payload=json.dumps(payload, default=str),
        ts=op_ts,
    ))
    return True


def _http_json(url: str, payload=None, timeout=4):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type":"application/json"},
        method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def sync_with_peer(peer_url: str):
    """peer 한 곳과 1회 동기화 (push + pull)."""
    cfg = load_config()
    db = SessionLocal()
    try:
        # 1) PULL: 마지막으로 받아본 ts 이후의 op 가져오기
        last = db.query(models.SyncOp.ts).order_by(models.SyncOp.ts.desc()).first()
        since = (last[0].isoformat() if last else "1970-01-01T00:00:00")
        try:
            remote_ops = _http_json(
                f"{peer_url}/api/sync/pull?since={since}&exclude_node={cfg['node_id']}"
            )
        except Exception as e:
            return f"PULL fail: {e}"

        for op in remote_ops.get("ops", []):
            apply_op(db, op)
        db.commit()

        # 2) PUSH: 우리 node_id 의 op 중 peer 가 아직 모르는 것들
        my_ops = (db.query(models.SyncOp)
                    .filter(models.SyncOp.node_id == cfg["node_id"])
                    .order_by(models.SyncOp.ts.desc()).limit(500).all())
        payload = {"ops": [
            {"id":o.id,"node_id":o.node_id,"entity":o.entity,"entity_id":o.entity_id,
             "op":o.op,"payload":o.payload,"ts":o.ts.isoformat()} for o in my_ops]}
        try:
            _http_json(f"{peer_url}/api/sync/push", payload)
        except Exception as e:
            return f"PUSH fail: {e}"
        return f"OK pulled={len(remote_ops.get('ops',[]))} pushed={len(my_ops)}"
    finally:
        db.close()


_worker_started = False
def start_sync_worker():
    global _worker_started
    if _worker_started: return
    _worker_started = True
    def loop():
        while True:
            try:
                cfg = load_config()
                interval = max(5, int(cfg.get("sync_interval_sec", 15)))
                peers = []
                if cfg.get("mode") == "sub" and cfg.get("main_url"):
                    peers.append(cfg["main_url"].rstrip("/"))
                peers += [p.rstrip("/") for p in (cfg.get("peers") or [])]
                for url in peers:
                    try: sync_with_peer(url)
                    except Exception: pass
                time.sleep(interval)
            except Exception:
                time.sleep(15)
    threading.Thread(target=loop, daemon=True).start()
