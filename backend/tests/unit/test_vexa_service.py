"""
Tests du client Vexa — lecture des liens de réunion et corps du POST /bots.

Ces tests portent sur le point qui a fait échouer Zoom en conditions réelles :
Vexa reconstruit l'URL d'entrée à partir de l'identifiant pour Google Meet, mais
refuse un bot Zoom lancé sans "meeting_url", parce que le code d'accès ne vit
que dans le paramètre "?pwd=" du lien. Envoyer le même corps pour toutes les
plateformes ne peut donc pas marcher.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import vexa_service
from app.services.vexa_service import parse_meeting_link, spawn_bot, VexaError

MEET = "https://meet.google.com/hid-ggwt-sft"
ZOOM_INVITATION = "https://us04web.zoom.us/j/79337496630?pwd=SYh4xxYEaSLOn0rXFmIC2Q3W1Got6g.1"
ZOOM_CLIENT_WEB = "https://app.zoom.us/wc/79337496630/start?ref_from=launch&pwd=SYh4xx"


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(vexa_service.settings, "VEXA_API_KEY", "test-key")


def mock_httpx(payload):
    """Remplace httpx.AsyncClient. Retourne le patcher et le double du client."""
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    client = AsyncMock()
    client.post = AsyncMock(return_value=response)

    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)

    return patch.object(vexa_service.httpx, "AsyncClient", return_value=context), client


def corps_envoye(client):
    """Le corps JSON du POST /bots effectivement transmis."""
    return client.post.await_args.kwargs["json"]


# ─── Lecture des liens ───

@pytest.mark.parametrize("lien, attendu", [
    (MEET,            ("google_meet", "hid-ggwt-sft")),
    (ZOOM_INVITATION, ("zoom",        "79337496630")),
    (ZOOM_CLIENT_WEB, ("zoom",        "79337496630")),
    # Le sous-domaine régional varie d'un compte à l'autre et ne doit rien changer.
    ("https://us05web.zoom.us/j/85123456789?pwd=abc", ("zoom", "85123456789")),
    ("https://zoom.us/j/85123456789",                 ("zoom", "85123456789")),
])
def test_liens_reconnus(lien, attendu):
    assert parse_meeting_link(lien) == attendu


@pytest.mark.parametrize("lien", [
    "https://exemple.fr/reunion",
    "pas un lien du tout",
    "",
    None,
])
def test_liens_refuses(lien):
    """Un lien inconnu échoue à la création, pas plus tard par un bot fantôme."""
    with pytest.raises(VexaError):
        parse_meeting_link(lien)


# ─── Corps du POST /bots ───

@pytest.mark.asyncio
async def test_zoom_transmet_le_lien_complet():
    """
    Sans meeting_url, Vexa répond : "unsupported platform 'zoom' without a
    meeting_url". Le lien doit partir intact, code d'accès compris.
    """
    patcher, client = mock_httpx({"id": 27325, "platform": "zoom"})
    with patcher:
        await spawn_bot(ZOOM_INVITATION)

    corps = corps_envoye(client)
    assert corps["platform"]          == "zoom"
    assert corps["native_meeting_id"] == "79337496630"
    assert corps["meeting_url"]       == ZOOM_INVITATION
    assert "pwd=" in corps["meeting_url"]


@pytest.mark.asyncio
async def test_meet_n_envoie_pas_de_lien():
    """
    Google Meet fonctionne sans meeting_url : on ne modifie pas un corps qui
    marche pour la seule plateforme validée de bout en bout.
    """
    patcher, client = mock_httpx({"id": 27252, "platform": "google_meet"})
    with patcher:
        await spawn_bot(MEET)

    corps = corps_envoye(client)
    assert corps["platform"] == "google_meet"
    assert "meeting_url" not in corps


@pytest.mark.asyncio
async def test_identifiant_vexa_retourne():
    """L'identifiant renvoyé relie les webhooks entrants à la réunion Auris."""
    patcher, _ = mock_httpx({"id": 27325, "platform": "zoom"})
    with patcher:
        bot = await spawn_bot(ZOOM_INVITATION)

    assert bot["id"] == 27325


@pytest.mark.asyncio
async def test_refus_de_vexa_remonte_en_erreur():
    """Un refus doit lever, pas être avalé : sinon le bot ne part jamais en silence."""
    response = MagicMock()
    response.status_code = 409
    response.text = '{"detail":"bot already in meeting"}'
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "conflit", request=MagicMock(), response=response
    )

    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)

    with patch.object(vexa_service.httpx, "AsyncClient", return_value=context):
        with pytest.raises(VexaError) as erreur:
            await spawn_bot(ZOOM_INVITATION)

    assert "409" in str(erreur.value)
