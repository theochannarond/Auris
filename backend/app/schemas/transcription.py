from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class TranscriptionCreate(BaseModel):
    meeting_id: UUID


class TranscriptionResponse(BaseModel):
    id:            UUID
    meeting_id:    UUID
    audio_file_id: Optional[UUID] = None
    status:        str
    raw_text:      Optional[str] = None
    language:      Optional[str] = None
    model:         Optional[str] = None
    processing_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at:    datetime
    updated_at:    datetime

    class Config:
        from_attributes = True


class TranscriptionStatusResponse(BaseModel):
    """Réponse allégée pour le polling de progression côté React."""
    id:            UUID
    meeting_id:    UUID
    status:        str
    processing_ms: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
