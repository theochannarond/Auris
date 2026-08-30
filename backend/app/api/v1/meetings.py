from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.api.v1.auth import require_consent
from app.models.user import User
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
from app.models.summary import Summary
from app.models.transcription import Transcription
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingStatusUpdate, MeetingStatusResponse, MeetingListItem, MeetingDetailResponse, MeetingTranscriptionDetail, MeetingDeleteResponse
from app.schemas.summary import SummaryResponse
from app.services import vexa_service
from app.services.storage_service import upload_audio_file_with_fallback, delete_audio_file
from app.services.meeting_deletion_service import soft_delete_meeting
from datetime import datetime
from typing import List
from uuid import UUID
import uuid as uuid_lib
import time


router = APIRouter(prefix="/api/v1", tags=["meetings"])


# ─── Dashboard — historique des réunions de l'utilisateur ───
@router.get("/meetings", response_model=List[MeetingListItem])
async def list_meetings(
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    # owner_id vient du sub du JWT — un utilisateur ne voit jamais les réunions d'un autre
    meetings = db.query(Meeting).filter(
        Meeting.owner_id   == user.id,
        Meeting.deleted_at == None
    ).order_by(Meeting.created_at.desc()).all()

    if not meetings:
        return []

    # Thème et ton vivent dans summaries : une seule requête groupée plutôt qu'une par réunion
    summaries = db.query(Summary).filter(
        Summary.meeting_id.in_([m.id for m in meetings]),
        Summary.deleted_at == None
    ).order_by(Summary.created_at.asc()).all()
    summary_by_meeting = {s.meeting_id: s for s in summaries}  # si plusieurs, le plus récent gagne

    items = []
    for meeting in meetings:
        summary = summary_by_meeting.get(meeting.id)
        items.append(MeetingListItem(
            id           = meeting.id,
            title        = meeting.title,
            mode         = meeting.mode,
            status       = meeting.status,
            duration_sec = meeting.duration_sec,
            created_at   = meeting.created_at,
            theme        = summary.theme if summary else None,
            tone         = summary.tone  if summary else None
        ))
    return items


# ─── Dashboard — détail d'une réunion ───
@router.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(
    meeting_id:   UUID,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    # Le filtre sur owner_id évite qu'un utilisateur lise la réunion d'un autre en devinant l'UUID
    meeting = db.query(Meeting).filter(
        Meeting.id         == meeting_id,
        Meeting.owner_id   == user.id,
        Meeting.deleted_at == None
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")

    # Rien ne contraint l'unicité en base : on retient la plus récente
    transcription = db.query(Transcription).filter(
        Transcription.meeting_id == meeting.id,
        Transcription.deleted_at == None
    ).order_by(Transcription.created_at.desc()).first()

    summary = db.query(Summary).filter(
        Summary.meeting_id == meeting.id,
        Summary.deleted_at == None
    ).order_by(Summary.created_at.desc()).first()

    return MeetingDetailResponse(
        id            = meeting.id,
        title         = meeting.title,
        mode          = meeting.mode,
        status        = meeting.status,
        meeting_link  = meeting.meeting_link,
        started_at    = meeting.started_at,
        ended_at      = meeting.ended_at,
        duration_sec  = meeting.duration_sec,
        created_at    = meeting.created_at,
        transcription = MeetingTranscriptionDetail.model_validate(transcription) if transcription else None,
        summary       = SummaryResponse.model_validate(summary) if summary else None
    )


# ─── RGPD Art.17 — suppression d'une réunion ───
@router.delete("/meetings/{meeting_id}", response_model=MeetingDeleteResponse)
async def delete_meeting(
    meeting_id:   UUID,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    # Même filtre owner_id qu'en lecture : on ne supprime jamais la réunion d'un autre.
    # Une réunion déjà supprimée renvoie 404 — l'appelant ne peut pas distinguer
    # "jamais existé" de "déjà supprimée", ce qui évite de divulguer son existence.
    meeting = db.query(Meeting).filter(
        Meeting.id         == meeting_id,
        Meeting.owner_id   == user.id,
        Meeting.deleted_at == None
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")

    # Les clés sont relevées avant le soft delete, tant que les lignes sont encore actives
    storage_keys = [
        audio.storage_key for audio in db.query(AudioFile).filter(
            AudioFile.meeting_id == meeting.id,
            AudioFile.deleted_at == None
        ).all()
    ]

    soft_delete_meeting(db, meeting)

    # La base fait foi : un échec OVH laisse un fichier orphelin, jamais une
    # donnée encore lisible par l'utilisateur. On ne remonte donc pas l'erreur.
    for storage_key in storage_keys:
        await delete_audio_file(storage_key)

    return MeetingDeleteResponse(
        id         = meeting.id,
        deleted_at = meeting.deleted_at,
        message    = "Réunion supprimée. Vos données seront définitivement effacées à l'issue de la période de conservation légale."
    )


# ─── Dictaphone — créer une réunion ───
@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload:      MeetingCreate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user),
    consent:      dict    = Depends(require_consent)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    meeting = Meeting(
        owner_id = user.id,
        title    = payload.title,
        mode     = "dictaphone",
        status   = "pending"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


# ─── Dictaphone — upload audio ───
@router.post("/meetings/{meeting_id}/audio", response_model=MeetingResponse)
async def upload_meeting_audio(
    meeting_id:   UUID,
    file:         UploadFile = File(...),
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé en base")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.owner_id == user.id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réunion non trouvée")

    content = await file.read()
    object_key = f"{meeting_id}/{uuid_lib.uuid4()}-{file.filename}"

    upload_start = time.perf_counter()
    result = await upload_audio_file_with_fallback(content, object_key, file.content_type)
    upload_ms = round((time.perf_counter() - upload_start) * 1000, 2)
    object_key = result["storage_key"]

    # La clé OVH est tracée dans audio_files — c'est elle que la transcription ira chercher
    audio_file = AudioFile(
        meeting_id=meeting.id,
        storage_key=object_key,
        file_size_bytes=len(content),
        mime_type=file.content_type or "audio/wav",
        upload_ms=int(upload_ms)
    )
    db.add(audio_file)
    # Calcule la durée approximative depuis la taille du fichier WAV
    # WAV 16bit mono 16kHz = ~32000 bytes/sec
    estimated_duration = len(content) // 16000
    if estimated_duration > 0:
        meeting.duration_sec = estimated_duration
    db.commit()
    db.refresh(meeting)
    return meeting


# ─── Vidéo — créer une réunion avec bot Vexa ───
@router.post("/meetings/video", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_video_meeting(
    meeting_data: MeetingCreate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user),
    consent:      dict    = Depends(require_consent)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    meeting = Meeting(
        owner_id     = user.id,
        title        = meeting_data.title,
        mode         = "video",
        status       = "pending",
        meeting_link = meeting_data.meeting_link
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Le retour de Vexa porte l'identifiant numerique qu'il renverra dans ses
    # webhooks : sans le stocker, aucun evenement entrant ne peut etre rattache
    # a cette reunion. L'ancienne version jetait cette reponse.
    if meeting_data.meeting_link:
        try:
            bot = await vexa_service.spawn_bot(meeting_data.meeting_link)
            meeting.vexa_meeting_id = bot.get("id")
            meeting.vexa_platform   = bot.get("platform")
            meeting.vexa_native_id  = bot.get("native_meeting_id")
            db.commit()
            db.refresh(meeting)
        except vexa_service.VexaError as e:
            # Le bot n'est pas parti : la reunion ne produira jamais rien. On le
            # dit tout de suite plutot que de laisser l'utilisateur attendre un
            # bot fantome, comme le faisait la version precedente.
            meeting.status = "failed"
            db.commit()
            raise HTTPException(status_code=502, detail=str(e))

    return meeting


@router.put("/meetings/{meeting_id}/status", response_model=MeetingResponse)
async def update_meeting_status(
    meeting_id:    UUID,
    payload:       MeetingStatusUpdate,
    db:            Session = Depends(get_db),
    current_user:  dict    = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.owner_id == user.id,
        Meeting.deleted_at == None
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")

    valid_statuses = ["pending", "recording", "processing", "completed", "failed"]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs acceptées : {valid_statuses}")

    meeting.status = payload.status
    db.commit()
    db.refresh(meeting)
    return meeting


# Dernière interrogation de Vexa par réunion, pour ne pas l'appeler à chaque
# sondage du navigateur (toutes les 3 s côté useMeetingStatus).
_derniere_verif_bot: dict[UUID, float] = {}
INTERVALLE_VERIF_BOT_SEC = 5.0


async def _synchroniser_etat_bot(meeting: Meeting, db: Session) -> None:
    """
    Demande à Vexa si le bot est entré, et met la réunion à jour le cas échéant.

    Vexa n'envoie PAS l'événement "meeting.started" — ses journaux de livraison
    le marquent "suppressed", seul "meeting.completed" part réellement. Sans
    cette interrogation, la page vidéo affichait « en attente que le bot
    rejoigne » indéfiniment alors que le bot était déjà dans la réunion.

    N'agit que sur une réunion vidéo encore en attente : dès qu'elle passe en
    "recording", plus aucun appel n'est fait.
    """
    if meeting.status != "pending" or not meeting.vexa_meeting_id:
        return

    maintenant = time.monotonic()
    if maintenant - _derniere_verif_bot.get(meeting.id, 0.0) < INTERVALLE_VERIF_BOT_SEC:
        return
    _derniere_verif_bot[meeting.id] = maintenant

    try:
        bot = await vexa_service.get_bot_status(meeting.vexa_meeting_id)
    except vexa_service.VexaError:
        # Vexa injoignable : on laisse le statut tel quel plutôt que de faire
        # échouer le sondage du navigateur.
        return

    if bot and bot.get("status") in ("active", "recording"):
        meeting.status = "recording"
        meeting.started_at = meeting.started_at or datetime.utcnow()
        db.commit()
        db.refresh(meeting)
        _derniere_verif_bot.pop(meeting.id, None)


# ─── Vidéo — faire quitter la réunion au bot ───
@router.post("/meetings/{meeting_id}/stop", response_model=MeetingResponse)
async def stop_video_meeting(
    meeting_id:   UUID,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    """
    Retire le bot de la visioconférence.

    Sans cette route, l'utilisateur n'avait aucun moyen d'arrêter un
    enregistrement depuis l'interface : quitter le Meat soi-même laisse le bot
    seul dans la salle. C'est aussi ce départ qui déclenche "meeting.completed"
    côté Vexa, donc la récupération de l'audio et la transcription.
    """
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

    if meeting.mode != "video" or not meeting.vexa_native_id:
        raise HTTPException(
            status_code=400,
            detail="Cette réunion n'a pas de bot à arrêter"
        )

    if meeting.status in ("processing", "completed", "failed"):
        # Déjà terminée : on ne renvoie pas d'erreur, l'utilisateur a peut-être
        # cliqué deux fois ou le webhook est arrivé entre-temps.
        return meeting

    try:
        await vexa_service.stop_bot(
            platform          = meeting.vexa_platform or "google_meet",
            native_meeting_id = meeting.vexa_native_id,
        )
    except vexa_service.VexaError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Le statut définitif viendra du webhook "meeting.completed", qui porte les
    # horodatages réels et l'identifiant de l'enregistrement. On se contente ici
    # de refléter la demande pour que l'interface réagisse tout de suite.
    meeting.status   = "processing"
    meeting.ended_at = meeting.ended_at or datetime.utcnow()
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/meetings/{meeting_id}/status", response_model=MeetingStatusResponse)
async def get_meeting_status(
    meeting_id:   UUID,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé en base")

    meeting = db.query(Meeting).filter(
        Meeting.id       == meeting_id,
        Meeting.owner_id == user.id,
        Meeting.deleted_at == None
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion non trouvée")

    # Vexa n'émet pas "meeting.started" : c'est ici qu'on constate l'entrée du
    # bot, au fil des sondages du navigateur.
    await _synchroniser_etat_bot(meeting, db)

    return meeting