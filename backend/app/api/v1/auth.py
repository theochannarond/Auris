from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.consent import Consent  # le vrai modèle, plus consents_store

router = APIRouter(prefix="/api/v1", tags=["auth"])


# --- Créer un consentement (maintenant en vraie BDD) ---
@router.post("/consents", status_code=status.HTTP_201_CREATED)
async def create_consent(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # 1. Retrouver l'utilisateur en base à partir de son ID Keycloak
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    # 2. Créer un vrai objet Consent (plus un dictionnaire)
    consent = Consent(
        user_id=user.id,
        given_at=datetime.utcnow(),
        ip_address=request.client.host,
        is_active=True
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)

    # 3. Renvoyer la réponse (même structure qu'avant)
    return {
        "message": "Consentement enregistré avec succès",
        "consent": {
            "id": str(consent.id),
            "user_id": str(consent.user_id),
            "given_at": consent.given_at.isoformat(),
            "ip_address": consent.ip_address,
            "is_active": consent.is_active
        }
    }


# --- Vérifier si un consentement actif existe ---
@router.get("/consents/check", status_code=status.HTTP_200_OK)
async def check_consent(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        return {"has_consent": False, "consent": None}

    # Cherche le dernier consentement actif de cet utilisateur
    consent = db.query(Consent).filter(
        Consent.user_id == user.id,
        Consent.is_active == True
    ).order_by(Consent.given_at.desc()).first()

    has_consent = consent is not None

    return {
        "has_consent": has_consent,
        "consent": {
            "id": str(consent.id),
            "user_id": str(consent.user_id),
            "given_at": consent.given_at.isoformat(),
            "ip_address": consent.ip_address,
            "is_active": consent.is_active
        } if has_consent else None
    }


# --- La dependency de blocage (maintenant sur vraie BDD) ---
def require_consent(
    db: Session = Depends(get_db),  # nouveau : elle a besoin de la BDD maintenant
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consentement RGPD requis avant tout enregistrement"
        )

    consent = db.query(Consent).filter(
        Consent.user_id == user.id,
        Consent.is_active == True
    ).order_by(Consent.given_at.desc()).first()

    if not consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consentement RGPD requis avant tout enregistrement"
        )

    return consent  # renvoie l'objet Consent, plus un dictionnaire


# --- Créer l'utilisateur après login Keycloak (déjà fait par l'équipe, inchangé) ---
@router.post("/auth/register", status_code=status.HTTP_200_OK)
async def register_user(
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
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