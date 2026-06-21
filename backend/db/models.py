from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    thumbnail = Column(String)
    category = Column(String, default="general")  # quest, loot, npc, general
    ocr_text = Column(Text)
    zone = Column(String)
    captured_at = Column(DateTime, default=datetime.utcnow)


class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    zone = Column(String, index=True)
    npc_name = Column(String)
    status = Column(String, default="active")  # active, completed, failed
    screenshot_id = Column(Integer, ForeignKey("screenshots.id"), nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)
    raw_ocr_text = Column(Text)


class LootEntry(Base):
    __tablename__ = "loot"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String, nullable=False, index=True)
    quantity = Column(Integer, default=1)
    zone = Column(String)
    screenshot_id = Column(Integer, ForeignKey("screenshots.id"), nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)


class NPC(Base):
    __tablename__ = "npcs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    zone = Column(String)
    dialogue = Column(Text)
    screenshot_id = Column(Integer, ForeignKey("screenshots.id"), nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)


class VoiceLog(Base):
    __tablename__ = "voice_logs"

    id = Column(Integer, primary_key=True, index=True)
    command = Column(String)
    result = Column(Text)
    executed_at = Column(DateTime, default=datetime.utcnow)
