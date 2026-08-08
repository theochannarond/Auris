from sqlalchemy.orm import Session
from datetime import datetime
from app.models.meeting import Meeting


def soft_delete_meeting(db: Session, meeting: Meeting) -> Meeting:
    """
    Marque une réunion comme supprimée sans effacer la ligne (RGPD Art.17).

    La ligne reste en base jusqu'à la fin de la période de conservation légale :
    c'est la purge définitive qui l'effacera. Tous les endpoints de lecture
    filtrent déjà `deleted_at == None`, la réunion disparaît donc du dashboard
    dès que cette date est posée.
    """
    # Idempotent : une réunion déjà supprimée garde sa date d'origine
    if meeting.deleted_at is not None:
        return meeting

    meeting.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(meeting)
    return meeting
