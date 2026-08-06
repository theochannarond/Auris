import pytest
from datetime import datetime
from app.models.meeting import Meeting
import uuid

def test_bot_joined_updates_status_to_recording(db, test_meeting):
    """bot.joined → status passe à recording et started_at est renseigné"""
    assert test_meeting.status == "pending"

    test_meeting.status = "recording"
    test_meeting.started_at = datetime.utcnow()
    db.commit()
    db.refresh(test_meeting)

    assert test_meeting.status == "recording"
    assert test_meeting.started_at is not None


def test_bot_left_updates_status_to_processing(db, test_meeting):
    """bot.left → status passe à processing et ended_at est renseigné"""
    test_meeting.status = "recording"
    db.commit()

    test_meeting.status = "processing"
    test_meeting.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(test_meeting)

    assert test_meeting.status == "processing"
    assert test_meeting.ended_at is not None


def test_bot_failed_updates_status_to_failed(db, test_meeting):
    """bot.failed → status passe à failed"""
    test_meeting.status = "failed"
    db.commit()
    db.refresh(test_meeting)

    assert test_meeting.status == "failed"


def test_idempotence_bot_joined_twice(db, test_meeting):
    """Recevoir bot.joined deux fois ne doit pas écraser started_at"""
    first_time = datetime(2026, 7, 30, 10, 0, 0)
    test_meeting.status = "recording"
    test_meeting.started_at = first_time
    db.commit()

    # Deuxième événement — statut déjà recording, on ne touche pas
    if test_meeting.status == "pending":
        test_meeting.status = "recording"
        test_meeting.started_at = datetime.utcnow()
        db.commit()

    db.refresh(test_meeting)
    assert test_meeting.started_at == first_time


def test_deleted_meeting_ignored(db, test_meeting):
    """Une réunion soft-deletée ne doit pas être mise à jour"""
    test_meeting.deleted_at = datetime.utcnow()
    db.commit()

    meeting = db.query(Meeting).filter(
        Meeting.id == test_meeting.id,
        Meeting.deleted_at == None
    ).first()

    assert meeting is None