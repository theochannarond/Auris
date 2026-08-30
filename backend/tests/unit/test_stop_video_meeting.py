"""
Tests de POST /meetings/{id}/stop — retrait du bot Vexa d'une visioconférence.

Ces tests existent parce que la première version de la route appelait une
fonction absente du module (get_owned_meeting, définie ailleurs) : elle échouait
en NameError à chaque appel, et rien ne l'a signalé avant un essai en production.
Une route non testée est une route qui ne marche pas.
"""

import uuid
import pytest
from unittest.mock import patch, AsyncMock

from app.models.meeting import Meeting
from app.services import vexa_service


@pytest.fixture
def reunion_video(db, test_user):
    meeting = Meeting(
        id=uuid.uuid4(),
        owner_id=test_user.id,
        title="Réunion vidéo en cours",
        mode="video",
        status="recording",
        meeting_link="https://meet.google.com/hid-ggwt-sft",
        vexa_meeting_id=27257,
        vexa_platform="google_meet",
        vexa_native_id="hid-ggwt-sft",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


def test_arret_du_bot_reussi(client, reunion_video, db):
    with patch.object(vexa_service, "stop_bot", new=AsyncMock(return_value={"status": "stopping"})) as stop:
        res = client.post(f"/api/v1/meetings/{reunion_video.id}/stop")

    assert res.status_code == 200
    stop.assert_awaited_once_with(
        platform="google_meet", native_meeting_id="hid-ggwt-sft"
    )

    db.refresh(reunion_video)
    assert reunion_video.status == "processing"
    assert reunion_video.ended_at is not None


def test_reunion_dictaphone_refusee(client, test_meeting, db):
    test_meeting.mode = "dictaphone"
    db.commit()

    res = client.post(f"/api/v1/meetings/{test_meeting.id}/stop")
    assert res.status_code == 400


def test_reunion_sans_bot_refusee(client, test_meeting, db):
    """Réunion vidéo dont le bot n'a jamais démarré : rien à arrêter."""
    test_meeting.mode = "video"
    test_meeting.vexa_native_id = None
    db.commit()

    res = client.post(f"/api/v1/meetings/{test_meeting.id}/stop")
    assert res.status_code == 400


def test_reunion_inconnue(client):
    res = client.post(f"/api/v1/meetings/{uuid.uuid4()}/stop")
    assert res.status_code == 404


def test_double_clic_sans_erreur(client, reunion_video, db):
    """Réunion déjà terminée : on acquitte au lieu de renvoyer une erreur."""
    reunion_video.status = "processing"
    db.commit()

    with patch.object(vexa_service, "stop_bot", new=AsyncMock()) as stop:
        res = client.post(f"/api/v1/meetings/{reunion_video.id}/stop")

    assert res.status_code == 200
    stop.assert_not_awaited()


def test_echec_vexa_remonte_en_502(client, reunion_video, db):
    erreur = vexa_service.VexaError("Vexa injoignable")
    with patch.object(vexa_service, "stop_bot", new=AsyncMock(side_effect=erreur)):
        res = client.post(f"/api/v1/meetings/{reunion_video.id}/stop")

    assert res.status_code == 502
    assert "injoignable" in res.json()["detail"]
