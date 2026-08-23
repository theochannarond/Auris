from sqlalchemy import Column, String, DateTime, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base

class AudioFile(Base):
    __tablename__ = "audio_files"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id      = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    storage_key     = Column(String(512), nullable=False)   # chemin OVH : "meetings/uuid/audio.wav"
    file_size_bytes = Column(BigInteger, nullable=True)
    upload_ms = Column(Integer, nullable=True)  # durée upload OVH en millisecondes
    duration_sec    = Column(Integer, nullable=True)
    mime_type       = Column(String(50), nullable=False, default="audio/wav")
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)