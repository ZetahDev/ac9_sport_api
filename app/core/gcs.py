import os
from typing import Tuple
from datetime import timedelta

S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION", "us-east-2")  # Default to us-east-2 if not specified


def _get_client():
    try:
        import boto3
        from botocore.config import Config
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "boto3 is not installed. Add 'boto3' to requirements.txt"
        ) from exc

    # Configure to use signature version 4
    config = Config(signature_version="s3v4", region_name=S3_REGION)
    return boto3.client("s3", config=config)


def generate_presigned_upload_url(
    object_name: str, content_type: str, expires_in: int = 300
) -> Tuple[str, str]:
    """Generate a presigned PUT URL for S3 uploads. Returns (url, key).
    Requires AWS credentials available in environment or instance profile.
    """
    client = _get_client()
    bucket = S3_BUCKET
    if not bucket:
        raise RuntimeError("S3_BUCKET not configured")

    # Ensure we have a valid content type
    if not content_type:
        content_type = "application/octet-stream"

    params = {"Bucket": bucket, "Key": object_name, "ContentType": content_type}
    url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params=params,
        ExpiresIn=expires_in,
        HttpMethod="PUT",  # Explicitly set HTTP method
    )
    return url, object_name


def generate_presigned_get_url(object_name: str, expires_in: int = 300) -> str:
    client = _get_client()
    bucket = S3_BUCKET
    if not bucket:
        raise RuntimeError("S3_BUCKET not configured")
    params = {"Bucket": bucket, "Key": object_name}
    url = client.generate_presigned_url(
        ClientMethod="get_object", Params=params, ExpiresIn=expires_in
    )
    return url
