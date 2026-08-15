def test_create_meeting_returns_201(client):
    """POST /meetings avec des données valides retourne 201 et la réunion créée"""
    response = client.post("/api/v1/meetings", json={
        "title": "Réunion équipe"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Réunion équipe"
    assert data["status"] == "pending"
    assert data["mode"] == "dictaphone"
    assert "id" in data
    assert "owner_id" in data


def test_create_meeting_missing_title_returns_422(client):
    """POST /meetings sans title (champ requis) retourne 422 — validation Pydantic"""
    response = client.post("/api/v1/meetings", json={})
    assert response.status_code == 422


def test_create_meeting_response_schema(client):
    """La réponse respecte le schéma MeetingResponse"""
    response = client.post("/api/v1/meetings", json={"title": "Test schema"})
    assert response.status_code == 201
    data = response.json()
    required_fields = ["id", "owner_id", "title", "mode", "status", "created_at", "updated_at"]
    for field in required_fields:
        assert field in data, f"Champ manquant dans la réponse : {field}"


def test_update_meeting_status_returns_200(client):
    """PUT /meetings/{id}/status met à jour le statut correctement"""
    create = client.post("/api/v1/meetings", json={"title": "Réunion status"})
    meeting_id = create.json()["id"]

    response = client.put(f"/api/v1/meetings/{meeting_id}/status", json={
        "status": "processing"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


def test_update_meeting_status_invalid_returns_400(client):
    """PUT /meetings/{id}/status avec un statut invalide retourne 400"""
    create = client.post("/api/v1/meetings", json={"title": "Réunion invalide"})
    meeting_id = create.json()["id"]

    response = client.put(f"/api/v1/meetings/{meeting_id}/status", json={
        "status": "statut_qui_nexiste_pas"
    })
    assert response.status_code == 400