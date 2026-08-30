"""
Tests du webhook Vexa.

La version précédente de ce fichier ne testait rien : elle modifiait le modèle
à la main (meeting.status = "recording") puis vérifiait que la modification
avait eu lieu, sans jamais appeler l'endpoint. C'est la raison pour laquelle un
module entièrement inopérant — mauvais noms d'événements, mauvais type
d'identifiant — a pu rester en place sans qu'aucun test n'échoue.

Les charges utiles ci-dessous reprennent la forme réelle observée le
30 août 2026 sur le compte de production (event_type, meeting_id entier).
"""

import uuid
import pytest
from unittest.mock import patch

from app.models.meeting import Meeting
from app.core.database import settings


SECRET = "secret-de-test-vexa"
VEXA_MEETING_ID = 27246

WEBHOOK_URL = "/api/v1/webhooks/vexa"


@pytest.fixture
def vexa_meeting(db, test_user):
    """Réunion vidéo reliée à une réunion Vexa, comme après spawn_bot()."""
    meeting = Meeting(
        id=uuid.uuid4(),
        owner_id=test_user.id,
        title="Réunion vidéo test",
        mode="video",
        status="pending",
        meeting_link="https://meet.google.com/ora-scow-epu",
        vexa_meeting_id=VEXA_MEETING_ID,
        vexa_platform="google_meet",
        vexa_native_id="ora-scow-epu",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


class _SessionSansFermeture:
    """
    Enveloppe la session de test pour neutraliser close().

    Le webhook ouvre et referme sa propre session ; sur la session partagée du
    test, cette fermeture détacherait les objets et rendrait tout db.refresh()
    impossible côté assertions.
    """

    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def close(self):
        pass


@pytest.fixture
def webhook_client(client, db, monkeypatch):
    """
    Le webhook ouvre sa propre session (SessionLocal) : la surcharge de get_db
    du client de test ne s'y applique pas, il faut la rediriger explicitement.
    """
    monkeypatch.setattr(settings, "VEXA_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(
        "app.api.v1.webhooks.SessionLocal", lambda: _SessionSansFermeture(db)
    )
    return client


def _headers(secret=SECRET):
    return {"X-Vexa-Secret": secret}


# ─── Authentification ───

def test_secret_absent_rejete(webhook_client):
    res = webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.started", "meeting_id": VEXA_MEETING_ID},
    )
    assert res.status_code == 401


def test_secret_invalide_rejete(webhook_client):
    res = webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.started", "meeting_id": VEXA_MEETING_ID},
        headers=_headers("mauvais-secret"),
    )
    assert res.status_code == 401


def test_secret_accepte_dans_un_autre_en_tete(webhook_client, vexa_meeting, db):
    """Vexa ne documente pas le nom de l'en-tête : plusieurs sont acceptés."""
    res = webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.started", "meeting_id": VEXA_MEETING_ID},
        headers={"X-Webhook-Secret": SECRET},
    )
    assert res.status_code == 200


# ─── Transitions d'état ───

def test_meeting_started_passe_en_recording(webhook_client, vexa_meeting, db):
    res = webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.started", "meeting_id": VEXA_MEETING_ID},
        headers=_headers(),
    )
    assert res.status_code == 200

    db.refresh(vexa_meeting)
    assert vexa_meeting.status == "recording"
    assert vexa_meeting.started_at is not None


def test_meeting_completed_passe_en_processing_et_declenche_ingestion(
    webhook_client, vexa_meeting, db
):
    vexa_meeting.status = "recording"
    db.commit()

    with patch("app.api.v1.webhooks.ingest_vexa_recording") as ingest:
        res = webhook_client.post(
            WEBHOOK_URL,
            json={"event_type": "meeting.completed", "meeting_id": VEXA_MEETING_ID},
            headers=_headers(),
        )

    assert res.status_code == 200
    db.refresh(vexa_meeting)
    assert vexa_meeting.status == "processing"
    assert vexa_meeting.ended_at is not None
    # C'est le chaînon qui manquait : sans lui la réunion restait en processing
    ingest.assert_called_once()


def test_status_change_actif_vaut_demarrage(webhook_client, vexa_meeting, db):
    """Vexa émet aussi des meeting.status_change portant le statut du bot."""
    res = webhook_client.post(
        WEBHOOK_URL,
        json={
            "event_type": "meeting.status_change",
            "meeting_id": VEXA_MEETING_ID,
            "status": "active",
        },
        headers=_headers(),
    )
    assert res.status_code == 200

    db.refresh(vexa_meeting)
    assert vexa_meeting.status == "recording"


