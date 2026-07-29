from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class MeetingBase(BaseModel):
    title: Optional[str] = None

class MeetingCreate(MeetingBase):
    pass

class MeetingResponse(MeetingBase):
    id: UUID
    owner_id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True