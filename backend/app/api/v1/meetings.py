from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.api.v1.auth import require_consent
from app.models.user import User
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingStatusUpdate
from app.services import vexa_service
from app.services.storage_service import upload_audio_file
from uuid import UUID
import uuid as uuid_lib


router = APIRouter(prefix="/api/v1", tags=["meetings"])


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

    meeting.audio_object_key = object_key
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