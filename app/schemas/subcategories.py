from typing import Optional, List
from pydantic import BaseModel, Field


class SubcategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    categoryIds: Optional[List[str]] = Field(None, alias="categoryIds")

    class Config:
        allow_population_by_field_name = True