def test_echec_du_bot_passe_en_failed(webhook_client, vexa_meeting, db):
    res = webhook_client.post(
        WEBHOOK_URL,
        json={
            "event_type": "meeting.status_change",
            "meeting_id": VEXA_MEETING_ID,
            "status": "failed",
        },
        headers=_headers(),
    )
    assert res.status_code == 200

    db.refresh(vexa_meeting)
    assert vexa_meeting.status == "failed"


# ─── Idempotence et robustesse ───

def test_meeting_started_deux_fois_ne_change_pas_started_at(
    webhook_client, vexa_meeting, db
):
    payload = {"event_type": "meeting.started", "meeting_id": VEXA_MEETING_ID}
    webhook_client.post(WEBHOOK_URL, json=payload, headers=_headers())
    db.refresh(vexa_meeting)
    premier = vexa_meeting.started_at

    webhook_client.post(WEBHOOK_URL, json=payload, headers=_headers())
    db.refresh(vexa_meeting)
    assert vexa_meeting.started_at == premier


def test_statut_ne_recule_jamais(webhook_client, vexa_meeting, db):
    """Un meeting.started arrivant après la fin ne doit pas rouvrir la réunion."""
    vexa_meeting.status = "completed"
    db.commit()

    webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.started", "meeting_id": VEXA_MEETING_ID},
        headers=_headers(),
    )
    db.refresh(vexa_meeting)
    assert vexa_meeting.status == "completed"


def test_reunion_inconnue_acquittee_sans_erreur(webhook_client, db):
    """Le compte Vexa peut servir hors Auris : on acquitte pour éviter les réémissions."""
    res = webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.completed", "meeting_id": 999999},
        headers=_headers(),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"


def test_reunion_supprimee_ignoree(webhook_client, vexa_meeting, db):
    from datetime import datetime
    vexa_meeting.deleted_at = datetime.utcnow()
    db.commit()

    res = webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.started", "meeting_id": VEXA_MEETING_ID},
        headers=_headers(),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"


