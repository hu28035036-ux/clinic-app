"""Background peer-to-peer database synchronization service."""

import json
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone

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
    "daily_work_report": models.DailyWorkReport,
    "daily_medical_summary": models.DailyMedicalSummary,
    "record_tab_setting": models.RecordTabSetting,
    "record_entry": models.RecordEntry,
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


def _natural_existing(db: Session, Model, payload: dict):
    """Find rows whose stable business key may differ from the peer primary key."""
    if Model is models.RevenueRecord:
        record_date = str(payload.get("record_date") or "").strip()
        category_id = str(payload.get("category_id") or "").strip()
        if record_date:
            return (
                db.query(models.RevenueRecord)
                .filter(
                    models.RevenueRecord.record_date == record_date,
                    models.RevenueRecord.category_id == category_id,
                )
                .first()
            )
    if Model is models.DailyWorkReport:
        report_date = str(payload.get("report_date") or "").strip()
        if report_date:
            return (
                db.query(models.DailyWorkReport)
                .filter(models.DailyWorkReport.report_date == report_date)
                .first()
            )
    if Model is models.DailyMedicalSummary:
        summary_date = str(payload.get("summary_date") or "").strip()
        if summary_date:
            return (
                db.query(models.DailyMedicalSummary)
                .filter(models.DailyMedicalSummary.summary_date == summary_date)
                .first()
            )
    return None


def apply_op(db: Session, op_dict: dict) -> bool:
    """Apply one operation from a peer. Duplicate op ids are ignored.

    반환: True = op 행이 새로 기록됨 (commit 필요). 데이터 적용 여부와는 무관 —
    모르는 entity 도 op 행은 기록하고 True 를 반환한다.
    """
    if db.get(models.SyncOp, op_dict["id"]):
        return False

    eid = op_dict["entity_id"]
    payload = op_dict.get("payload") or {}
    if isinstance(payload, str):
        payload = json.loads(payload)
    op_ts = _parse_ts(op_dict["ts"])

    Model = ENTITY_MAP.get(op_dict["entity"])
    if not Model:
        # 모르는 entity (이쪽이 구버전) — 데이터 적용은 못 하지만 SyncOp 행은
        # 저장해서 pull 커서(since = 저장된 원격 op 의 max ts)가 전진하게 한다.
        # 저장하지 않으면 커서가 이 op 직전에 영구히 멈춰 매 주기 같은 구간을
        # 재수신하게 됨. 트레이드오프: 이 노드를 나중에 업데이트해도 해당 op 은
        # 재적용되지 않음 — 버전 차이 기간의 신규 entity 데이터는 DB 복사로 복구.
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

    existing = db.get(Model, eid) or _natural_existing(db, Model, payload)
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


def prune_sync_ops(db: Session, retention_days: int | None = None) -> int:
    """보존 기간이 지난 SyncOp 삭제 — 무한 누적 방지.

    SyncOp 은 예약 수정 하나하나마다 쌓이는데 어디서도 지워지지 않아
    수년 운영 시 DB 비대 + push 페이로드 폭증의 원인이 됨.
    ⚠ 보존 기간보다 오래 꺼져 있던 sub 노드는 op 재생으로 따라잡을 수 없음
      → 그런 노드는 메인 PC 의 clinic.db 파일 복사로 부트스트랩해야 한다.
    반환: 삭제된 행 수.
    """
    if retention_days is None:
        try:
            retention_days = int(load_config().get("sync_op_retention_days", 180))
        except Exception:
            retention_days = 180
    if retention_days <= 0:  # 0 이하 = 정리 비활성 (전체 보존)
        return 0
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    deleted = (
        db.query(models.SyncOp)
        .filter(models.SyncOp.ts < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return int(deleted or 0)


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
                    timeout=10,
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

        # ── 증분 push ──
        # peer 에게 "내 노드의 op 을 어디까지 갖고 있는지" 물어보고 그 이후 것만 전송.
        # 상태를 로컬에 저장하지 않아 자기치유적 — peer 가 데이터를 잃으면
        # last-ts 가 과거로 돌아가므로 자동으로 다시 보내게 된다.
        # 조회 실패(구버전 peer 404 등) 시 기존 동작(전체 push)으로 폴백.
        my_ops_q = (
            db.query(models.SyncOp)
            .filter(models.SyncOp.node_id == cfg["node_id"])
        )
        try:
            resp = _http_json(
                f"{peer_url}/api/sync/last-ts?node_id={cfg['node_id']}",
                timeout=10,
                headers=auth_headers,
            )
            peer_last = _parse_ts(resp.get("last_ts") or "1970-01-01T00:00:00")
            my_ops_q = my_ops_q.filter(models.SyncOp.ts > peer_last)
        except Exception:
            pass  # 전체 push 폴백
        my_ops = my_ops_q.order_by(models.SyncOp.ts.asc()).all()

        # 1000개 단위 청크 전송 — 거대 단일 페이로드의 timeout/메모리 부담 방지.
        pushed = 0
        for i in range(0, len(my_ops), 1000):
            chunk = my_ops[i:i + 1000]
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
                    for o in chunk
                ]
            }
            try:
                _http_json(f"{peer_url}/api/sync/push", payload,
                           timeout=30, headers=auth_headers)
            except Exception as e:
                return f"PUSH fail: {e} (pushed={pushed})"
            pushed += len(chunk)
        return f"OK pulled={pulled} pushed={pushed}"
    finally:
        db.close()


_worker_started = False
_stop_flag = threading.Event()
_worker_thread = None
_last_prune_at = 0.0  # SyncOp 정리 마지막 실행 시각 (epoch)


def run_daily_maintenance():
    """일일 DB 유지보수 — SyncOp 보존 기간 정리 + audit_log 5년 보존 정리.

    각 작업은 독립 세션/예외 격리 — 한쪽이 실패해도 다른 쪽은 진행.
    """
    db = SessionLocal()
    try:
        prune_sync_ops(db)
    except Exception:
        db.rollback()
    finally:
        db.close()

    # audit_log 5년 보존 정책 (modules/audit/retention.py, 사용자 §4-A 결정).
    # 헬퍼만 있고 호출처가 없어 무한 누적되던 것을 여기서 일일 주기로 실행.
    db = SessionLocal()
    try:
        from ..modules.audit.retention import delete_old_audit_logs
        delete_old_audit_logs(db)
    except Exception:
        db.rollback()
    finally:
        db.close()


def _prune_if_due():
    """하루 1회 일일 유지보수 — sync worker 루프에서 호출.

    peer 가 없는 환경(메인 PC 단독)에서도 record_op/audit 은 계속 쌓이므로
    peer 유무와 무관하게 worker 루프에서 주기 실행한다.
    """
    global _last_prune_at
    now = time.time()
    if now - _last_prune_at < 24 * 3600:
        return
    _last_prune_at = now
    run_daily_maintenance()


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
                _prune_if_due()
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
