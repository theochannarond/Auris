from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any

class SummaryCreate(BaseModel):
    meeting_id:      UUID
    transcription_id: Optional[UUID] = None

class SummaryResponse(BaseModel):
    id:               UUID
    meeting_id:       UUID
    transcription_id: Optional[UUID] = None
    content:          str
    decisions:        Optional[Any] = None
    action_items:     Optional[Any] = None
    tone:             Optional[str] = None
    theme:            Optional[str] = None
    mistral_model:    str
    tokens_used:      Optional[int] = None
    processing_ms:    Optional[int] = None
    created_at:       datetime

    class Config:
        from_attributes = True