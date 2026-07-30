import boto3
from botocore.client import Config
from app.core.database import settings

def get_storage_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.OVH_ENDPOINT_URL,
        aws_access_key_id=settings.OVH_ACCESS_KEY,
        aws_secret_access_key=settings.OVH_SECRET_KEY,
        region_name=settings.OVH_REGION,
        config=Config(signature_version="s3v4"),
    )

def upload_audio_file(file_content: bytes, object_key: str, content_type: str) -> str:
    client = get_storage_client()
    client.put_object(
        Bucket=settings.OVH_BUCKET_NAME,
        Key=object_key,
        Body=file_content,
        ContentType=content_type,
    )
    return object_key