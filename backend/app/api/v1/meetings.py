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
from app.services.storage_service import upload_audio_file, delete_audio_file
from app.services.meeting_deletion_service import soft_delete_meeting
from typing import List
from uuid import UUID
import uuid as uuid_lib


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
    await upload_audio_file(content, object_key, file.content_type)

    # La clé OVH est tracée dans audio_files — c'est elle que la transcription ira chercher
    audio_file = AudioFile(
        meeting_id      = meeting.id,
        storage_key     = object_key,
        file_size_bytes = len(content),
        mime_type       = file.content_type or "audio/wav"
    )
    db.add(audio_file)
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

    if meeting_data.meeting_link:
        await vexa_service.spawn_bot(
            meeting_id   = str(meeting.id),
            meeting_link = meeting_data.meeting_link
        )

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

    return meeting