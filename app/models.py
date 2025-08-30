from typing import List, Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class Category(Document):
    name: str
    description: Optional[str] = None
    macro_category_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    class Settings:
        name = "categories"


class MacroCategory(Document):
    # Use UUID strings as the document _id so frontend gets stable UUIDs
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    class Settings:
        name = "macro_categories"


class Subcategory(Document):
    name: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

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
    createdAt: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    subcategoryId: Optional[str] = None
    stockBySize: Optional[dict] = None
    categories: Optional[List[dict]] = None

    class Settings:
        name = "products"


class User(Document):
    email: str
    password_hash: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    class Settings:
        name = "users"