def test_charge_utile_sans_identifiant_ignoree(webhook_client):
    res = webhook_client.post(
        WEBHOOK_URL,
        json={"event_type": "meeting.started"},
        headers=_headers(),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"


def test_identifiant_imbrique_dans_data(webhook_client, vexa_meeting, db):
    """Certaines charges utiles Vexa imbriquent les champs sous "data"."""
    res = webhook_client.post(
        WEBHOOK_URL,
        json={
            "event_type": "meeting.status_change",
            "data": {"meeting_id": VEXA_MEETING_ID, "status": "active"},
        },
        headers=_headers(),
    )
    assert res.status_code == 200

    db.refresh(vexa_meeting)
    assert vexa_meeting.status == "recording"


# ─── Charge utile réelle ───
#
# Reproduite depuis un événement capté en production le 30 août 2026. C'est
# elle qui compte : les tests plus haut valident la tolérance aux formes
# plates, celui-ci valide la structure que Vexa envoie vraiment.

def _charge_utile_reelle(vexa_id=VEXA_MEETING_ID, recording_id=320588629711):
    return {
        "event_id": "evt_1b97f7cf8bcb11a0981591b109c61acd",
        "event_type": "meeting.completed",
        "api_version": "2026-03-01",
        "created_at": "2026-08-30T13:24:38.832955Z",
        "data": {
            "meeting": {
                "id": vexa_id,
                "user_id": 3089,
                "platform": "google_meet",
                "native_meeting_id": "bug-wriq-yfn",
                "status": "completed",
                "completion_reason": "stopped",
                "start_time": "2026-08-30T13:22:56.750914Z",
                "end_time": "2026-08-30T13:24:38.667351Z",
                "data": {
                    "recordings": [
                        {
                            "id": recording_id,
                            "source": "bot",
                            "status": "completed",
                            "meeting_id": vexa_id,
                            "media_files": [
                                {"id": 330255740132, "type": "audio", "format": "webm"}
                            ],
                            "playback_url": {
                                "audio": f"/recordings/{recording_id}/master?type=audio",
                                "video": None,
                            },
                        }
                    ],
                    "recording_enabled": True,
                    "segments_captured": 6,
                },
            }
        },
    }


def test_charge_utile_reelle_identifie_la_reunion(webhook_client, vexa_meeting, db):
    """
    L'identifiant est sous data.meeting.id, pas à la racine.

    C'est précisément ce que la première version ne savait pas lire : elle
    répondait 200 avec "ignored" et la réunion restait bloquée.
    """
    with patch("app.api.v1.webhooks.ingest_vexa_recording"):
        res = webhook_client.post(
            WEBHOOK_URL, json=_charge_utile_reelle(), headers=_headers()
        )

    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    db.refresh(vexa_meeting)
    assert vexa_meeting.status == "processing"


def test_charge_utile_reelle_transmet_l_identifiant_d_enregistrement(
    webhook_client, vexa_meeting, db
):
    """L'événement porte déjà le recording_id : inutile d'interroger /recordings."""
    with patch("app.api.v1.webhooks.ingest_vexa_recording") as ingest:
        webhook_client.post(
            WEBHOOK_URL, json=_charge_utile_reelle(), headers=_headers()
        )

    ingest.assert_called_once()
    assert ingest.call_args.kwargs["recording_id"] == 320588629711
    assert ingest.call_args.kwargs["vexa_meeting_id"] == VEXA_MEETING_ID


def test_charge_utile_reelle_renseigne_les_horodatages_et_la_duree(
    webhook_client, vexa_meeting, db
):
    """start_time / end_time viennent de Vexa ; duration_sec s'en déduit."""
    with patch("app.api.v1.webhooks.ingest_vexa_recording"):
        webhook_client.post(
            WEBHOOK_URL, json=_charge_utile_reelle(), headers=_headers()
        )

    db.refresh(vexa_meeting)
    assert vexa_meeting.started_at is not None
    assert vexa_meeting.ended_at is not None
    # 13:22:56.75 → 13:24:38.66, soit 101 secondes
    assert vexa_meeting.duration_sec == 101


def test_charge_utile_reelle_d_une_autre_reunion_ignoree(webhook_client, db):
    res = webhook_client.post(
        WEBHOOK_URL, json=_charge_utile_reelle(vexa_id=999999), headers=_headers()
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"


def test_sans_enregistrement_dans_la_charge_utile_on_retombe_sur_la_recherche(
    webhook_client, vexa_meeting, db
):
    """Si l'événement ne porte pas d'enregistrement, recording_id est None."""
    charge = _charge_utile_reelle()
    charge["data"]["meeting"]["data"]["recordings"] = []

    with patch("app.api.v1.webhooks.ingest_vexa_recording") as ingest:
        webhook_client.post(WEBHOOK_URL, json=charge, headers=_headers())

    assert ingest.call_args.kwargs["recording_id"] is None


# ─── Enchaînement avec le bouton « Quitter la réunion » ───
#
# La route POST /meetings/{id}/stop passe la réunion en "processing" pour que
# l'interface réagisse dès le clic. Le webhook meeting.completed qui suit doit
# donc accepter cet état : le refuser revenait à ne jamais récupérer l'audio
# dès lors que l'utilisateur arrêtait le bot depuis l'application — la page
# restait sur « transcription en cours » indéfiniment.

def test_completed_apres_arret_manuel_declenche_bien_l_ingestion(
    webhook_client, vexa_meeting, db
):
    vexa_meeting.status = "processing"   # état posé par la route /stop
    db.commit()

    with patch("app.api.v1.webhooks.ingest_vexa_recording") as ingest:
        res = webhook_client.post(
            WEBHOOK_URL, json=_charge_utile_reelle(), headers=_headers()
        )

    assert res.status_code == 200
    ingest.assert_called_once()


def test_reemission_du_meme_evenement_n_ingere_pas_deux_fois(
    webhook_client, vexa_meeting, db, test_audio_file
):
    """Une transcription existante vaut « déjà traitée »."""
    from app.models.transcription import Transcription

    db.add(Transcription(
        id=uuid.uuid4(),
        meeting_id=vexa_meeting.id,
        audio_file_id=test_audio_file.id,
        status="completed",
    ))
    vexa_meeting.status = "processing"
    db.commit()

    with patch("app.api.v1.webhooks.ingest_vexa_recording") as ingest:
        webhook_client.post(
            WEBHOOK_URL, json=_charge_utile_reelle(), headers=_headers()
        )

    ingest.assert_not_called()
