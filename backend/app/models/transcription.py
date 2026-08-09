from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base
from app.models.types import JSONColumn

class Transcription(Base):
    __tablename__ = "transcriptions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id    = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    audio_file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="SET NULL"), nullable=True)
    status        = Column(String(20), nullable=False, default="pending")  # pending | processing | completed | failed
    raw_text      = Column(Text, nullable=True)                            # texte brut renvoyé par Voxtral
    diarization   = Column(JSONColumn, nullable=True)  # labels locuteurs + timestamps Voxtral
    language      = Column(String(10), nullable=True)                      # code langue détecté ("fr", "en"…)
    model         = Column(String(50), nullable=True)                      # modèle Voxtral utilisé
    processing_ms = Column(Integer, nullable=True)                         # durée de traitement Voxtral en ms
    error_message = Column(Text, nullable=True)                            # message d'erreur si status = failed
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at    = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at    = Column(DateTime, nullable=True)  # soft delete RGPD Art.17
