from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.api.v1.auth import require_consent
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingResponse
from app.services import vexa_service

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


@router.post(
    "/video",
    status_code=status.HTTP_201_CREATED,
    response_model=MeetingResponse
)
async def create_video_meeting(
    meeting_data: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    consent: dict = Depends(require_consent)
):
    meeting = Meeting(
        owner_id=current_user["id"],
        title=meeting_data.title,
        mode="video",
        status="pending",
        meeting_link=meeting_data.meeting_link
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    if meeting_data.meeting_link:
        vexa_response = await vexa_service.spawn_bot(
            meeting_id=str(meeting.id),
            meeting_link=meeting_data.meeting_link
        )
        if vexa_response.get("status") != "error":
            meeting.status = "recording"
            db.commit()
            db.refresh(meeting)

    return meeting
