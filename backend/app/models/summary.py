from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base
from app.models.types import JSONColumn

class Summary(Base):
    __tablename__ = "summaries"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id       = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=True)
    content          = Column(Text, nullable=False)           # CR structuré complet
    decisions        = Column(JSONColumn, nullable=True)      # décisions extraites
    action_items     = Column(JSONColumn, nullable=True)      # actions par responsable
    tone             = Column(String(50), nullable=True)      # 'formal' | 'informal' | 'technical'
    theme            = Column(String(100), nullable=True)     # thème principal
    mistral_model    = Column(String(100), nullable=False, default="mistral-small-latest")
    tokens_used      = Column(Integer, nullable=True)
    processing_ms    = Column(Integer, nullable=True)
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at       = Column(DateTime, nullable=True)        # soft delete RGPD