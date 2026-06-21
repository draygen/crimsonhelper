from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import Quest
import youtube as yt

router = APIRouter(prefix="/api/quests", tags=["quests"])
_VALID_STATUSES = {"active", "completed", "failed"}


class QuestOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    zone: Optional[str]
    npc_name: Optional[str]
    status: str
    screenshot_id: Optional[int]
    captured_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[QuestOut])
def list_quests(
    q: Optional[str] = Query(None, description="Search title/description"),
    zone: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Quest)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Quest.title.ilike(like) | Quest.description.ilike(like) | Quest.raw_ocr_text.ilike(like)
        )
    if zone:
        query = query.filter(Quest.zone.ilike(f"%{zone}%"))
    if status:
        query = query.filter(Quest.status == status)
    return query.order_by(Quest.captured_at.desc()).offset(offset).limit(limit).all()


@router.get("/{quest_id}", response_model=QuestOut)
def get_quest(quest_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    quest = db.get(Quest, quest_id)
    if not quest:
        raise HTTPException(404, "Quest not found")
    return quest


@router.delete("/{quest_id}")
def delete_quest(quest_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    quest = db.get(Quest, quest_id)
    if not quest:
        raise HTTPException(404, "Quest not found")
    db.delete(quest)
    db.commit()
    return {"ok": True}


@router.patch("/{quest_id}/status")
def update_status(quest_id: int, status: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    if status not in _VALID_STATUSES:
        raise HTTPException(400, f"status must be one of: {', '.join(sorted(_VALID_STATUSES))}")
    quest = db.get(Quest, quest_id)
    if not quest:
        raise HTTPException(404, "Quest not found")
    quest.status = status
    db.commit()
    return {"ok": True, "status": status}


@router.get("/{quest_id}/guide")
def get_guide(quest_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    quest = db.get(Quest, quest_id)
    if not quest:
        raise HTTPException(404, "Quest not found")
    return yt.lookup(quest.title)
