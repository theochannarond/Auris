import httpx
import time
from typing import Optional
from app.core.database import settings


class VoxtralTranscriptionError(Exception):
    """
    Erreur levée quand Voxtral ne renvoie pas de transcription exploitable.
    Porte le temps de traitement déjà écoulé pour qu'il soit tout de même stocké.
    """
    def __init__(self, message: str, processing_ms: Optional[int] = None):
        super().__init__(message)
        self.processing_ms = processing_ms


async def transcribe_audio(
    audio_content: bytes,
    filename:      str = "audio.wav",
    mime_type:     str = "audio/wav",
    language:      Optional[str] = None
) -> dict:
    """
    Envoie un fichier audio à Voxtral Mini V2 (API Mistral) et retourne sa transcription.

    Retourne un dict : {"text", "language", "model", "processing_ms"}.
    Lève VoxtralTranscriptionError en cas d'échec — l'appelant décide quoi
    en faire (ici : passer la transcription en status "failed").
    """
    if not settings.MISTRAL_API_KEY:
        raise VoxtralTranscriptionError("Clé API Mistral manquante (MISTRAL_API_KEY)")

    if not audio_content:
        raise VoxtralTranscriptionError("Fichier audio vide — rien à transcrire")

    data = {"model": settings.VOXTRAL_MODEL}
    if language:
        data["language"] = language

    started_at = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.MISTRAL_API_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                files={"file": (filename, audio_content, mime_type)},
                data=data,
                timeout=settings.VOXTRAL_TIMEOUT_SEC
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as e:
        processing_ms = int((time.perf_counter() - started_at) * 1000)
        raise VoxtralTranscriptionError(
            f"Voxtral a répondu {e.response.status_code} : {e.response.text[:200]}",
            processing_ms
        ) from e
    except httpx.TimeoutException as e:
        processing_ms = int((time.perf_counter() - started_at) * 1000)
        raise VoxtralTranscriptionError(
            f"Timeout Voxtral après {settings.VOXTRAL_TIMEOUT_SEC}s",
            processing_ms
        ) from e
    except httpx.HTTPError as e:
        processing_ms = int((time.perf_counter() - started_at) * 1000)
        raise VoxtralTranscriptionError(f"Erreur réseau vers Voxtral : {e}", processing_ms) from e

    processing_ms = int((time.perf_counter() - started_at) * 1000)

    text = (payload.get("text") or "").strip()
    if not text:
        raise VoxtralTranscriptionError("Voxtral a renvoyé une transcription vide", processing_ms)

    return {
        "text":          text,
        "language":      payload.get("language") or language,
        "model":         payload.get("model") or settings.VOXTRAL_MODEL,
        "processing_ms": processing_ms
    }
