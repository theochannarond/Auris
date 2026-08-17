from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal, settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
from app.models.transcription import Transcription
from app.schemas.transcription import (
    TranscriptionCreate,
    TranscriptionResponse,
    TranscriptionStatusResponse,
)
from app.services.storage_service import download_audio_file
from app.services.voxtral_service import transcribe_audio_with_backoff, VoxtralTranscriptionError
from uuid import UUID

import os
from app.services.storage_service import LOCAL_FALLBACK_DIR


router = APIRouter(prefix="/api/v1", tags=["transcriptions"])

# Statuts pour lesquels on ne relance pas de transcription (idempotence)
ACTIVE_STATUSES = ("pending", "processing", "completed")


async def run_transcription(transcription_id: UUID, storage_key: str, mime_type: str):
    """
    Tâche de fond : récupère l'audio sur OVH, l'envoie à Voxtral, stocke le résultat.
    Ouvre sa propre session — celle de la requête HTTP est déjà fermée.
    """
    db = SessionLocal()
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        if not transcription:
            return

        transcription.status = "processing"
        db.commit()

        try:
            if storage_key.startswith("/tmp") or os.path.isfile(storage_key):
                with open(storage_key, "rb") as f:
                    audio_content = f.read()
            else:
                audio_content = await download_audio_file(storage_key)

            result = await transcribe_audio_with_backoff(
                audio_content = audio_content,
                filename      = storage_key.split("/")[-1],
                mime_type     = mime_type
            )
        except VoxtralTranscriptionError as e:
            transcription.status        = "failed"
            transcription.error_message = str(e)
            transcription.processing_ms = e.processing_ms
            transcription.retry_count   = settings.MAX_RETRY_COUNT
            db.commit()
            return
        except Exception as e:
            # Échec côté OVH (objet introuvable, credentials…) — on trace sans planter le worker
            transcription.status        = "failed"
            transcription.error_message = f"Récupération de l'audio impossible : {e}"
            db.commit()
            return

        transcription.status        = "completed"
        transcription.raw_text      = result["text"]
        transcription.language      = result["language"]
        transcription.model         = result["model"]
        transcription.processing_ms = result["processing_ms"]
        transcription.retry_count   = result.get("attempts", 1)
        db.commit()
    finally:
        db.close()


def get_owned_meeting(meeting_id: UUID, db: Session, current_user: dict) -> Meeting:
    """Récupère une réunion appartenant à l'utilisateur courant, ou lève une 404."""
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    meeting = db.query(Meeting).filter(
        Meeting.id         == meeting_id,
        Meeting.owner_id   == user.id,
        Meeting.deleted_at == None
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")

    return meeting


# ─── Déclencher la transcription d'une réunion ───
@router.post("/transcriptions", response_model=TranscriptionResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_transcription(
    payload:          TranscriptionCreate,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
    current_user:     dict    = Depends(get_current_user)
):
    meeting = get_owned_meeting(payload.meeting_id, db, current_user)

    audio_file = db.query(AudioFile).filter(
        AudioFile.meeting_id == meeting.id,
        AudioFile.deleted_at == None
    ).order_by(AudioFile.created_at.desc()).first()
    if not audio_file:
        raise HTTPException(
            status_code=404,
            detail="Aucun fichier audio n'a été uploadé pour cette réunion"
        )

    # Idempotence — le front peut renvoyer la requête, on ne transcrit pas deux fois
    existing = db.query(Transcription).filter(
        Transcription.meeting_id == meeting.id,
        Transcription.deleted_at == None,
        Transcription.status.in_(ACTIVE_STATUSES)
    ).order_by(Transcription.created_at.desc()).first()
    if existing:
        return existing

    transcription = Transcription(
        meeting_id    = meeting.id,
        audio_file_id = audio_file.id,
        status        = "pending"
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)

    background_tasks.add_task(
        run_transcription,
        transcription_id = transcription.id,
        storage_key      = audio_file.storage_key,
        mime_type        = audio_file.mime_type
    )

    return transcription


# ─── Relance manuelle après échec définitif ───
@router.post(
    "/transcriptions/{transcription_id}/retry",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def retry_transcription(
    transcription_id: UUID,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
    current_user:     dict    = Depends(get_current_user)
):
    transcription = db.query(Transcription).filter(
        Transcription.id         == transcription_id,
        Transcription.deleted_at == None
    ).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription non trouvée")

    get_owned_meeting(transcription.meeting_id, db, current_user)

    if transcription.status != "failed":
        raise HTTPException(
            status_code=400,
            detail="Seule une transcription en échec peut être relancée"
        )

    audio_file = db.query(AudioFile).filter(
        AudioFile.id == transcription.audio_file_id
    ).first()
    if not audio_file:
        raise HTTPException(
            status_code=404,
            detail="Fichier audio introuvable pour cette transcription"
        )

    transcription.status        = "pending"
    transcription.error_message = None
    transcription.retry_count   = 0
    db.commit()
    db.refresh(transcription)

    background_tasks.add_task(
        run_transcription,
        transcription_id = transcription.id,
        storage_key      = audio_file.storage_key,
        mime_type        = audio_file.mime_type
    )

    return transcription


# ─── Suivi de progression (polling React) ───
@router.get("/transcriptions/{transcription_id}/status", response_model=TranscriptionStatusResponse)
async def get_transcription_status(
    transcription_id: UUID,
    db:               Session = Depends(get_db),
    current_user:     dict    = Depends(get_current_user)
):
    transcription = db.query(Transcription).filter(
        Transcription.id         == transcription_id,
        Transcription.deleted_at == None
    ).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription non trouvée")

    get_owned_meeting(transcription.meeting_id, db, current_user)
    return transcription


# ─── Transcription complète (texte brut inclus) ───
@router.get("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: UUID,
    db:               Session = Depends(get_db),
    current_user:     dict    = Depends(get_current_user)
):
    transcription = db.query(Transcription).filter(
        Transcription.id         == transcription_id,
        Transcription.deleted_at == None
    ).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription non trouvée")

    get_owned_meeting(transcription.meeting_id, db, current_user)
    return transcription