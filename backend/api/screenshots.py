import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import Screenshot

_root = Path(__file__).resolve().parents[2]
with open(_root / "config.json") as _f:
    _cfg = json.load(_f)
SHOTS_DIR = (_root / _cfg["screenshots_dir"]).resolve()

router = APIRouter(prefix="/api/screenshots", tags=["screenshots"])


class ShotOut(BaseModel):
    id: int
    filename: str
    thumbnail: Optional[str]
    category: str
    ocr_text: Optional[str]
    zone: Optional[str]
    captured_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[ShotOut])
def list_screenshots(
    q: Optional[str] = Query(None),
    category: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Screenshot)
    if q:
        query = query.filter(Screenshot.ocr_text.ilike(f"%{q}%"))
    if category:
        query = query.filter(Screenshot.category == category)
    return query.order_by(Screenshot.captured_at.desc()).offset(offset).limit(limit).all()


@router.get("/{shot_id}", response_model=ShotOut)
def get_screenshot(shot_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    shot = db.get(Screenshot, shot_id)
    if not shot:
        raise HTTPException(404, "Screenshot not found")
    return shot


@router.delete("/{shot_id}")
def delete_screenshot(shot_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    shot = db.get(Screenshot, shot_id)
    if not shot:
        raise HTTPException(404, "Not found")
    for fname in [shot.filename, shot.thumbnail]:
        if fname:
            p = SHOTS_DIR / fname
            if p.exists():
                p.unlink()
    db.delete(shot)
    db.commit()
    return {"ok": True}
