import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.services import voxtral_service
from app.services.voxtral_service import transcribe_audio, VoxtralTranscriptionError

AUDIO = b"fake-wav-bytes"


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    """Voxtral refuse de partir sans clé — on en fournit une pour tous les tests."""
    monkeypatch.setattr(voxtral_service.settings, "MISTRAL_API_KEY", "test-key")


def mock_httpx(response=None, raises=None):
    """
    Remplace httpx.AsyncClient par un double.
    Retourne le patcher et le mock du client, pour inspecter l'appel POST.
    """
    client = AsyncMock()
    client.post = AsyncMock(return_value=response, side_effect=raises)

    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)

    return patch.object(voxtral_service.httpx, "AsyncClient", return_value=context), client


def ok_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def error_response(status_code, text="Erreur"):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "erreur", request=MagicMock(), response=response
    )
    return response


# ─── Cas nominal ───

@pytest.mark.asyncio
async def test_transcription_reussie_retourne_le_texte():
    """Une réponse Voxtral valide donne le texte, la langue et le modèle"""
    patcher, _ = mock_httpx(ok_response({
        "text":     "Bonjour, ceci est le compte rendu de la réunion.",
        "language": "fr",
        "model":    "voxtral-mini-latest"
    }))
    with patcher:
        result = await transcribe_audio(AUDIO)

    assert result["text"]     == "Bonjour, ceci est le compte rendu de la réunion."
    assert result["language"] == "fr"
    assert result["model"]    == "voxtral-mini-latest"


@pytest.mark.asyncio
async def test_processing_ms_est_mesure():
    """Le temps de traitement est renvoyé, en entier et positif"""
    patcher, _ = mock_httpx(ok_response({"text": "Texte transcrit", "language": "fr"}))
    with patcher:
        result = await transcribe_audio(AUDIO)

    assert isinstance(result["processing_ms"], int)
    assert result["processing_ms"] >= 0


@pytest.mark.asyncio
async def test_texte_nettoye_des_espaces():
    """Les espaces et retours à la ligne autour du texte sont supprimés"""
    patcher, _ = mock_httpx(ok_response({"text": "  \n Texte transcrit \n "}))
    with patcher:
        result = await transcribe_audio(AUDIO)

    assert result["text"] == "Texte transcrit"


@pytest.mark.asyncio
async def test_modele_et_fichier_envoyes_a_voxtral():
    """Le modèle configuré et le fichier audio sont bien transmis dans la requête"""
    patcher, client = mock_httpx(ok_response({"text": "Texte transcrit"}))
    with patcher:
        await transcribe_audio(AUDIO, filename="reunion.wav", mime_type="audio/wav")

    kwargs = client.post.call_args.kwargs
    assert kwargs["data"]["model"] == voxtral_service.settings.VOXTRAL_MODEL
    assert kwargs["files"]["file"] == ("reunion.wav", AUDIO, "audio/wav")
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_langue_transmise_si_precisee():
    """La langue est passée à Voxtral quand l'appelant la connaît"""
    patcher, client = mock_httpx(ok_response({"text": "Texte transcrit"}))
    with patcher:
        await transcribe_audio(AUDIO, language="fr")

    assert client.post.call_args.kwargs["data"]["language"] == "fr"


@pytest.mark.asyncio
async def test_langue_absente_si_non_precisee():
    """Sans langue fournie, on laisse Voxtral la détecter"""
    patcher, client = mock_httpx(ok_response({"text": "Texte transcrit"}))
    with patcher:
        await transcribe_audio(AUDIO)

    assert "language" not in client.post.call_args.kwargs["data"]


# ─── Cas d'erreur ───

@pytest.mark.asyncio
async def test_cle_api_manquante(monkeypatch):
    """Sans clé API, on échoue avant tout appel réseau"""
    monkeypatch.setattr(voxtral_service.settings, "MISTRAL_API_KEY", "")

    with pytest.raises(VoxtralTranscriptionError, match="Clé API Mistral manquante"):
        await transcribe_audio(AUDIO)


@pytest.mark.asyncio
async def test_audio_vide_refuse():
    """Un fichier audio vide ne part pas chez Voxtral"""
    with pytest.raises(VoxtralTranscriptionError, match="Fichier audio vide"):
        await transcribe_audio(b"")


@pytest.mark.asyncio
async def test_erreur_http_voxtral():
    """Un 500 Voxtral lève VoxtralTranscriptionError avec le code dans le message"""
    patcher, _ = mock_httpx(error_response(500, "Internal Server Error"))
    with patcher:
        with pytest.raises(VoxtralTranscriptionError, match="500"):
            await transcribe_audio(AUDIO)


@pytest.mark.asyncio
async def test_erreur_http_porte_le_processing_ms():
    """Même en échec, le temps écoulé est conservé pour le benchmark"""
    patcher, _ = mock_httpx(error_response(401, "Unauthorized"))
    with patcher:
        with pytest.raises(VoxtralTranscriptionError) as exc:
            await transcribe_audio(AUDIO)

    assert isinstance(exc.value.processing_ms, int)
    assert exc.value.processing_ms >= 0


@pytest.mark.asyncio
async def test_timeout_voxtral():
    """Un timeout est converti en VoxtralTranscriptionError explicite"""
    patcher, _ = mock_httpx(raises=httpx.TimeoutException("timeout"))
    with patcher:
        with pytest.raises(VoxtralTranscriptionError, match="Timeout"):
            await transcribe_audio(AUDIO)


@pytest.mark.asyncio
async def test_erreur_reseau():
    """Une panne réseau est également remontée proprement"""
    patcher, _ = mock_httpx(raises=httpx.ConnectError("connexion refusée"))
    with patcher:
        with pytest.raises(VoxtralTranscriptionError, match="Erreur réseau"):
            await transcribe_audio(AUDIO)


@pytest.mark.asyncio
async def test_transcription_vide_refusee():
    """Une réponse 200 sans texte est un échec — rien à stocker en base"""
    patcher, _ = mock_httpx(ok_response({"text": "   ", "language": "fr"}))
    with patcher:
        with pytest.raises(VoxtralTranscriptionError, match="transcription vide"):
            await transcribe_audio(AUDIO)
