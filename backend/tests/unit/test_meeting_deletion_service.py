import pytest
from datetime import datetime
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.services.meeting_deletion_service import soft_delete_meeting
import uuid


@pytest.fixture
def test_summary(db, test_meeting, test_transcription):
    """Résumé rattaché à la réunion de test — pas de fixture pour ça dans conftest."""
    summary = Summary(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        transcription_id=test_transcription.id,
        content="Compte rendu de test"
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def test_soft_delete_sets_deleted_at(db, test_meeting):
    """La suppression pose une date sans effacer la ligne (RGPD Art.17)"""
    assert test_meeting.deleted_at is None

    soft_delete_meeting(db, test_meeting)

    # La ligne existe toujours en base, elle est seulement marquée
    stored = db.query(Meeting).filter(Meeting.id == test_meeting.id).first()
    assert stored is not None
    assert stored.deleted_at is not None


def test_soft_delete_propagates_to_children(db, test_meeting, test_audio_file, test_transcription, test_summary):
    """La suppression est propagée aux audio_files, transcriptions et summaries"""
    soft_delete_meeting(db, test_meeting)

    audio         = db.query(AudioFile).filter(AudioFile.id == test_audio_file.id).first()
    transcription = db.query(Transcription).filter(Transcription.id == test_transcription.id).first()
    summary       = db.query(Summary).filter(Summary.id == test_summary.id).first()

    assert audio.deleted_at         is not None
    assert transcription.deleted_at is not None
    assert summary.deleted_at       is not None


def test_all_rows_share_the_same_timestamp(db, test_meeting, test_audio_file, test_transcription, test_summary):
    """Réunion et données filles portent la même date : la conservation expire d'un bloc"""
    soft_delete_meeting(db, test_meeting)

    meeting       = db.query(Meeting).filter(Meeting.id == test_meeting.id).first()
    audio         = db.query(AudioFile).filter(AudioFile.id == test_audio_file.id).first()
    transcription = db.query(Transcription).filter(Transcription.id == test_transcription.id).first()
    summary       = db.query(Summary).filter(Summary.id == test_summary.id).first()

    assert audio.deleted_at         == meeting.deleted_at
    assert transcription.deleted_at == meeting.deleted_at
    assert summary.deleted_at       == meeting.deleted_at


def test_soft_delete_is_idempotent(db, test_meeting):
    """Un second appel ne redémarre pas le délai de conservation"""
    first_deletion = datetime(2026, 1, 15, 9, 30, 0)
    test_meeting.deleted_at = first_deletion
    db.commit()

    soft_delete_meeting(db, test_meeting)

    stored = db.query(Meeting).filter(Meeting.id == test_meeting.id).first()
    assert stored.deleted_at == first_deletion


def test_deleted_meeting_no_longer_listed(db, test_meeting, test_user):
    """Le filtre du dashboard ne renvoie plus la réunion supprimée"""
    soft_delete_meeting(db, test_meeting)

    # Requête identique à celle de GET /api/v1/meetings
    listed = db.query(Meeting).filter(
        Meeting.owner_id   == test_user.id,
        Meeting.deleted_at == None
    ).all()

    assert listed == []


def test_other_meetings_are_untouched(db, test_user, test_meeting, test_audio_file):
    """La cascade est bornée à la réunion visée, pas à toute la table"""
    other_meeting = Meeting(
        id=uuid.uuid4(),
        owner_id=test_user.id,
        title="Réunion à conserver",
        mode="dictaphone",
        status="completed"
    )
    db.add(other_meeting)
    db.commit()

    other_audio = AudioFile(
        id=uuid.uuid4(),
        meeting_id=other_meeting.id,
        storage_key=f"{other_meeting.id}/recording.wav",
        file_size_bytes=2048,
        mime_type="audio/wav"
    )
    db.add(other_audio)
    db.commit()

    soft_delete_meeting(db, test_meeting)

    # Sans le filtre meeting_id dans la cascade, cet audio serait marqué lui aussi
    survivor       = db.query(Meeting).filter(Meeting.id == other_meeting.id).first()
    survivor_audio = db.query(AudioFile).filter(AudioFile.id == other_audio.id).first()

    assert survivor.deleted_at       is None
    assert survivor_audio.deleted_at is None
