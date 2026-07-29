from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingResponse
from uuid import UUID
import uuid as uuid_lib
from app.services.storage import upload_audio_file

router = APIRouter(prefix="/api/v1", tags=["meetings"])

@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé en base"
        )

    meeting = Meeting(owner_id=user.id, title=payload.title)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting

@router.post("/meetings/{meeting_id}/audio", response_model=MeetingResponse)
async def upload_meeting_audio(
    meeting_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.keycloak_id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé en base")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.owner_id == user.id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réunion non trouvée")

    content = await file.read()
    object_key = f"{meeting_id}/{uuid_lib.uuid4()}-{file.filename}"
    upload_audio_file(content, object_key, file.content_type)

    meeting.audio_object_key = object_key
    db.commit()
    db.refresh(meeting)
    return meeting