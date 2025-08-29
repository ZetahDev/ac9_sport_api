# package

from .categories import router as categories_router
from .subcategories import router as subcategories_router
from .products import router as products_router

__all__ = ["categories_router", "subcategories_router", "products_router"]
