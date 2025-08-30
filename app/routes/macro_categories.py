from typing import List
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from ..models import MacroCategory, Category
from ..deps import get_current_active_superuser
from datetime import datetime, timezone
import logging
from fastapi import UploadFile, File
import os
import uuid
import aiofiles
from ..core import gcs

logger = logging.getLogger("ac9_sport_api.macro")

router = APIRouter()

MACRO_NOT_FOUND = "Macro category not found"


@router.get("/", response_model=List[dict])
async def list_macro_categories(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
):
    docs = await MacroCategory.find_many({}).skip(skip).limit(limit).to_list()
    return [
        {
            "id": d.id,
            "name": d.name,
            "slug": d.slug,
            "description": d.description,
            "image": d.image,
        }
        for d in docs
    ]


@router.post("/", response_model=dict)
async def create_macro_category(data: dict, _=Depends(get_current_active_superuser)):
    m = MacroCategory(
        name=data.get("name"),
        slug=data.get("slug"),
        description=data.get("description"),
        image=data.get("image"),
    )
    await m.insert()
    logger.info("Macro created: %s id=%s", m.name, m.id)
    return {
        "id": m.id,
        "name": m.name,
        "slug": m.slug,
        "description": m.description,
        "image": m.image,
    }


@router.put("/{macro_id}", response_model=dict)
async def update_macro_category(
    macro_id: str = Path(...),
    data: dict = None,
    _=Depends(get_current_active_superuser),
):
    # Try multiple resolution strategies to be robust against id formats
    m = await MacroCategory.find_one({"id": macro_id})
    if not m:
        try:
            m = await MacroCategory.get(macro_id)
        except Exception:
            m = None
    if not m:
        # fallback: try slug
        m = await MacroCategory.find_one({"slug": macro_id})
    if not m:
        raise HTTPException(status_code=404, detail=MACRO_NOT_FOUND)
    if not data:
        data = {}
    updated = False
    for k in ("name", "slug", "description", "image"):
        if k in data and getattr(m, k) != data.get(k):
            setattr(m, k, data.get(k))
            updated = True
    if updated:
        await m.save()
        logger.info("Macro updated: %s id=%s", m.name, m.id)
    return {
        "id": m.id,
        "name": m.name,
        "slug": m.slug,
        "description": m.description,
        "image": m.image,
    }


@router.delete("/{macro_id}")
async def delete_macro_category(
    macro_id: str = Path(...), _=Depends(get_current_active_superuser)
):
    m = await MacroCategory.find_one({"id": macro_id})
    if not m:
        raise HTTPException(status_code=404, detail=MACRO_NOT_FOUND)
    await m.delete()
    logger.info("Macro deleted: %s id=%s", m.name, m.id)
    return {"ok": True}


@router.get("/{macro_id}", response_model=dict)
async def get_macro(macro_id: str = Path(...)):
    # Try multiple resolution strategies to be robust against id formats
    m = await MacroCategory.find_one({"id": macro_id})
    if not m:
        try:
            m = await MacroCategory.get(macro_id)
        except Exception:
            m = None
    if not m:
        # fallback: try slug
        m = await MacroCategory.find_one({"slug": macro_id})
    if not m:
        raise HTTPException(status_code=404, detail=MACRO_NOT_FOUND)
    return {
        "id": m.id,
        "name": m.name,
        "slug": m.slug,
        "description": m.description,
        "image": m.image,
    }


@router.get("/{macro_id}/categories", response_model=List[dict])
async def get_categories_by_macro(macro_id: str = Path(...)):
    # Resolve macro by multiple strategies to be robust against id formats
    m = await MacroCategory.find_one({"id": macro_id})
    if not m:
        try:
            m = await MacroCategory.get(macro_id)
        except Exception:
            m = None
    if not m:
        # fallback: try slug
        m = await MacroCategory.find_one({"slug": macro_id})
    if not m:
        raise HTTPException(status_code=404, detail=MACRO_NOT_FOUND)
    cats = await Category.find_many({"macro_category_id": macro_id}).to_list()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "macroCategoryId": c.macro_category_id,
        }
        for c in cats
    ]


@router.post("/{macro_id}/upload-image")
async def upload_macro_image(
    macro_id: str = Path(...),
    file: UploadFile = File(...),
    _=Depends(get_current_active_superuser),
):
    # Resolve macro by multiple strategies to be robust against id formats
    m = await MacroCategory.find_one({"id": macro_id})
    if not m:
        try:
            m = await MacroCategory.get(macro_id)
        except Exception:
            m = None
    if not m:
        m = await MacroCategory.find_one({"slug": macro_id})
    if not m:
        raise HTTPException(status_code=404, detail=MACRO_NOT_FOUND)

    # validate content type
    allowed = {"image/png", "image/jpeg", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    # limit size by reading first chunk (e.g., 5MB max)
    MAX_BYTES = 5 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    # If GCS is configured, generate a signed URL and return it so the client
    # can upload directly. Otherwise fall back to local storage.
    try:
        # object key: macros/<macro_id>/<uuid>.<ext>
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        key = f"macros/{macro_id}/{uuid.uuid4().hex}{ext}"
        presigned_url, public_key = gcs.generate_presigned_upload_url(
            key, file.content_type
        )
        # Store reference in model (we store the GCS object key, frontend will request GET signed URL)
        m.image = f"gcs://{public_key}"
        await m.save()
        logger.info("Macro image presign created: %s -> %s", m.id, m.image)
        return {"ok": True, "upload_url": presigned_url, "key": public_key}
    except Exception:
        # Fallback to local storage if GCS not configured or error occurs
        from pathlib import Path

        storage_dir = Path(__file__).resolve().parents[1] / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        fname = f"macro_{macro_id}_{uuid.uuid4().hex}{ext}"
        path = storage_dir / fname
        logger.info("Writing uploaded macro image to %s", str(path))
        async with aiofiles.open(path, "wb") as out:
            await out.write(contents)

        # update model
        m.image = f"/storage/{fname}"
        await m.save()
        logger.info("Macro image uploaded (local fallback): %s -> %s", m.id, m.image)
        return {"ok": True, "image": m.image}


@router.get("/__debug__/storage-list")
async def debug_storage_list():
    from pathlib import Path

    storage_dir = Path(__file__).resolve().parents[1] / "storage"
    files = []
    if storage_dir.exists():
        for p in storage_dir.iterdir():
            files.append(p.name)
    return {"storage_dir": str(storage_dir), "files": files}


@router.get("/{macro_id}/image-url")
async def get_macro_image_url(macro_id: str = Path(...)):
    m = await MacroCategory.find_one({"id": macro_id})
    if not m:
        try:
            m = await MacroCategory.get(macro_id)
        except Exception:
            m = None
    if not m:
        m = await MacroCategory.find_one({"slug": macro_id})
    if not m:
        raise HTTPException(status_code=404, detail=MACRO_NOT_FOUND)

    if m.image and str(m.image).startswith("gcs://"):
        key = str(m.image).replace("gcs://", "")
        try:
            url = gcs.generate_presigned_get_url(key)
            return {"ok": True, "url": url}
        except Exception:
            # fallback: no presigned url available
            return {"ok": False, "url": None}
    # fallback: local storage
    return {"ok": True, "url": m.image}
