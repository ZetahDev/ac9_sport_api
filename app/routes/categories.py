from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from ..models import Category
from ..deps import get_current_active_superuser

router = APIRouter()


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
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "macroCategoryId": c.macro_category_id,
    }
