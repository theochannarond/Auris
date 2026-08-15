import os
import logging
from app.services.storage_service import (
    check_ovh_health,
    upload_audio_file,
    LOCAL_FALLBACK_DIR
)

logger = logging.getLogger(__name__)


async def sync_local_files_to_ovh() -> dict:
    """
    Job de synchronisation — à appeler périodiquement (ex: toutes les 5 minutes).

    Parcourt le dossier de fallback local, tente d'uploader chaque fichier
    sur OVH, et supprime le fichier local si l'upload réussit.

    Retourne un résumé :
    {
        "synced":  int,  # fichiers uploadés avec succès
        "failed":  int,  # fichiers en échec
        "skipped": int   # OVH toujours indisponible
    }
    """
    health = await check_ovh_health()

    if health["status"] != "ok":
        logger.info(
            f"Sync ignorée — OVH toujours indisponible : {health.get('error')}"
        )
        return {"synced": 0, "failed": 0, "skipped": 1}

    if not os.path.exists(LOCAL_FALLBACK_DIR):
        return {"synced": 0, "failed": 0, "skipped": 0}

    files = [
        f for f in os.listdir(LOCAL_FALLBACK_DIR)
        if os.path.isfile(os.path.join(LOCAL_FALLBACK_DIR, f))
    ]

    if not files:
        return {"synced": 0, "failed": 0, "skipped": 0}

    synced = 0
    failed = 0

    for filename in files:
        local_path = os.path.join(LOCAL_FALLBACK_DIR, filename)

        # Reconstitue la storage_key OVH depuis le nom de fichier local
        object_key = filename.replace("_", "/", 1)

        try:
            with open(local_path, "rb") as f:
                content = f.read()

            await upload_audio_file(content, object_key, "audio/wav")
            os.remove(local_path)
            synced += 1
            logger.info(f"Sync réussie : {filename} → OVH ({object_key})")

        except Exception as e:
            failed += 1
            logger.error(f"Sync échouée pour {filename} : {e}")

    logger.info(f"Sync terminée — {synced} uploadés, {failed} en échec")
    return {"synced": synced, "failed": failed, "skipped": 0}