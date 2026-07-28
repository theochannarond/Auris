import httpx
from app.core.database import settings


async def spawn_bot(meeting_id: str, meeting_link: str) -> dict:
    """
    Envoie un bot Vexa dans la réunion vidéo.
    Retourne le statut de la réponse Vexa.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.vexa.ai/v1/bots",
                headers={
                    "Authorization": f"Bearer {settings.VEXA_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "meeting_url": meeting_link,
                    "meeting_id":  meeting_id,
                    "bot_name":    "Auris Assistant"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        # On log l'erreur mais on ne bloque pas la création de la réunion
        print(f"Vexa bot spawn error: {e}")
        return {"status": "error", "detail": str(e)}
