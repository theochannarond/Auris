from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from app.schemas.summary import SummaryResponse


class MeetingCreate(BaseModel):
    title:        str
    meeting_link: Optional[str] = None


class MeetingResponse(BaseModel):
    id:           UUID
    owner_id:     UUID
    title:        str
    mode:         str
    status:       str
    meeting_link: Optional[str] = None
    started_at:   Optional[datetime] = None
    ended_at:     Optional[datetime] = None
    duration_sec: Optional[int] = None
    created_at:   datetime
    updated_at:   datetime

    class Config:
        from_attributes = True


class MeetingListItem(BaseModel):
    """Réunion telle qu'affichée sur une carte du dashboard."""
    id:           UUID
    title:        str
    mode:         str
    status:       str
    duration_sec: Optional[int] = None
    created_at:   datetime
    theme:        Optional[str] = None   # vient de summaries
    tone:         Optional[str] = None   # vient de summaries

    class Config:
        from_attributes = True


class MeetingTranscriptionDetail(BaseModel):
    """Transcription telle qu'affichée sur la page détail d'une réunion."""
    id:            UUID
    status:        str
    raw_text:      Optional[str] = None
    diarization:   Optional[Any] = None   # segments {speaker, start, end, text}
    language:      Optional[str] = None
    processing_ms: Optional[int] = None

    class Config:
        from_attributes = True


class MeetingDetailResponse(BaseModel):
    """Réunion complète : ses métadonnées, sa transcription et son résumé."""
    id:            UUID
    title:         str
    mode:          str
    status:        str
    meeting_link:  Optional[str] = None
    started_at:    Optional[datetime] = None
    ended_at:      Optional[datetime] = None
    duration_sec:  Optional[int] = None
    created_at:    datetime
    transcription: Optional[MeetingTranscriptionDetail] = None
    summary:       Optional[SummaryResponse] = None

    class Config:
        from_attributes = True


class MeetingDeleteResponse(BaseModel):
    """Confirmation de suppression renvoyée à l'utilisateur (RGPD Art.17)."""
    id:         UUID
    deleted_at: datetime
    message:    str


class MeetingStatusUpdate(BaseModel):
    status: str


class MeetingStatusResponse(BaseModel):
    """Réponse allégée pour le polling de statut côté React."""
    id:     UUID
    status: str

    class Config:
        from_attributes = True