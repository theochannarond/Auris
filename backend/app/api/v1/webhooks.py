from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from app.core.database import get_db, settings
from app.models.meeting import Meeting
from app.schemas.webhook import VexaWebhookPayload
from datetime import datetime

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


async def verify_vexa_secret(x_vexa_secret: str = Header(None)):
    """
    Vérification du secret Vexa.
    Keycloak ne peut pas protéger ce endpoint — c'est Vexa qui l'appelle.
    On utilise un secret partagé en attendant confirmation du mécanisme Vexa.
    """
    if not x_vexa_secret or x_vexa_secret != settings.VEXA_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Secret Vexa invalide")


@router.post("/vexa", status_code=200)
async def vexa_webhook(
    payload:  VexaWebhookPayload,
    db:       Session = Depends(get_db),
    _:        None    = Depends(verify_vexa_secret)
):
    meeting = db.query(Meeting).filter(
        Meeting.id == payload.meeting_id,
        Meeting.deleted_at == None
    ).first()

    if not meeting:
        return {"status": "ignored", "reason": "meeting not found or deleted"}

    # Idempotence — on ne fait jamais reculer un statut
    if payload.event == "bot.joined" and meeting.status == "pending":
        meeting.status = "recording"
        meeting.started_at = datetime.utcnow()
        db.commit()

    elif payload.event == "bot.left" and meeting.status == "recording":
        meeting.status = "processing"
        meeting.ended_at = datetime.utcnow()
        db.commit()

    elif payload.event == "bot.failed" and meeting.status in ("pending", "recording"):
        meeting.status = "failed"
        db.commit()

    return {"status": "ok"}