from app.core.database import settings
import aiobotocore.session

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