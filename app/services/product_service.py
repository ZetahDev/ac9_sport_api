from typing import List, Optional
from ..models import Product


async def list_products(skip: int = 0, limit: int = 100, search: Optional[str] = None):
    if search:
        docs = await Product.find_many({}).to_list()
        return [d for d in docs if search.lower() in (d.name or "").lower()][
            skip : skip + limit
        ]
    return await Product.find_many({"isActive": True}).skip(skip).limit(limit).to_list()
