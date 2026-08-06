import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services import mistral_service
from app.services.mistral_service import generate_summary, MistralSummaryError

TRANSCRIPTION = "On a décidé de livrer le module auth vendredi. Marc s'occupe des tests."

@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(mistral_service.settings, "MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(mistral_service.settings, "MISTRAL_API_URL", "https://api.mistral.ai/v1")

def mock_httpx(payload):
    response = MagicMock()
    response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {"total_tokens": 100}
    }
    response.raise_for_status.return_value = None
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    return patch.object(mistral_service.httpx, "AsyncClient", return_value=context)

# ─── Tests tone ───

@pytest.mark.asyncio
async def test_tone_formal():
    patcher = mock_httpx({"content": "Résumé", "decisions": [], "action_items": [], "tone": "formal", "theme": "Réunion direction"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["tone"] == "formal"

@pytest.mark.asyncio
async def test_tone_informal():
    patcher = mock_httpx({"content": "Résumé", "decisions": [], "action_items": [], "tone": "informal", "theme": "Point équipe"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["tone"] == "informal"

@pytest.mark.asyncio
async def test_tone_technical():
    patcher = mock_httpx({"content": "Résumé", "decisions": [], "action_items": [], "tone": "technical", "theme": "Revue de code"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["tone"] == "technical"

# ─── Tests theme ───

@pytest.mark.asyncio
async def test_theme_present():
    patcher = mock_httpx({"content": "Résumé", "decisions": [], "action_items": [], "tone": "formal", "theme": "Revue de sprint"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["theme"] == "Revue de sprint"

@pytest.mark.asyncio
async def test_theme_non_vide():
    patcher = mock_httpx({"content": "Résumé", "decisions": [], "action_items": [], "tone": "formal", "theme": "Point chantier"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert result["theme"] is not None
    assert len(result["theme"]) > 0

# ─── Tests structure JSON complète ───

@pytest.mark.asyncio
async def test_tous_les_champs_presents():
    patcher = mock_httpx({"content": "Résumé complet", "decisions": ["Décision 1"], "action_items": ["Action 1"], "tone": "formal", "theme": "Réunion client"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert "content" in result
    assert "decisions" in result
    assert "action_items" in result
    assert "tone" in result
    assert "theme" in result
    assert "tokens_used" in result
    assert "processing_ms" in result

@pytest.mark.asyncio
async def test_decisions_liste():
    patcher = mock_httpx({"content": "Résumé", "decisions": ["D1", "D2"], "action_items": [], "tone": "formal", "theme": "Réunion"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert isinstance(result["decisions"], list)
    assert len(result["decisions"]) == 2

@pytest.mark.asyncio
async def test_action_items_liste():
    patcher = mock_httpx({"content": "Résumé", "decisions": [], "action_items": ["Marc : tests", "Sophie : doc"], "tone": "formal", "theme": "Réunion"})
    with patcher:
        result = await generate_summary(TRANSCRIPTION)
    assert isinstance(result["action_items"], list)
    assert len(result["action_items"]) == 2