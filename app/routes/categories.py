from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from ..models import Category
from ..deps import get_current_active_superuser
from fastapi import HTTPException, Path, Body
from datetime import datetime, timezone
import logging
from fastapi import UploadFile, File
import os
import uuid
import aiofiles

logger = logging.getLogger("ac9_sport_api.category")

router = APIRouter()

CATEGORY_NOT_FOUND_MSG = "Category not found"


@router.get("/", response_model=List[dict])
async def get_categories_minimal(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
) -> List[dict]:
    if search:
        docs = await Category.find_many({}).to_list()
        docs = [d for d in docs if search.lower() in (d.name or "").lower()]
        docs = docs[skip : skip + limit]
    else:
        docs = await Category.find_many({}).skip(skip).limit(limit).to_list()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "macroCategoryId": r.macro_category_id,
        }
        for r in docs
    ]


@router.post("/", response_model=dict)
async def create_category(category_in: dict, _=Depends(get_current_active_superuser)):
    c = Category(
        name=category_in.get("name"),
        description=category_in.get("description"),
        macro_category_id=category_in.get("macroCategoryId"),
    )
    await c.insert()
    logger.info(
        "Category created: %s id=%s macro=%s", c.name, c.id, c.macro_category_id
    )
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "macroCategoryId": c.macro_category_id,
    }


@router.get("/{category_id}", response_model=dict)
async def get_category(category_id: str = Path(...)):
    # Try multiple resolution strategies to be robust against id formats
    c = await Category.find_one({"id": category_id})
    if not c:
        try:
            c = await Category.get(category_id)
        except Exception:
            c = None
    if not c:
        c = await Category.find_one({"slug": category_id})
    if not c:
        raise HTTPException(status_code=404, detail=CATEGORY_NOT_FOUND_MSG)
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "macroCategoryId": c.macro_category_id,
    }


@router.put("/{category_id}", response_model=dict)
async def update_category(
    category_id: str = Path(...),
    category_in: dict = Body(...),
    _=Depends(get_current_active_superuser),
):
    c = await Category.get(category_id)
    if not c:
        raise HTTPException(status_code=404, detail=CATEGORY_NOT_FOUND_MSG)
    # update fields if provided
    if "name" in category_in:
        c.name = category_in.get("name")
    if "description" in category_in:
        c.description = category_in.get("description")
    if "macroCategoryId" in category_in:
        c.macro_category_id = category_in.get("macroCategoryId")
    if "image" in category_in:
        # store images in a separate field if desired; categories currently have only name/description/macro
        setattr(c, "image", category_in.get("image"))
    c.updated_at = datetime.now(timezone.utc)
    await c.save()
    logger.info(
        "Category updated: %s id=%s macro=%s", c.name, c.id, c.macro_category_id
    )
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "macroCategoryId": c.macro_category_id,
    }


@router.delete("/{category_id}")
async def delete_category(
    category_id: str = Path(...), _=Depends(get_current_active_superuser)
):
    c = await Category.get(category_id)
    if not c:
        raise HTTPException(status_code=404, detail=CATEGORY_NOT_FOUND_MSG)
    await c.delete()
    logger.info("Category deleted: %s id=%s", c.name, c.id)
    return {"ok": True}


@router.post("/{category_id}/upload-image")
async def upload_category_image(
    category_id: str = Path(...),
    file: UploadFile = File(...),
    _=Depends(get_current_active_superuser),
):
    # Resolve category by multiple strategies to avoid 404 on different id formats
    c = await Category.find_one({"id": category_id})
    if not c:
        try:
            c = await Category.get(category_id)
        except Exception:
            c = None
    if not c:
        c = await Category.find_one({"slug": category_id})
    if not c:
        raise HTTPException(status_code=404, detail=CATEGORY_NOT_FOUND_MSG)

    allowed = {"image/png", "image/jpeg", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    MAX_BYTES = 5 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    # Use package-relative storage directory (match app.main STORAGE_DIR)
    from pathlib import Path

    storage_dir = Path(__file__).resolve().parents[1] / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    fname = f"category_{category_id}_{uuid.uuid4().hex}{ext}"
    path = storage_dir / fname
    async with aiofiles.open(path, "wb") as out:
        await out.write(contents)

    setattr(c, "image", f"/storage/{fname}")
    c.updated_at = datetime.now(timezone.utc)
    await c.save()
    logging.getLogger("ac9_sport_api.category").info(
        "Category image uploaded: %s -> %s", c.id, c.image
    )
    return {"ok": True, "image": c.image}
