from app.core.database import settings
import aiobotocore.session

# Valeur par défaut de Settings tant que l'abonnement OVH n'est pas souscrit
OVH_PLACEHOLDER_ACCESS_KEY = "your-ovh-access-key"


def is_storage_configured() -> bool:
    """
    Indique si de vraies credentials OVH sont en place.

    Sans abonnement, la clé reste sur sa valeur par défaut : appeler OVH
    déclencherait un aller-retour réseau voué à échouer.
    """
    return settings.OVH_ACCESS_KEY != OVH_PLACEHOLDER_ACCESS_KEY


async def upload_audio_file(file_content: bytes, object_key: str, content_type: str) -> str:
    session = aiobotocore.session.get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.OVH_ENDPOINT_URL,
        aws_access_key_id=settings.OVH_ACCESS_KEY,
        aws_secret_access_key=settings.OVH_SECRET_KEY,
        region_name=settings.OVH_REGION,
    ) as client:
        await client.put_object(
            Bucket=settings.OVH_BUCKET_NAME,
            Key=object_key,
            Body=file_content,
            ContentType=content_type,
        )
    return object_key


async def download_audio_file(object_key: str) -> bytes:
    """
    Récupère un fichier audio depuis OVH Object Storage.
    Utilisé avant l'envoi du contenu à Voxtral pour transcription.
    """
    session = aiobotocore.session.get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.OVH_ENDPOINT_URL,
        aws_access_key_id=settings.OVH_ACCESS_KEY,
        aws_secret_access_key=settings.OVH_SECRET_KEY,
        region_name=settings.OVH_REGION,
    ) as client:
        response = await client.get_object(
            Bucket=settings.OVH_BUCKET_NAME,
            Key=object_key,
        )
        async with response["Body"] as stream:
            return await stream.read()


async def delete_audio_file(object_key: str) -> bool:
    """
    Supprime un fichier audio d'OVH Object Storage (RGPD Art.17).

    Retourne True si OVH a accepté la suppression, False si le stockage n'est
    pas encore configuré ou si l'appel a échoué. L'appelant ne doit jamais
    faire dépendre le succès de la suppression RGPD de ce retour : la donnée
    qui compte pour l'utilisateur est celle qui disparaît de la base.
    """
    if not is_storage_configured():
        print(f"OVH non configuré — suppression ignorée pour {object_key}")
        return False

    try:
        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings.OVH_ENDPOINT_URL,
            aws_access_key_id=settings.OVH_ACCESS_KEY,
            aws_secret_access_key=settings.OVH_SECRET_KEY,
            region_name=settings.OVH_REGION,
        ) as client:
            # delete_object est idempotent : une clé absente renvoie 204
            await client.delete_object(
                Bucket=settings.OVH_BUCKET_NAME,
                Key=object_key,
            )
        return True
    except Exception as e:
        # On log mais on ne bloque pas : le fichier orphelin sera repris par la purge
        print(f"OVH delete error for {object_key}: {e}")
        return False
    
async def check_ovh_health() -> dict:
    """
    Vérifie que OVH Object Storage est accessible en tentant un head_bucket.
    Retourne un dict {"status": "ok"|"unavailable", "error": str|None}.
    Utilisé par le health endpoint et le fallback automatique.
    """
    if not settings.OVH_ACCESS_KEY or not settings.OVH_SECRET_KEY:
        return {"status": "unavailable", "error": "Credentials OVH manquants"}

    session = aiobotocore.session.get_session()
    try:
        async with session.create_client(
            "s3",
            endpoint_url=settings.OVH_ENDPOINT_URL,
            aws_access_key_id=settings.OVH_ACCESS_KEY,
            aws_secret_access_key=settings.OVH_SECRET_KEY,
            region_name=settings.OVH_REGION,
        ) as client:
            await client.head_bucket(Bucket=settings.OVH_BUCKET_NAME)
            return {"status": "ok", "error": None}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}