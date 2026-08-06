import httpx
import time
import json
from typing import Optional
from app.core.database import settings

class MistralSummaryError(Exception):
    """Erreur levée quand Mistral ne renvoie pas un résumé exploitable."""
    def __init__(self, message: str, processing_ms: Optional[int] = None):
        super().__init__(message)
        self.processing_ms = processing_ms

async def generate_summary(transcription_text: str) -> dict:
    """
    Envoie la transcription à Mistral Small 4 et retourne un résumé structuré.
    Retourne un dict : {"content", "decisions", "action_items", "tone", "theme", 
                        "tokens_used", "processing_ms"}.
    Lève MistralSummaryError en cas d'échec.
    """
    if not settings.MISTRAL_API_KEY:
        raise MistralSummaryError("Clé API Mistral manquante (MISTRAL_API_KEY)")

    if not transcription_text or not transcription_text.strip():
        raise MistralSummaryError("Transcription vide — rien à résumer")

    prompt = f"""Tu es un assistant spécialisé dans la rédaction de comptes-rendus de réunion professionnels.

À partir de la transcription suivante, génère un compte-rendu structuré en JSON avec exactement ces champs :
- "content" : résumé complet de la réunion en français (paragraphe narratif)
- "decisions" : liste des décisions prises (liste de strings, vide si aucune)
- "action_items" : liste des actions à réaliser avec responsable si mentionné (liste de strings)
- "tone" : ton de la réunion ("formal", "informal" ou "technical")
- "theme" : thème principal de la réunion (string court, ex: "Revue de sprint", "Réunion client")

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.

TRANSCRIPTION :
{transcription_text}"""

    started_at = time.perf_counter()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.MISTRAL_API_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model":       "mistral-small-latest",
                    "messages":    [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0
            )
            response.raise_for_status()
            payload = response.json()

    except httpx.HTTPStatusError as e:
        processing_ms = int((time.perf_counter() - started_at) * 1000)
        raise MistralSummaryError(
            f"Mistral a répondu {e.response.status_code} : {e.response.text[:200]}",
            processing_ms
        ) from e
    except httpx.TimeoutException as e:
        processing_ms = int((time.perf_counter() - started_at) * 1000)
        raise MistralSummaryError(
            f"Timeout Mistral après 60s",
            processing_ms
        ) from e
    except httpx.HTTPError as e:
        processing_ms = int((time.perf_counter() - started_at) * 1000)
        raise MistralSummaryError(
            f"Erreur réseau vers Mistral : {e}",
            processing_ms
        ) from e

    processing_ms = int((time.perf_counter() - started_at) * 1000)

    try:
        content_str = payload["choices"][0]["message"]["content"]
        result = json.loads(content_str)
    except (KeyError, json.JSONDecodeError) as e:
        raise MistralSummaryError(
            f"Réponse Mistral invalide : {e}",
            processing_ms
        )

    if not result.get("content"):
        raise MistralSummaryError("Mistral a renvoyé un résumé vide", processing_ms)

    return {
        "content":      result.get("content", ""),
        "decisions":    result.get("decisions", []),
        "action_items": result.get("action_items", []),
        "tone":         result.get("tone"),
        "theme":        result.get("theme"),
        "tokens_used":  payload.get("usage", {}).get("total_tokens"),
        "processing_ms": processing_ms
    }