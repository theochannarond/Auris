"""
Client de l'API Vexa — envoi du bot dans une visioconférence et récupération
de l'audio qu'il a capté.

Contrat vérifié le 30 août 2026 contre l'API réelle (compte de production) :

    Base            https://api.cloud.vexa.ai
    Authentification en-tête "X-API-Key" — surtout PAS "Authorization: Bearer",
                    qui renvoie 401 {"detail": "Missing API key"}
    Lancer un bot   POST /bots  {platform, native_meeting_id, bot_name}
                    + meeting_url pour zoom et jitsi (voir plus bas)
    Arrêter un bot  DELETE /bots/{platform}/{native_meeting_id}
    Enregistrements GET /recordings
                    GET /recordings/{id}/master              → media_file_id
                    GET /recordings/{id}/media/{mid}/download → octets WebM

La version précédente visait "https://api.vexa.ai/v1/bots" avec un jeton
Bearer : ce domaine n'existe pas (curl renvoie 000) et l'en-tête est le mauvais.
Le mode vidéo n'a donc jamais pu fonctionner, quelle que soit la clé.

Complément vérifié le 31 août 2026, réunion Zoom réelle : Vexa refuse un bot
Zoom lancé sans "meeting_url" —

    "unsupported platform 'zoom' without a meeting_url —
     use google_meet/teams, or provide meeting_url (required for zoom/jitsi)"

C'est logique : un code Meet ("hid-ggwt-sft") suffit à reconstruire l'URL
d'entrée, alors qu'une réunion Zoom exige en plus un code d'accès, transporté
par le paramètre "?pwd=" du lien d'invitation. L'identifiant numérique seul ne
permet donc pas d'entrer. Le lien complet est déjà stocké dans
Meeting.meeting_link : il n'y a rien de plus à demander à l'utilisateur.
"""

import httpx
import logging
import re
from typing import Optional
from app.core.database import settings

logger = logging.getLogger(__name__)

VEXA_API_URL = "https://api.cloud.vexa.ai"

# Vexa identifie une réunion par une plateforme et un identifiant natif, jamais
# par une URL complète : "https://meet.google.com/ora-scow-epu" doit devenir
# ("google_meet", "ora-scow-epu").
#
# Zoom accepte deux formes : le lien d'invitation "zoom.us/j/<id>?pwd=..." — le
# seul que nous documentions — et l'URL du client web "app.zoom.us/wc/<id>/..."
# qu'affiche la barre d'adresse une fois dans la réunion. La seconde est
# reconnue pour ne pas rejeter un lien qu'un utilisateur aura simplement copié
# depuis son navigateur. Le sous-domaine régional (us04web, us05web…) est sans
# importance : la recherche porte sur une sous-chaîne.
_MEETING_PATTERNS = (
    (re.compile(r"meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})", re.I), "google_meet"),
    (re.compile(r"teams\.(?:microsoft|live)\.com/.*?/(\d{10,})",   re.I), "teams"),
    (re.compile(r"zoom\.us/j/(\d+)",                               re.I), "zoom"),
    (re.compile(r"zoom\.us/wc/(\d+)",                              re.I), "zoom"),
)

# Plateformes pour lesquelles Vexa exige le lien complet en plus de
# l'identifiant : sans lui, la demande est rejetée d'emblée.
PLATFORMS_REQUIRING_URL = frozenset({"zoom", "jitsi"})

BOT_NAME = "Auris Assistant"
REQUEST_TIMEOUT_SEC = 30.0
# Le fichier audio d'une réunion d'une heure dépasse largement les quelques Mo :
# le téléchargement mérite une marge bien plus large qu'un appel d'API ordinaire.
DOWNLOAD_TIMEOUT_SEC = 300.0


class VexaError(Exception):
    """Erreur d'échange avec Vexa. L'appelant décide s'il bloque ou non."""


def _headers() -> dict:
    return {"X-API-Key": settings.VEXA_API_KEY, "Content-Type": "application/json"}


def parse_meeting_link(meeting_link: str) -> tuple[str, str]:
    """
    Extrait (platform, native_meeting_id) d'un lien de visioconférence.

    Lève VexaError si le lien n'est pas reconnu — mieux vaut un message clair
    à la création de la réunion qu'un bot qui ne partira jamais en silence.
    """
    for pattern, platform in _MEETING_PATTERNS:
        found = pattern.search(meeting_link or "")
        if found:
            return platform, found.group(1)

    raise VexaError(
        "Lien de réunion non reconnu. Formats acceptés : Google Meet, "
        "Microsoft Teams, Zoom."
    )


