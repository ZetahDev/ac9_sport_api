import os
from typing import Tuple
from datetime import timedelta

S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION")


def _get_client():
    try:
        import boto3
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "boto3 is not installed. Add 'boto3' to requirements.txt"
        ) from exc
    return boto3.client("s3", region_name=S3_REGION)


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

    params = {
        "Bucket": bucket,
        "Key": object_name,
        "ContentType": content_type,
        "SignatureVersion": "s3v4",  # Force AWS4-HMAC-SHA256
    }
    url = client.generate_presigned_url(
        ClientMethod="put_object", Params=params, ExpiresIn=expires_in, HttpMethod="PUT"
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
