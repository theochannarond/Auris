from unittest.mock import patch, AsyncMock

def test_create_transcription_without_audio_returns_404(client):
    """POST /transcriptions sans fichier audio uploadé retourne 404"""
    meeting = client.post("/api/v1/meetings", json={"title": "Réunion sans audio"})
    meeting_id = meeting.json()["id"]

    response = client.post("/api/v1/transcriptions", json={
        "meeting_id": meeting_id
    })
    assert response.status_code == 404


def test_create_transcription_with_audio_returns_202(client, test_meeting, test_audio_file):
    """POST /transcriptions avec un fichier audio existant retourne 202 Accepted"""
    with patch("app.api.v1.transcriptions.run_transcription", new_callable=AsyncMock):
        response = client.post("/api/v1/transcriptions", json={
            "meeting_id": str(test_meeting.id)
        })
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "id" in data


def test_create_transcription_idempotent(client, test_meeting, test_audio_file):
    """POST /transcriptions deux fois retourne la même transcription — idempotence"""
    with patch("app.api.v1.transcriptions.run_transcription", new_callable=AsyncMock):
        r1 = client.post("/api/v1/transcriptions", json={"meeting_id": str(test_meeting.id)})
        r2 = client.post("/api/v1/transcriptions", json={"meeting_id": str(test_meeting.id)})
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["id"] == r2.json()["id"]


def test_get_transcription_status_returns_200(client, test_meeting, test_audio_file):
    """GET /transcriptions/{id}/status retourne le statut en cours"""
    with patch("app.api.v1.transcriptions.run_transcription", new_callable=AsyncMock):
        create = client.post("/api/v1/transcriptions", json={"meeting_id": str(test_meeting.id)})
    transcription_id = create.json()["id"]

    response = client.get(f"/api/v1/transcriptions/{transcription_id}/status")
    assert response.status_code == 200
    assert "status" in response.json()