async def spawn_bot(meeting_link: str) -> dict:
    """
    Envoie le bot Auris dans la réunion.

    Retourne le dict de Vexa, dont le champ "id" (entier) est l'identifiant
    qu'il renverra plus tard dans ses webhooks : c'est lui qu'il faut stocker
    pour relier un événement entrant à la réunion Auris correspondante.

    Lève VexaError en cas d'échec — contrairement à la version précédente qui
    avalait l'exception et laissait l'utilisateur devant une réunion dont le
    bot n'était jamais parti.
    """
    platform, native_meeting_id = parse_meeting_link(meeting_link)

    payload = {
        "platform":          platform,
        "native_meeting_id": native_meeting_id,
        "bot_name":          BOT_NAME,
    }

    # Zoom et Jitsi : le lien complet porte le code d'accès, que l'identifiant
    # numérique ne contient pas. On l'envoie tel quel plutôt que d'extraire le
    # "pwd" nous-mêmes — Vexa sait le lire, et un lien intact vieillit mieux
    # qu'un paramètre que nous aurions recopié.
    if platform in PLATFORMS_REQUIRING_URL:
        payload["meeting_url"] = meeting_link

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VEXA_API_URL}/bots",
                headers=_headers(),
                json=payload,
                timeout=REQUEST_TIMEOUT_SEC,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise VexaError(
            f"Vexa a refusé le lancement du bot ({e.response.status_code}) : "
            f"{e.response.text[:200]}"
        ) from e
    except httpx.HTTPError as e:
        raise VexaError(f"Vexa injoignable : {e}") from e

    logger.info(
        "Bot Vexa lancé — vexa_meeting_id=%s platform=%s native_id=%s",
        data.get("id"), platform, native_meeting_id,
    )
    return data


async def stop_bot(platform: str, native_meeting_id: str) -> dict:
    """
    Fait quitter la réunion au bot. Vexa clôt alors l'enregistrement et émet
    l'événement "meeting.completed".
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{VEXA_API_URL}/bots/{platform}/{native_meeting_id}",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT_SEC,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise VexaError(f"Arrêt du bot impossible : {e}") from e


async def get_bot_status(vexa_meeting_id: int) -> Optional[dict]:
    """
    Interroge Vexa sur l'état d'un bot en cours.

    Indispensable parce que Vexa n'ENVOIE pas l'événement "meeting.started" :
    ses journaux de livraison le marquent "suppressed", seul "meeting.completed"
    part réellement. Sans cette interrogation, une réunion resterait affichée
    "en attente que le bot rejoigne" alors que le bot est déjà entré.

    Retourne le descriptif du bot, ou None s'il n'est plus dans la liste des
    bots actifs (soit il n'a pas démarré, soit la réunion est terminée).
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{VEXA_API_URL}/bots/status",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT_SEC,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as e:
        raise VexaError(f"Etat des bots indisponible : {e}") from e

    for bot in payload.get("running", []):
        if bot.get("id") == vexa_meeting_id:
            return bot
    return None


async def find_recording(vexa_meeting_id: int) -> Optional[dict]:
    """
    Retrouve l'enregistrement produit pour une réunion Vexa donnée.

    Retourne None si Vexa n'a encore rien publié : l'assemblage du fichier
    prend un moment après le départ du bot, et l'appelant doit pouvoir
    réessayer plutôt que d'échouer définitivement.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{VEXA_API_URL}/recordings",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT_SEC,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as e:
        raise VexaError(f"Liste des enregistrements indisponible : {e}") from e

    for recording in payload.get("recordings", []):
        if recording.get("meeting_id") == vexa_meeting_id:
            return recording
    return None


async def download_audio(recording_id: int) -> tuple[bytes, str]:
    """
    Télécharge l'audio complet d'un enregistrement.

    Vexa découpe l'audio en segments de 30 secondes (000000.webm, 000001.webm…) :
    une réunion d'une heure en produit cent vingt. On passe donc par /master,
    qui désigne le fichier assemblé, plutôt que de concaténer les morceaux.

    Retourne (octets, type MIME).
    """
    try:
        async with httpx.AsyncClient() as client:
            master = await client.get(
                f"{VEXA_API_URL}/recordings/{recording_id}/master",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT_SEC,
            )
            master.raise_for_status()
            media_file_id = master.json().get("media_file_id")

            if media_file_id is None:
                raise VexaError(
                    f"Enregistrement {recording_id} : aucun fichier assemblé disponible"
                )

            audio = await client.get(
                f"{VEXA_API_URL}/recordings/{recording_id}/media/{media_file_id}/download",
                headers=_headers(),
                timeout=DOWNLOAD_TIMEOUT_SEC,
            )
            audio.raise_for_status()
    except httpx.HTTPError as e:
        raise VexaError(f"Téléchargement de l'audio impossible : {e}") from e

    content = audio.content
    if not content:
        raise VexaError(f"Enregistrement {recording_id} : fichier audio vide")

    mime_type = audio.headers.get("content-type", "audio/webm").split(";")[0].strip()
    logger.info(
        "Audio Vexa récupéré — recording_id=%s taille=%d octets type=%s",
        recording_id, len(content), mime_type,
    )
    return content, mime_type
