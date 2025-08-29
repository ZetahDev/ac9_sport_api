from typing import Optional
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    macro_category_id: Optional[int] = None


class CategoryRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    macro_category_id: Optional[int]
