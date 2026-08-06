from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class AudioFileResponse(BaseModel):
    id:              UUID
    meeting_id:      UUID
    storage_key:     str
    file_size_bytes: Optional[int] = None
    duration_sec:    Optional[int] = None
    mime_type:       str
    created_at:      datetime

    class Config:
        from_attributes = True