from fastapi import FastAPI, Response

from .routes.categories import router as categories_router
from .routes.subcategories import router as subcategories_router
from .routes.products import router as products_router
from .routes.auth import router as auth_router
from .routes.macro_categories import router as macro_categories_router
from .routes.uploads import router as uploads_router

API_PREFIX = "/api"


def register_routes(app: FastAPI) -> None:
    """Register all application routers under a single API prefix.

    This keeps `main.py` focused on app lifecycle and middleware while
    grouping route wiring in one place.
    """

    app.include_router(
        categories_router, prefix=f"{API_PREFIX}/categories", tags=["categories"]
    )
    app.include_router(
        macro_categories_router,
        prefix=f"{API_PREFIX}/macro-categories",
        tags=["macro-categories"],
    )
    app.include_router(
        subcategories_router,
        prefix=f"{API_PREFIX}/subcategories",
        tags=["subcategories"],
    )
    app.include_router(
        products_router, prefix=f"{API_PREFIX}/products", tags=["products"]
    )
    app.include_router(uploads_router, prefix=f"{API_PREFIX}/uploads", tags=["uploads"])
    app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["auth"])

    @app.get(f"{API_PREFIX}/health")
    def health():
        return {"status": "ok"}

    @app.options(f"{API_PREFIX}/auth/login")
    async def options_auth_login():
        """Fallback handler for OPTIONS preflight requests to /auth/login.
        Some clients or intermediaries may send a plain OPTIONS without
        Access-Control-Request-Method/Headers. Returning 204 ensures the
        preflight can succeed and lets CORSMiddleware provide the CORS headers.
        """
        return Response(status_code=204)
