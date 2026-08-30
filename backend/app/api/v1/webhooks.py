"""
Réception des événements Vexa (mode vidéo).

Contrat vérifié le 30 août 2026 contre l'API réelle. Deux corrections majeures
par rapport à la version précédente, qui n'a jamais pu traiter un seul appel :

  - les noms d'événements attendus (bot.joined / bot.left / bot.failed)
    n'existent pas. Vexa émet "meeting.started", "meeting.status_change" et
    "meeting.completed" ;
  - le champ meeting_id porte l'identifiant NUMÉRIQUE de Vexa (ex. 27246), pas
    notre UUID. Le schéma le déclarait en UUID, donc toute charge utile réelle
    aurait été rejetée avant même d'être lue.

C'est aussi ici que se referme le trou fonctionnel du mode vidéo : à la fin de
la réunion, on récupère l'audio capté par le bot, on le dépose sur OVH et on
déclenche la transcription — chaînon qui n'existait nulle part, si bien qu'une
réunion vidéo restait bloquée en "processing" indéfiniment.
"""

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
import hmac
import logging

from app.core.database import SessionLocal, settings
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
from app.models.transcription import Transcription
from app.services import vexa_service
from app.services.storage_service import upload_audio_file_with_fallback
from app.api.v1.transcriptions import run_transcription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Vexa ne documente pas le nom de l'en-tête portant le secret. On accepte les
# candidats plausibles plutôt que d'en imposer un : la journalisation ci-dessous
# liste les en-têtes réellement reçus, ce qui permettra de resserrer ensuite.
SECRET_HEADERS = (
    "x-vexa-secret",
    "x-webhook-secret",
    "x-vexa-signature",
    "x-hub-signature-256",
    "webhook-secret",
    "authorization",
)

# Statuts Vexa signifiant « la réunion est finie, l'audio est disponible »
COMPLETED_STATUSES = ("completed", "finished", "stopped", "ended")


def _extract_secret(headers) -> Optional[str]:
    for name in SECRET_HEADERS:
        value = headers.get(name)
        if value:
            return value.replace("Bearer ", "").replace("sha256=", "").strip()
    return None


def _secret_is_valid(headers) -> bool:
    expected = settings.VEXA_WEBHOOK_SECRET or ""
    received = _extract_secret(headers)
    if not expected or not received:
        return False
    # compare_digest : comparaison à temps constant. Un simple "==" laisse
    # fuiter la longueur du préfixe correct par le temps de réponse.
    return hmac.compare_digest(received, expected)


@router.post("/vexa", status_code=200)
async def vexa_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    data    = payload.get("data") or {}

    event  = payload.get("event_type") or payload.get("event") or ""
    status = payload.get("status") or data.get("status") or ""
    vexa_meeting_id = (
        payload.get("meeting_id")
        or data.get("meeting_id")
        or payload.get("id")
    )

    # Journalisé à chaque appel : c'est ce qui permet de constater la forme
    # réelle des messages au lieu de la deviner — l'erreur d'origine du module.
    logger.info(
        "Webhook Vexa - event=%s status=%s meeting_id=%s en-tetes=%s",
        event, status, vexa_meeting_id, sorted(request.headers.keys()),
    )

    if not _secret_is_valid(request.headers):
        logger.warning("Webhook Vexa rejete : secret absent ou invalide")
        raise HTTPException(status_code=401, detail="Secret Vexa invalide")

    if vexa_meeting_id is None:
        return {"status": "ignored", "reason": "no meeting id in payload"}

    db: Session = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.vexa_meeting_id == int(vexa_meeting_id),
            Meeting.deleted_at == None,
        ).first()

        if not meeting:
            # Cas normal : ce compte Vexa peut servir à des essais hors Auris.
            # On acquitte pour éviter des réémissions inutiles.
            return {"status": "ignored", "reason": "meeting not found"}

        # ─── Le bot est entré dans la réunion ───
        if event == "meeting.started" or status == "active":
            if meeting.status == "pending":
                meeting.status = "recording"
                meeting.started_at = datetime.utcnow()
                db.commit()

        # ─── La réunion est terminée, l'audio est disponible ───
        elif event == "meeting.completed" or status in COMPLETED_STATUSES:
            if meeting.status in ("pending", "recording"):
                meeting.status = "processing"
                meeting.ended_at = datetime.utcnow()
                db.commit()
                # Le téléchargement peut prendre plusieurs minutes : il ne doit
                # pas retarder la réponse, sans quoi Vexa considérerait la
                # livraison en échec et réémettrait l'événement.
                background_tasks.add_task(
                    ingest_vexa_recording,
                    meeting_id      = meeting.id,
                    vexa_meeting_id = int(vexa_meeting_id),
                )

        # ─── Échec du bot ───
        elif event == "meeting.failed" or status in ("failed", "error"):
            if meeting.status in ("pending", "recording"):
                meeting.status = "failed"
                db.commit()

        return {"status": "ok"}
    finally:
        db.close()


async def ingest_vexa_recording(meeting_id: UUID, vexa_meeting_id: int) -> None:
    """
    Tâche de fond : récupère l'audio capté par le bot, le dépose sur OVH, crée
    la ligne audio_files puis lance la transcription.

    C'est l'équivalent, pour le mode vidéo, de ce que fait
    POST /meetings/{id}/audio en mode dictaphone.
    """
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return

        try:
            recording = await vexa_service.find_recording(vexa_meeting_id)
            if not recording:
                raise vexa_service.VexaError(
                    f"Aucun enregistrement publie par Vexa pour la reunion {vexa_meeting_id}"
                )
            content, mime_type = await vexa_service.download_audio(recording["id"])
        except vexa_service.VexaError as e:
            logger.error("Recuperation audio Vexa impossible : %s", e)
            meeting.status = "failed"
            db.commit()
            return

        object_key = f"{meeting.id}/{uuid4()}-vexa.webm"
        result = await upload_audio_file_with_fallback(content, object_key, mime_type)

        audio_file = AudioFile(
            meeting_id      = meeting.id,
            storage_key     = result["storage_key"],
            file_size_bytes = len(content),
            mime_type       = mime_type,
        )
        db.add(audio_file)
        db.flush()   # attribue audio_file.id avant de le référencer

        duration = recording.get("duration_seconds")
        if duration:
            meeting.duration_sec = int(duration)

        transcription = Transcription(
            meeting_id    = meeting.id,
            audio_file_id = audio_file.id,
            status        = "pending",
        )
        db.add(transcription)
        db.commit()
        db.refresh(audio_file)
        db.refresh(transcription)

        logger.info(
            "Audio Vexa ingere - meeting=%s taille=%d octets, transcription=%s",
            meeting.id, len(content), transcription.id,
        )

        transcription_id = transcription.id
        storage_key      = audio_file.storage_key
        audio_mime       = audio_file.mime_type
    finally:
        db.close()

    # Hors de la session : run_transcription ouvre la sienne.
    await run_transcription(
        transcription_id = transcription_id,
        storage_key      = storage_key,
        mime_type        = audio_mime,
    )
