import os
from typing import Tuple
from google.cloud import storage
from datetime import timedelta

GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def _get_client():
    # The google-cloud-storage client uses GOOGLE_APPLICATION_CREDENTIALS env var
    return storage.Client()


def generate_presigned_upload_url(
    object_name: str, content_type: str, expires_in: int = 300
) -> Tuple[str, str]:
    """Generate a signed URL for uploading an object via PUT.

    Returns tuple (url, public_url_key)
    """
    client = _get_client()
    bucket_name = GCS_BUCKET
    import os
    from typing import Tuple
    from datetime import timedelta

    GCS_BUCKET = os.getenv("GCS_BUCKET")


    def _get_client():
        try:
            # Import lazily so environments without google-cloud-storage don't fail on import
            from google.cloud import storage
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "google-cloud-storage not installed. Add 'google-cloud-storage' to requirements or set up the client." 
            ) from exc

        # The google-cloud-storage client uses GOOGLE_APPLICATION_CREDENTIALS env var
        return storage.Client()


    def generate_presigned_upload_url(object_name: str, content_type: str, expires_in: int = 300) -> Tuple[str, str]:
        """Generate a signed URL for uploading an object via PUT.

        Returns tuple (url, public_url_key)
        """
        client = _get_client()
        bucket_name = GCS_BUCKET
        if not bucket_name:
            raise RuntimeError("GCS_BUCKET not configured")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires_in),
            method="PUT",
            content_type=content_type,
        )

        # Public-accessible key for later reference
        public_key = object_name
        return url, public_key


    def generate_presigned_get_url(object_name: str, expires_in: int = 300) -> str:
        client = _get_client()
        bucket_name = GCS_BUCKET
        if not bucket_name:
            raise RuntimeError("GCS_BUCKET not configured")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        url = blob.generate_signed_url(version="v4", expiration=timedelta(seconds=expires_in), method="GET")
        return url
