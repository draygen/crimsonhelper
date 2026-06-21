from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import NPC

router = APIRouter(prefix="/api/npcs", tags=["npcs"])


class NPCOut(BaseModel):
    id: int
    name: str
    zone: Optional[str]
    dialogue: Optional[str]
    screenshot_id: Optional[int]
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


@router.get("/count")
def count_npcs(db: Session = Depends(get_db)):
    return {"count": db.query(NPC).count()}


@router.get("", response_model=list[NPCOut])
def list_npcs(
    q: Optional[str] = Query(None),
    zone: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(NPC)
    if q:
        query = query.filter(NPC.name.ilike(f"%{q}%") | NPC.dialogue.ilike(f"%{q}%"))
    if zone:
        query = query.filter(NPC.zone.ilike(f"%{zone}%"))
    return query.order_by(NPC.last_seen.desc()).offset(offset).limit(limit).all()


@router.get("/{npc_id}", response_model=NPCOut)
def get_npc(npc_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    npc = db.get(NPC, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    return npc


@router.delete("/{npc_id}")
def delete_npc(npc_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    npc = db.get(NPC, npc_id)
    if not npc:
        raise HTTPException(404, "Not found")
    db.delete(npc)
    db.commit()
    return {"ok": True}
