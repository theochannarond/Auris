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

    # ─── Identifiants Vexa (mode vidéo uniquement) ───
    # Renseignés au lancement du bot. vexa_meeting_id est l'entier que Vexa
    # renvoie dans ses webhooks (ex. 27246) : c'est la SEULE clé permettant de
    # relier un événement entrant à cette réunion, Vexa ne connaissant pas nos
    # UUID. Sans cette colonne, un webhook arrive sans destinataire identifiable.
    vexa_meeting_id = Column(Integer, nullable=True, index=True)
    vexa_platform   = Column(String(30), nullable=True)   # google_meet | teams | zoom
    vexa_native_id  = Column(String(100), nullable=True)  # code de réunion, ex. ora-scow-epu
    started_at   = Column(DateTime, nullable=True)
    ended_at     = Column(DateTime, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    created_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at   = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at   = Column(DateTime, nullable=True)  # soft delete RGPD Art.17