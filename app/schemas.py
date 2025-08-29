from typing import Optional, List
from pydantic import BaseModel, conlist


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    macro_category_id: Optional[int] = None


class CategoryRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    macro_category_id: Optional[int]


class SubcategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: int


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    sizes: List[str]
    stockBySize: Optional[List[dict]] = None
    colors: List[str]
    categoryIds: List[int]
    isActive: Optional[bool] = True
    isFeatured: Optional[bool] = False


class ProductRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    sizes: List[str]
    stockBySize: Optional[List[dict]]
    colors: List[str]
    images: List[str]
    isActive: bool
    isFeatured: bool
