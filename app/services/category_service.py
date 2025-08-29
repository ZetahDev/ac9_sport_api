from typing import List, Optional
from ..models import Category


async def list_categories(
    skip: int = 0, limit: int = 50, search: Optional[str] = None
) -> List[Category]:
    if search:
        docs = await Category.find_many({}).to_list()
        return [d for d in docs if search.lower() in (d.name or "").lower()][
            skip : skip + limit
        ]
    return await Category.find_many({}).skip(skip).limit(limit).to_list()


async def create_category(data: dict) -> Category:
    c = Category(
        name=data.get("name"),
        description=data.get("description"),
        macro_category_id=data.get("macroCategoryId"),
    )
    await c.insert()
    return c
