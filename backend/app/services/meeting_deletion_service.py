from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
import calendar
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
from app.models.transcription import Transcription
from app.models.summary import Summary


# Tables filles d'une réunion : toutes portent meeting_id et deleted_at
CHILD_MODELS = (AudioFile, Transcription, Summary)

# Durée de conservation légale avant effacement définitif (RGPD Art.17)
RETENTION_MONTHS = 12


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


def _subtract_months(reference: datetime, months: int) -> datetime:
    """
    Recule d'un nombre de mois calendaires.

    timedelta ne connaît que les jours : « 12 mois » ne vaut ni 360 ni 365 jours
    selon l'année. On passe donc par le calendrier, en ramenant le quantième au
    dernier jour du mois cible quand il n'existe pas (31 mars → 28 février).
    """
    month_index = reference.month - 1 - months
    year        = reference.year + month_index // 12
    month       = month_index % 12 + 1
    day         = min(reference.day, calendar.monthrange(year, month)[1])
    return reference.replace(year=year, month=month, day=day)


def purge_expired_meetings(db: Session, retention_months: int = RETENTION_MONTHS) -> int:
    """
    Efface définitivement les réunions dont la conservation légale est écoulée.

    Contrairement au soft delete, cette opération est irréversible : les lignes
    quittent la base. Elle ne vise que les réunions déjà supprimées par leur
    propriétaire — une réunion active n'est jamais purgée, quel que soit son âge.

    Retourne le nombre de réunions effacées.

    Aucun déclencheur n'est branché pour l'instant : le mécanisme de
    planification (cron, tâche applicative, pg_cron) reste à décider.
    """
    cutoff = _subtract_months(datetime.utcnow(), retention_months)

    expired_ids = [
        row.id for row in db.query(Meeting.id).filter(
            Meeting.deleted_at != None,
            Meeting.deleted_at <= cutoff
        ).all()
    ]
    if not expired_ids:
        return 0

    # Les filles d'abord. Les clés étrangères sont ON DELETE CASCADE, mais
    # SQLite ne les applique pas par défaut : on ne dépend pas du dialecte.
    # reversed() place Summary avant Transcription, dont il dépend.
    for model in reversed(CHILD_MODELS):
        db.query(model).filter(
            model.meeting_id.in_(expired_ids)
        ).delete(synchronize_session=False)

    db.query(Meeting).filter(
        Meeting.id.in_(expired_ids)
    ).delete(synchronize_session=False)

    db.commit()
    return len(expired_ids)
