from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User


router = APIRouter(prefix="/api/v1", tags=["auth"])

# Stockage temporaire des consentements (sera remplacé par BDD en SCRUM-79)
consents_store = {}

@router.post("/consents", status_code=status.HTTP_201_CREATED)
async def create_consent(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    consent = {
        "id": str(uuid4()),
        "user_id": user_id,
        "given_at": datetime.utcnow().isoformat(),
        "ip_address": request.client.host,
        "is_active": True
    }
    consents_store[user_id] = consent
    return {
        "message": "Consentement enregistré avec succès",
        "consent": consent
    }

@router.get("/consents/check", status_code=status.HTTP_200_OK)
async def check_consent(
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    consent = consents_store.get(user_id)
    has_consent = consent is not None and consent.get("is_active", False)
    return {
        "has_consent": has_consent,
        "consent": consent if has_consent else None
    }

def require_consent(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    consent = consents_store.get(user_id)
    if not consent or not consent.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consentement RGPD requis avant tout enregistrement"
        )
    return consent


@router.post("/auth/register", status_code=status.HTTP_200_OK)
async def register_user(
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    """
    Crée l'utilisateur en base s'il n'existe pas encore.
    Appelé automatiquement après le login Keycloak.
    """
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        user = User(
            keycloak_id = current_user["id"],
            email       = current_user.get("email", ""),
            full_name   = current_user.get("name") or current_user.get("preferred_username") or "Utilisateur",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"id": str(user.id), "keycloak_id": user.keycloak_id}