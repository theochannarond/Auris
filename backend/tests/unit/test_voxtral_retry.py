import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services import voxtral_service
from app.services.voxtral_service import (
    transcribe_audio_with_backoff,
    VoxtralTranscriptionError
)

AUDIO = b"fake-wav-bytes"

@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(voxtral_service.settings, "MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(voxtral_service.settings, "MISTRAL_API_URL", "https://api.mistral.ai/v1")
    monkeypatch.setattr(voxtral_service.settings, "MAX_RETRY_COUNT", 3)


# ─── Cas nominal ───

@pytest.mark.asyncio
async def test_retry_reussit_au_premier_essai():
    """Sans erreur, retourne le résultat avec attempts=1"""
    mock_result = {
        "text": "Bonjour", "language": "fr",
        "model": "voxtral-mini-latest", "processing_ms": 100
    }
    with patch.object(voxtral_service, "transcribe_audio", new=AsyncMock(return_value=mock_result)):
        result = await transcribe_audio_with_backoff(AUDIO)
    assert result["attempts"] == 1
    assert result["text"] == "Bonjour"


@pytest.mark.asyncio
async def test_retry_reussit_apres_deux_echecs_transitoires():
    """Échoue 2 fois puis réussit — attempts=3"""
    mock_result = {
        "text": "Texte transcrit", "language": "fr",
        "model": "voxtral-mini-latest", "processing_ms": 200
    }
    side_effects = [
        VoxtralTranscriptionError("Erreur réseau", processing_ms=50),
        VoxtralTranscriptionError("Timeout", processing_ms=100),
        mock_result
    ]
    with patch.object(voxtral_service, "transcribe_audio", new=AsyncMock(side_effect=side_effects)):
        with patch("asyncio.sleep", new=AsyncMock()):
            result = await transcribe_audio_with_backoff(AUDIO)
    assert result["attempts"] == 3
    assert result["text"] == "Texte transcrit"


@pytest.mark.asyncio
async def test_retry_epuise_tous_les_essais():
    """Échoue à chaque tentative — lève VoxtralTranscriptionError après MAX_RETRY_COUNT+1 essais"""
    error = VoxtralTranscriptionError("Erreur réseau", processing_ms=50)
    with patch.object(voxtral_service, "transcribe_audio", new=AsyncMock(side_effect=error)):
        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(VoxtralTranscriptionError):
                await transcribe_audio_with_backoff(AUDIO, max_retries=3)


@pytest.mark.asyncio
async def test_retry_ne_reessaie_pas_erreur_definitive_cle_api():
    """Erreur 'clé API manquante' — aucun retry, échec immédiat"""
    error = VoxtralTranscriptionError("Clé API Mistral manquante", processing_ms=0)
    mock = AsyncMock(side_effect=error)
    with patch.object(voxtral_service, "transcribe_audio", new=mock):
        with patch("asyncio.sleep", new=AsyncMock()) as sleep_mock:
            with pytest.raises(VoxtralTranscriptionError, match="manquante"):
                await transcribe_audio_with_backoff(AUDIO)
    sleep_mock.assert_not_called()
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_retry_ne_reessaie_pas_audio_vide():
    """Erreur 'audio vide' — aucun retry"""
    error = VoxtralTranscriptionError("Fichier audio vide", processing_ms=0)
    mock = AsyncMock(side_effect=error)
    with patch.object(voxtral_service, "transcribe_audio", new=mock):
        with patch("asyncio.sleep", new=AsyncMock()) as sleep_mock:
            with pytest.raises(VoxtralTranscriptionError, match="vide"):
                await transcribe_audio_with_backoff(AUDIO)
    sleep_mock.assert_not_called()
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_retry_ne_reessaie_pas_transcription_vide():
    """Erreur 'transcription vide' — aucun retry"""
    error = VoxtralTranscriptionError("Voxtral a renvoyé une transcription vide", processing_ms=200)
    mock = AsyncMock(side_effect=error)
    with patch.object(voxtral_service, "transcribe_audio", new=mock):
        with patch("asyncio.sleep", new=AsyncMock()) as sleep_mock:
            with pytest.raises(VoxtralTranscriptionError):
                await transcribe_audio_with_backoff(AUDIO)
    sleep_mock.assert_not_called()
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_retry_custom_max_retries():
    """max_retries=1 — seulement 2 tentatives au total"""
    error = VoxtralTranscriptionError("Erreur réseau", processing_ms=50)
    mock = AsyncMock(side_effect=error)
    with patch.object(voxtral_service, "transcribe_audio", new=mock):
        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(VoxtralTranscriptionError):
                await transcribe_audio_with_backoff(AUDIO, max_retries=1)
    assert mock.call_count == 2


@pytest.mark.asyncio
async def test_backoff_delai_exponentiel():
    """Les délais entre tentatives sont bien 1s, 2s, 4s..."""
    error = VoxtralTranscriptionError("Erreur réseau", processing_ms=50)
    with patch.object(voxtral_service, "transcribe_audio", new=AsyncMock(side_effect=error)):
        with patch("asyncio.sleep", new=AsyncMock()) as sleep_mock:
            with pytest.raises(VoxtralTranscriptionError):
                await transcribe_audio_with_backoff(AUDIO, max_retries=3)
    sleep_calls = [call.args[0] for call in sleep_mock.call_args_list]
    assert sleep_calls == [1, 2, 4]