import os
from typing import Tuple
from datetime import timedelta

S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION", "us-east-2")


def _get_client():
    try:
        import boto3
        from botocore.config import Config
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "boto3 is not installed. Add 'boto3' to requirements.txt"
        ) from exc

    # Configure to use signature version 4 and force region
    config = Config(
        signature_version="s3v4",
        region_name=S3_REGION,
        s3={
            "addressing_style": "virtual",  # Use virtual-hosted style URLs
            "use_accelerate_endpoint": False,  # Don't use S3 acceleration
        },
    )
    return boto3.client(
        "s3",
        config=config,
        region_name=S3_REGION,  # Explicitly set region here too
        endpoint_url=f"https://s3.{S3_REGION}.amazonaws.com",  # Force specific regional endpoint
    )


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

    # Add CORS headers to the signed URL
    params = {
        "Bucket": bucket,
        "Key": object_name,
        "ContentType": content_type,
    }

    # Generate the URL with explicit parameters
    url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params=params,
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )

    # Log the URL for debugging (without sensitive parts)
    import re

    debug_url = re.sub(r"X-Amz-Signature=[^&]+", "X-Amz-Signature=REDACTED", url)
    print(f"Debug: Generated presigned URL (sanitized): {debug_url}")
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
