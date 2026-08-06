from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


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


class MeetingStatusUpdate(BaseModel):
    status: str


class MeetingStatusResponse(BaseModel):
    """Réponse allégée pour le polling de statut côté React."""
    id:     UUID
    status: str

    class Config:
        from_attributes = True