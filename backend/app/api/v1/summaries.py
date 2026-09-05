from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.schemas.summary import SummaryCreate, SummaryResponse
from app.services.mistral_service import generate_summary_with_backoff, MistralSummaryError
from datetime import datetime
import logging
from uuid import UUID

router = APIRouter(prefix="/api/v1", tags=["summaries"])
logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("pending", "processing", "completed")


def _abandonner(db, summary, motif: str):
    """
    Écarte un résumé qui n'a pas abouti.

    La ligne est créée AVANT l'appel à Mistral : un échec y laissait donc un
    enregistrement inutilisable. L'ancienne version écrivait le message
    d'erreur dans `content` — deux conséquences fâcheuses : l'utilisateur
    voyait la réponse brute de Mistral affichée comme si c'était son
    compte rendu, et la ligne, n'étant plus vide, passait pour un résumé
    valide. La réunion devenait alors définitivement ingénérable : chaque
    nouveau clic renvoyait cette ligne sans jamais relancer Mistral.

    On la marque donc supprimée. Elle disparaît des lectures, la réunion
    redevient générable, et l'erreur reste dans les logs pour le diagnostic.
    """
    summary.deleted_at = datetime.utcnow()
    db.commit()
    logger.warning("Resume %s abandonne : %s", summary.id, motif)


async def run_summary(summary_id: UUID, transcription_text: str):
    """
    Tâche de fond : envoie la transcription à Mistral et stocke le résultat.
    """
    db = SessionLocal()
    try:
        summary = db.query(Summary).filter(Summary.id == summary_id).first()
        if not summary:
            return

        try:
            result = await generate_summary_with_backoff(transcription_text)
        except MistralSummaryError as e:
            _abandonner(db, summary, str(e))
            return
        except Exception as e:
            _abandonner(db, summary, "erreur inattendue : %s" % e)
            return

        summary.content       = result["content"]
        summary.decisions     = result["decisions"]
        summary.action_items  = result["action_items"]
        summary.tone          = result["tone"]
        summary.theme         = result["theme"]
        summary.tokens_used   = result["tokens_used"]
        summary.processing_ms = result["processing_ms"]
        db.commit()

    finally:
        db.close()


def get_owned_meeting(meeting_id: UUID, db: Session, current_user: dict) -> Meeting:
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


@router.post("/summaries", response_model=SummaryResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_summary(
    payload:          SummaryCreate,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
    current_user:     dict    = Depends(get_current_user)
):
    meeting = get_owned_meeting(payload.meeting_id, db, current_user)

    # Récupère la transcription complète
    transcription = None
    if payload.transcription_id:
        transcription = db.query(Transcription).filter(
            Transcription.id         == payload.transcription_id,
            Transcription.deleted_at == None
        ).first()
    else:
        transcription = db.query(Transcription).filter(
            Transcription.meeting_id == meeting.id,
            Transcription.deleted_at == None,
            Transcription.status     == "completed"
        ).order_by(Transcription.created_at.desc()).first()

    if not transcription or not transcription.raw_text:
        raise HTTPException(
            status_code=404,
            detail="Aucune transcription complète trouvée pour cette réunion"
        )

    # Idempotence : on ne renvoie l'existant que s'il a REELLEMENT abouti.
    # Se contenter de vérifier qu'une ligne existe verrouillait la réunion, la
    # ligne étant créée avant l'appel à Mistral.
    existing = db.query(Summary).filter(
        Summary.meeting_id == meeting.id,
        Summary.deleted_at == None
    ).order_by(Summary.created_at.desc()).first()

    if existing and existing.content.strip():
        return existing

    if existing:
        # Tentative précédente restée vide : on réutilise la ligne plutôt que
        # d'en empiler une nouvelle à chaque essai.
        summary = existing
        summary.transcription_id = transcription.id
    else:
        summary = Summary(
            meeting_id       = meeting.id,
            transcription_id = transcription.id,
            content          = ""
        )
        db.add(summary)

    db.commit()
    db.refresh(summary)

    background_tasks.add_task(
        run_summary,
        summary_id        = summary.id,
        transcription_text = transcription.raw_text
    )

    return summary


@router.get("/summaries/{summary_id}", response_model=SummaryResponse)
async def get_summary(
    summary_id:   UUID,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    summary = db.query(Summary).filter(
        Summary.id         == summary_id,
        Summary.deleted_at == None
    ).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Résumé non trouvé")

    get_owned_meeting(summary.meeting_id, db, current_user)
    return summary


@router.get("/meetings/{meeting_id}/summary", response_model=SummaryResponse)
async def get_meeting_summary(
    meeting_id:   UUID,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    meeting = get_owned_meeting(meeting_id, db, current_user)

    summary = db.query(Summary).filter(
        Summary.meeting_id == meeting.id,
        Summary.deleted_at == None
    ).order_by(Summary.created_at.desc()).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Aucun résumé pour cette réunion")

    return summary