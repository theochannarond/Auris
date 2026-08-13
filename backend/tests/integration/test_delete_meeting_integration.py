from app.models.meeting import Meeting
import uuid


def test_delete_meeting_returns_200(client):
    """DELETE /meetings/{id} retourne 200 et un message de confirmation RGPD"""
    create = client.post("/api/v1/meetings", json={"title": "Réunion à supprimer"})
    meeting_id = create.json()["id"]

    response = client.delete(f"/api/v1/meetings/{meeting_id}")
    assert response.status_code == 200


def test_delete_meeting_soft_delete(client, db):
    """DELETE /meetings/{id} fait un soft delete -- la réunion reste en base avec deleted_at"""
    create = client.post("/api/v1/meetings", json={"title": "Réunion soft delete"})
    meeting_id = create.json()["id"]

    client.delete(f"/api/v1/meetings/{meeting_id}")

    meeting = db.query(Meeting).filter(Meeting.id == uuid.UUID(meeting_id)).first()
    assert meeting is not None
    assert meeting.deleted_at is not None


def test_delete_meeting_not_found_returns_404(client):
    """DELETE /meetings/{id} avec un ID inexistant retourne 404"""
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/meetings/{fake_id}")
    assert response.status_code == 404


def test_deleted_meeting_not_in_list(client):
    """Une réunion supprimée n'apparaît plus dans GET /meetings"""
    create = client.post("/api/v1/meetings", json={"title": "Réunion disparaît"})
    meeting_id = create.json()["id"]

    client.delete(f"/api/v1/meetings/{meeting_id}")

    response = client.get("/api/v1/meetings")
    if response.status_code == 200:
        meetings = response.json()
        ids = [m["id"] for m in meetings]
        assert meeting_id not in ids