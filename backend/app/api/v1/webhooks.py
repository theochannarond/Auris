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
# candidats plausibles plutôt que d'en imposer un seul au jugé. Vérifié en
# production le 30 août 2026 : un de ces noms correspond bien (le webhook est
# accepté), la liste pourra être resserrée quand on saura lequel.
SECRET_HEADERS = (
    "x-vexa-secret",
    "x-webhook-secret",
    "x-vexa-signature",
    "x-hub-signature-256",
    "webhook-secret",
    "authorization",
)

# Mêmes motifs que app/core/logging_config.py : un message les contenant est
# effacé par le formateur, journalisation de diagnostic comprise.
SECRET_PATTERNS = (
    "password", "token", "secret", "api_key",
    "access_key", "authorization", "credential",
)

# Statuts Vexa signifiant « la réunion est finie, l'audio est disponible »
COMPLETED_STATUSES = ("completed", "finished", "stopped", "ended")

# Statuts Vexa signifiant « le bot est en place et capte »
ACTIVE_STATUSES = ("active", "recording")


def _pour_journal(valeur, _profondeur=0):
    """
    Retire les clés sensibles avant journalisation.

    Sans ce nettoyage, le formateur JSON détecte un mot interdit et remplace la
    ligne ENTIÈRE par "[REDACTED]" — ce qui a rendu le premier diagnostic de ce
    webhook illisible alors même que la charge utile ne posait aucun problème.
    """
    if isinstance(valeur, dict):
        return {
            k: _pour_journal(v, _profondeur + 1)
            for k, v in valeur.items()
            if not any(motif in k.lower() for motif in SECRET_PATTERNS)
        }
    if isinstance(valeur, list):
        return [_pour_journal(v, _profondeur + 1) for v in valeur]
    return valeur


def _reunion_vexa(payload: dict) -> dict:
    """
    Renvoie le bloc décrivant la réunion.

    Forme réelle relevée en production le 30 août 2026 :
        {"event_type": "meeting.completed",
         "data": {"meeting": {"id": 27251, "status": "completed", ...}}}

    Rien n'était donc à la racine, ce que supposait la version précédente. Les
    variantes plus plates restent tolérées : Vexa versionne sa charge utile
    (champ api_version) et cette structure peut évoluer.
    """
    data = payload.get("data") or {}
    return data.get("meeting") or data or payload


def _identifiant_reunion(payload: dict) -> Optional[int]:
    reunion = _reunion_vexa(payload)
    brut = reunion.get("id") or reunion.get("meeting_id") or payload.get("meeting_id")
    try:
        return int(brut) if brut is not None else None
    except (TypeError, ValueError):
        return None


def _statut_reunion(payload: dict) -> str:
    return _reunion_vexa(payload).get("status") or payload.get("status") or ""


def _identifiant_enregistrement(payload: dict) -> Optional[int]:
    """
    Extrait l'identifiant d'enregistrement porté par l'événement.

    Vexa le fournit directement dans "meeting.completed". S'en servir évite un
    appel de plus ET la course à la publication : interroger /recordings juste
    après la fin d'une réunion peut ne rien retourner.
    """
    interne = _reunion_vexa(payload).get("data") or {}
    enregistrements = interne.get("recordings") or []
    if not isinstance(enregistrements, list):
        return None
    complets = [
        e for e in enregistrements
        if isinstance(e, dict) and e.get("id") and e.get("status") == "completed"
    ]
    if complets:
        return complets[0]["id"]
    for e in enregistrements:
        if isinstance(e, dict) and e.get("id"):
            return e["id"]
    return None


