from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from ..models import Subcategory, Category
from ..deps import get_current_active_superuser

router = APIRouter()


async def verify_category_exists(category_id: str):
    c = await Category.get(category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")


@router.get("/", response_model=List[dict])
async def get_subcategories_minimal(
    category_id: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
):
    if category_id:
        await verify_category_exists(category_id)
        docs = (
            await Subcategory.find_many({"category_id": category_id})
            .skip(skip)
            .limit(limit)
            .to_list()
        )
    else:
        docs = await Subcategory.find_many({}).skip(skip).limit(limit).to_list()

    if search:
        docs = [d for d in docs if search.lower() in (d.name or "").lower()]

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "categoryId": r.category_id,
        }
        for r in docs
    ]


@router.post("/", response_model=dict)
async def create_subcategory(
    subcategory_in: dict, _=Depends(get_current_active_superuser)
):
    await verify_category_exists(subcategory_in.get("categoryId"))
    existing = await Subcategory.find_one(
        {
            "name": subcategory_in.get("name"),
            "category_id": subcategory_in.get("categoryId"),
        }
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A subcategory with this name already exists in this category",
        )
    s = Subcategory(
        name=subcategory_in.get("name"),
        description=subcategory_in.get("description"),
        category_id=subcategory_in.get("categoryId"),
    )
    await s.insert()
    return {
        "id": str(s.id),
        "name": s.name,
        "description": s.description,
        "categoryId": s.category_id,
    }
