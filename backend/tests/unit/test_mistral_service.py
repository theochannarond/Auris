import pytest
import httpx
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services import mistral_service
from app.services.mistral_service import generate_summary, MistralSummaryError

TRANSCRIPTION = "Bonjour tout le monde. On commence la réunion. On a décidé de livrer le module auth vendredi. Marc s'occupe des tests."

@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(mistral_service.settings, "MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(mistral_service.settings, "MISTRAL_API_URL", "https://api.mistral.ai/v1")

def mock_httpx(response=None, raises=None):
    client = AsyncMock()
    client.post = AsyncMock(return_value=response, side_effect=raises)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    return patch.object(mistral_service.httpx, "AsyncClient", return_value=context), client

def ok_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response

def mistral_payload(content="Résumé de la réunion.", decisions=None, action_items=None, tone="formal", theme="Réunion équipe"):
    return {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "content":      content,
                    "decisions":    decisions or ["Livrer le module auth vendredi"],
                    "action_items": action_items or ["Marc : écrire les tests"],
                    "tone":         tone,
                    "theme":        theme
                })
            }
        }],
        "usage": {"total_tokens": 150}
    }

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
async def test_summary_retourne_content():
    patcher, _ = mock_httpx(ok_response(mistral_payload()))
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["content"] == "Résumé de la réunion."

@pytest.mark.asyncio
async def test_summary_retourne_decisions():
    patcher, _ = mock_httpx(ok_response(mistral_payload()))
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert isinstance(result["decisions"], list)
    assert len(result["decisions"]) > 0

@pytest.mark.asyncio
async def test_summary_retourne_action_items():
    patcher, _ = mock_httpx(ok_response(mistral_payload()))
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert isinstance(result["action_items"], list)

@pytest.mark.asyncio
async def test_summary_retourne_tone_et_theme():
    patcher, _ = mock_httpx(ok_response(mistral_payload()))
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["tone"] == "formal"
    assert result["theme"] == "Réunion équipe"

@pytest.mark.asyncio
async def test_tokens_used_retourne():
    patcher, _ = mock_httpx(ok_response(mistral_payload()))
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["tokens_used"] == 150

@pytest.mark.asyncio
async def test_processing_ms_positif():
    patcher, _ = mock_httpx(ok_response(mistral_payload()))
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert isinstance(result["processing_ms"], int)
    assert result["processing_ms"] >= 0

# ─── Cas d'erreur ───

@pytest.mark.asyncio
async def test_cle_api_manquante(monkeypatch):
    monkeypatch.setattr(mistral_service.settings, "MISTRAL_API_KEY", "")
    with pytest.raises(MistralSummaryError, match="Clé API Mistral manquante"):
        await generate_summary(TRANSCRIPTION)

@pytest.mark.asyncio
async def test_transcription_vide_refusee():
    with pytest.raises(MistralSummaryError, match="Transcription vide"):
        await generate_summary("   ")

@pytest.mark.asyncio
async def test_erreur_http_500():
    patcher, _ = mock_httpx(error_response(500))
    with patcher:
        with pytest.raises(MistralSummaryError, match="500"):
            await generate_summary(TRANSCRIPTION)

@pytest.mark.asyncio
async def test_timeout_mistral():
    patcher, _ = mock_httpx(raises=httpx.TimeoutException("timeout"))
    with patcher:
        with pytest.raises(MistralSummaryError, match="Timeout"):
            await generate_summary(TRANSCRIPTION)

@pytest.mark.asyncio
async def test_erreur_reseau():
    patcher, _ = mock_httpx(raises=httpx.ConnectError("connexion refusée"))
    with patcher:
        with pytest.raises(MistralSummaryError, match="Erreur réseau"):
            await generate_summary(TRANSCRIPTION)

@pytest.mark.asyncio
async def test_content_vide_refuse():
    patcher, _ = mock_httpx(ok_response(mistral_payload(content="")))
    with patcher:
        with pytest.raises(MistralSummaryError, match="résumé vide"):
            await generate_summary(TRANSCRIPTION)

@pytest.mark.asyncio
async def test_processing_ms_conserve_en_erreur():
    patcher, _ = mock_httpx(error_response(401))
    with patcher:
        with pytest.raises(MistralSummaryError) as exc:
            await generate_summary(TRANSCRIPTION)
    assert isinstance(exc.value.processing_ms, int)
    assert exc.value.processing_ms >= 0