from fastapi import APIRouter, HTTPException, Depends, Body
from ..deps import get_current_active_superuser
from ..core import gcs

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
    try:
        upload_url, public_key = gcs.generate_presigned_upload_url(key, content_type)
        return {"ok": True, "upload_url": upload_url, "key": public_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
