from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import LootEntry
import youtube as yt

router = APIRouter(prefix="/api/loot", tags=["loot"])


class LootOut(BaseModel):
    id: int
    item_name: str
    quantity: int
    zone: Optional[str]
    screenshot_id: Optional[int]
    captured_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[LootOut])
def list_loot(
    q: Optional[str] = Query(None),
    zone: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(LootEntry)
    if q:
        query = query.filter(LootEntry.item_name.ilike(f"%{q}%"))
    if zone:
        query = query.filter(LootEntry.zone.ilike(f"%{zone}%"))
    return query.order_by(LootEntry.captured_at.desc()).offset(offset).limit(limit).all()


@router.get("/summary")
def loot_summary(db: Session = Depends(get_db)):
    """Aggregated totals per item name."""
    rows = (
        db.query(LootEntry.item_name, func.sum(LootEntry.quantity).label("total"))
        .group_by(LootEntry.item_name)
        .order_by(func.sum(LootEntry.quantity).desc())
        .limit(50)
        .all()
    )
    return [{"item_name": r[0], "total": r[1]} for r in rows]


@router.get("/guide")
def loot_guide(item: str):
    return yt.lookup(item)


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    entry = db.get(LootEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Not found")
    db.delete(entry)
    db.commit()
    return {"ok": True}
