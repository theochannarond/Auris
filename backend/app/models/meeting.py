from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title        = Column(String(255), nullable=False)
    mode         = Column(String(20), nullable=False, default="dictaphone")  # "dictaphone" | "video"
    status       = Column(String(20), nullable=False, default="pending")     # pending | recording | processing | completed | failed
    meeting_link = Column(String(500), nullable=True)
    started_at   = Column(DateTime, nullable=True)
    ended_at     = Column(DateTime, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    created_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at   = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at   = Column(DateTime, nullable=True)  # soft delete RGPD Art.17