"""modules.resources.router — /api/resources CRUD (post-19-P / 20-3-5 / F-3).

# SAFETY: write 는 require_admin. audit 기록 (PII 부재 — name 만).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.modules.audit.service import cap_detail
from app.modules.resources.schemas import ResourceIn
from app.modules.resources.service import serialize_resource, serialize_resources
from app.routers.api import require_admin

router = APIRouter(prefix="/api", tags=["resources"])


@router.get("/resources")
def list_resources(
    active_only: bool = True,
    type: str | None = None,
    db: Session = Depends(get_db),
):
    """자원 목록.

    type=None 이면 모든 타입. 'room' / 'equipment' 필터 가능.
    """
    q = db.query(models.Resource)
    if active_only:
        q = q.filter(models.Resource.active == True)  # noqa: E712
    if type:
        q = q.filter(models.Resource.type == type)
    rows = q.order_by(
        models.Resource.active.desc(),
        models.Resource.type.asc(),
        models.Resource.sort_order.asc(),
        models.Resource.created_at.asc(),
    ).all()
    return serialize_resources(rows)


@router.post("/resources")
def create_resource(
    p: ResourceIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    if not p.name.strip():
        raise HTTPException(400, "자원 이름은 필수입니다.")
    res = models.Resource(
        type=p.type,
        name=p.name.strip(),
        capacity=p.capacity,
        active=p.active,
        sort_order=p.sort_order,
    )
    db.add(res)
    db.flush()
    from app.routers.api import _log, audit
    _log(db, "resource", res.id, "upsert", res)
    audit(db, "resource.create", res.id, cap_detail(f"name={res.name}"))
    db.commit()
    db.refresh(res)
    return serialize_resource(res)


@router.put("/resources/{rid}")
def update_resource(
    rid: str,
    p: ResourceIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    res = db.get(models.Resource, rid)
    if not res:
        raise HTTPException(404, "자원을 찾을 수 없습니다.")
    if not p.name.strip():
        raise HTTPException(400, "자원 이름은 필수입니다.")
    res.type = p.type
    res.name = p.name.strip()
    res.capacity = p.capacity
    res.active = p.active
    res.sort_order = p.sort_order
    db.flush()
    from app.routers.api import _log, audit
    _log(db, "resource", res.id, "upsert", res)
    audit(db, "resource.update", res.id, cap_detail(f"name={res.name}"))
    db.commit()
    db.refresh(res)
    return serialize_resource(res)


@router.delete("/resources/{rid}")
def delete_resource(
    rid: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    res = db.get(models.Resource, rid)
    if not res:
        raise HTTPException(404, "자원을 찾을 수 없습니다.")
    name = res.name
    db.delete(res)
    from app.routers.api import _log, audit
    _log(db, "resource", rid, "delete", None)
    audit(db, "resource.delete", rid, cap_detail(f"name={name}"))
    db.commit()
    return {"ok": True}
