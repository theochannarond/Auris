from unittest.mock import patch, AsyncMock
from app.models.transcription import Transcription


def test_create_summary_without_transcription_returns_404(client):
    """POST /summaries sans transcription complète retourne 404"""
    meeting = client.post("/api/v1/meetings", json={"title": "Réunion sans transcription"})
    meeting_id = meeting.json()["id"]

    response = client.post("/api/v1/summaries", json={"meeting_id": meeting_id})
    assert response.status_code == 404


def test_create_summary_with_transcription_returns_202(client, db, test_transcription):
    """POST /summaries avec une transcription complète retourne 202 Accepted"""
    transcription = db.query(Transcription).filter(
        Transcription.id == test_transcription.id
    ).first()
    transcription.status   = "completed"
    transcription.raw_text = "Bonjour tout le monde, on commence la réunion."
    db.commit()

    with patch("app.api.v1.summaries.run_summary", new_callable=AsyncMock):
        response = client.post("/api/v1/summaries", json={
            "meeting_id": str(test_transcription.meeting_id)
        })
    assert response.status_code == 202
    data = response.json()
    assert "id" in data


def test_create_summary_idempotent(client, db, test_transcription):
    """POST /summaries deux fois retourne le même résumé -- idempotence"""
    t = db.query(Transcription).filter(Transcription.id == test_transcription.id).first()
    t.status   = "completed"
    t.raw_text = "Texte de test pour idempotence."
    db.commit()

    with patch("app.api.v1.summaries.run_summary", new_callable=AsyncMock):
        r1 = client.post("/api/v1/summaries", json={"meeting_id": str(test_transcription.meeting_id)})
        r2 = client.post("/api/v1/summaries", json={"meeting_id": str(test_transcription.meeting_id)})
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["id"] == r2.json()["id"]