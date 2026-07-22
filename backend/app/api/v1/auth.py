from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4
from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["auth"])

@router.post("/consents", status_code=status.HTTP_201_CREATED)
async def create_consent(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    consent = {
        "id": str(uuid4()),
        "user_id": current_user["id"],
        "given_at": datetime.utcnow().isoformat(),
        "ip_address": request.client.host,
        "is_active": True
    }
    return {
        "message": "Consentement enregistré avec succès",
        "consent": consent
    }