def _horodatage(valeur) -> Optional[datetime]:
    """Convertit un horodatage ISO Vexa ("...Z") en datetime naïf UTC."""
    if not valeur:
        return None
    try:
        return datetime.fromisoformat(str(valeur).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


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

    event           = payload.get("event_type") or payload.get("event") or ""
    statut          = _statut_reunion(payload)
    vexa_meeting_id = _identifiant_reunion(payload)

    # Journalisé à chaque appel : c'est ce qui permet de constater la forme
    # réelle des messages au lieu de la deviner — l'erreur d'origine du module.
    # Le contenu passe par _pour_journal() car le formateur JSON efface tout
    # message contenant "secret", "token" ou "authorization" (logging_config.py),
    # et Vexa renvoie justement un champ webhook_secret dans certaines charges.
    logger.info(
        "Webhook Vexa - event=%s statut=%s reunion=%s contenu=%s",
        event, statut, vexa_meeting_id, _pour_journal(payload),
    )

    if not _secret_is_valid(request.headers):
        logger.warning("Webhook Vexa rejete : secret absent ou invalide")
        raise HTTPException(status_code=401, detail="Secret Vexa invalide")

    if vexa_meeting_id is None:
        return {"status": "ignored", "reason": "no meeting id in payload"}

    db: Session = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(
            Meeting.vexa_meeting_id == vexa_meeting_id,
            Meeting.deleted_at == None,
        ).first()

        if not meeting:
            # Cas normal : ce compte Vexa peut servir à des essais hors Auris.
            # On acquitte pour éviter des réémissions inutiles.
            return {"status": "ignored", "reason": "meeting not found"}

        reunion = _reunion_vexa(payload)

        # ─── Le bot est entré dans la réunion ───
        if event == "meeting.started" or statut in ACTIVE_STATUSES:
            if meeting.status == "pending":
                meeting.status = "recording"
                meeting.started_at = _horodatage(reunion.get("start_time")) or datetime.utcnow()
                db.commit()

        # ─── La réunion est terminée, l'audio est disponible ───
        elif event == "meeting.completed" or statut in COMPLETED_STATUSES:
            if meeting.status in ("pending", "recording"):
                debut = _horodatage(reunion.get("start_time"))
                fin   = _horodatage(reunion.get("end_time"))

                meeting.status     = "processing"
                meeting.started_at = meeting.started_at or debut
                meeting.ended_at   = fin or datetime.utcnow()
                # Vexa laisse souvent duration_seconds à null : on la déduit des
                # bornes réelles plutôt que de laisser la colonne vide.
                if debut and fin:
                    meeting.duration_sec = max(int((fin - debut).total_seconds()), 0)
                db.commit()

                # Le téléchargement peut prendre plusieurs minutes : il ne doit
                # pas retarder la réponse, sans quoi Vexa considérerait la
                # livraison en échec et réémettrait l'événement.
                background_tasks.add_task(
                    ingest_vexa_recording,
                    meeting_id      = meeting.id,
                    vexa_meeting_id = vexa_meeting_id,
                    recording_id    = _identifiant_enregistrement(payload),
                )

        # ─── Échec du bot ───
        elif event in ("meeting.failed", "bot.failed") or statut in ("failed", "error"):
            if meeting.status in ("pending", "recording"):
                meeting.status = "failed"
                db.commit()

        return {"status": "ok"}
    finally:
        db.close()


async def ingest_vexa_recording(
    meeting_id: UUID,
    vexa_meeting_id: int,
    recording_id: Optional[int] = None,
) -> None:
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
            # recording_id vient de la charge utile du webhook quand elle le
            # porte ; on ne retombe sur /recordings que s'il manque, car cette
            # liste peut ne rien contenir juste apres la fin d'une reunion.
            if recording_id is None:
                enregistrement = await vexa_service.find_recording(vexa_meeting_id)
                if not enregistrement:
                    raise vexa_service.VexaError(
                        f"Aucun enregistrement publie par Vexa pour la reunion {vexa_meeting_id}"
                    )
                recording_id = enregistrement["id"]

            content, mime_type = await vexa_service.download_audio(recording_id)
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
            "Audio Vexa ingere - reunion=%s taille=%d octets, transcription=%s",
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
