from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import JSONResponse
from ..deps import get_current_active_superuser
from ..core import gcs
import os

router = APIRouter()


@router.post("/presign")
async def presign_upload(
    data: dict = Body(...), _=Depends(get_current_active_superuser)
):
    """Request body: { "key": "macros/...jpg", "content_type": "image/jpeg" }
    Returns: { upload_url, key }
    """
    key = data.get("key")
    content_type = data.get("content_type")
    if not key or not content_type:
        raise HTTPException(status_code=400, detail="key and content_type required")

    # Check if AWS credentials are available
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    s3_bucket = os.getenv("S3_BUCKET")

    if not aws_access_key or not s3_bucket:
        # Fallback to local storage simulation
        # For local/demo deployments without S3 credentials
        base_url = os.getenv("API_BASE_URL", "http://localhost:8001")
        fake_upload_url = f"{base_url}/api/uploads/local/{key}"
        return {"ok": True, "upload_url": fake_upload_url, "key": key}

    try:
        upload_url, public_key = gcs.generate_presigned_upload_url(key, content_type)
        return {"ok": True, "upload_url": upload_url, "key": public_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/local/{key:path}")
async def handle_local_upload(key: str, request: Request):
    """Fallback endpoint for local storage when S3 credentials are not available.
    Accepts a PUT request with file content and stores it locally.
    """
    try:
        # Read the uploaded content
        content = await request.body()

        # Create storage directory
        from pathlib import Path
        import aiofiles

        storage_dir = Path(__file__).resolve().parents[2] / "storage"
        folder = key.split("/")[0] if "/" in key else "uploads"
        target_dir = storage_dir / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save the file asynchronously
        filename = key.split("/")[-1]
        file_path = target_dir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return JSONResponse(
            status_code=200,
            content={"message": "File uploaded successfully", "key": key},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(exc)}")
