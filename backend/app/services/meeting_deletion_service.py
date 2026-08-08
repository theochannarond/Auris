from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
from app.models.transcription import Transcription
from app.models.summary import Summary


# Tables filles d'une réunion : toutes portent meeting_id et deleted_at
CHILD_MODELS = (AudioFile, Transcription, Summary)


def _cascade_soft_delete(db: Session, meeting_id: UUID, deleted_at: datetime) -> None:
    """
    Propage la date de suppression aux tables filles.

    Les clés étrangères sont déclarées ON DELETE CASCADE, mais cette cascade
    n'existe qu'au niveau SQL et ne se déclenche que sur un vrai DELETE.
    Un soft delete est un UPDATE : la propagation doit être faite à la main.
    """
    for model in CHILD_MODELS:
        # UPDATE groupé : une requête par table plutôt qu'un aller-retour par ligne
        db.query(model).filter(
            model.meeting_id == meeting_id,
            model.deleted_at == None
        ).update({model.deleted_at: deleted_at}, synchronize_session=False)


def soft_delete_meeting(db: Session, meeting: Meeting) -> Meeting:
    """
    Marque une réunion et toutes ses données comme supprimées (RGPD Art.17).

    Les lignes restent en base jusqu'à la fin de la période de conservation
    légale : c'est la purge définitive qui les effacera. Tous les endpoints de
    lecture filtrent déjà `deleted_at == None`, la réunion et son contenu
    disparaissent donc du dashboard dès que cette date est posée.
    """
    # Idempotent : une réunion déjà supprimée garde sa date d'origine
    if meeting.deleted_at is not None:
        return meeting

    # Une seule date pour la réunion et ses filles : la période de conservation
    # expire au même instant pour toutes les lignes, ce dont dépend la purge
    deleted_at = datetime.utcnow()

    meeting.deleted_at = deleted_at
    _cascade_soft_delete(db, meeting.id, deleted_at)

    db.commit()
    db.refresh(meeting)
    return meeting
