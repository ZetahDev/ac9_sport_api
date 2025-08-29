from typing import List, Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from datetime import datetime


class Category(Document):
    name: str
    description: Optional[str] = None
    macro_category_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "categories"


class Subcategory(Document):
    name: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "subcategories"


class Product(Document):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    images: List[str] = Field(default_factory=list)
    sizes: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)
    isActive: bool = True
    isFeatured: bool = False
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    subcategoryId: Optional[str] = None
    stockBySize: Optional[dict] = None
    categories: Optional[List[dict]] = None

    class Settings:
        name = "products"
