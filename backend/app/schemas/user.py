from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    keycloak_id: str

class UserResponse(UserBase):
    id: UUID
    keycloak_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True