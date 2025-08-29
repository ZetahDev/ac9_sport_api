from typing import Optional
from pydantic import BaseModel


class SubcategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: int
