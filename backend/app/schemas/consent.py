from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class ConsentBase(BaseModel):
    meeting_id: Optional[UUID] = None

class ConsentCreate(ConsentBase):
    pass

class ConsentResponse(ConsentBase):
    id: UUID
    user_id: UUID
    given_at: datetime
    ip_address: Optional[str] = None
    is_active: bool
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True