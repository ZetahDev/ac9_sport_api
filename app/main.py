from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from fastapi.staticfiles import StaticFiles

package_root = Path(__file__).resolve().parents[1]
dotenv_path = package_root / ".env"
load_dotenv(dotenv_path=dotenv_path)

from .routes.categories import router as categories_router
from .routes.subcategories import router as subcategories_router
from .routes.products import router as products_router
from .models import Category, Subcategory, Product, User, MacroCategory
from .routes.auth import router as auth_router
from .routes.macro_categories import router as macro_categories_router

MONGO_URI = os.getenv("MONGO_URI")
# Strip surrounding quotes if present in the .env file
if MONGO_URI:
    MONGO_URI = MONGO_URI.strip().strip('"').strip("'")
DB_NAME = os.getenv("MONGO_DB", "ac9_sport")

app = FastAPI(title="ac9_sport_api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local storage (images)
STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


@app.on_event("startup")
async def on_startup():
    # Initialize Motor client and Beanie
    client = AsyncIOMotorClient(MONGO_URI)
    # If the connection string doesn't include a default database name (common with Atlas),
    # use the explicit DB name from MONGO_DB or fallback to 'ac9_sport'.
    db = client.get_database(DB_NAME)
    await init_beanie(
        database=db,
        document_models=[Category, Subcategory, Product, User, MacroCategory],
    )


# Include routers
app.include_router(categories_router, prefix="/categories", tags=["categories"])
# New dedicated macro-categories router
app.include_router(
    macro_categories_router, prefix="/macro-categories", tags=["macro-categories"]
)
app.include_router(
    subcategories_router, prefix="/subcategories", tags=["subcategories"]
)
app.include_router(products_router, prefix="/products", tags=["products"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}


from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging


logger = logging.getLogger("ac9_sport_api")


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Provide a consistent JSON structure for HTTP errors (including 404)
    content = {
        "detail": exc.detail if hasattr(exc, "detail") else str(exc),
        "status_code": exc.status_code,
        "path": str(request.url.path),
        "method": request.method,
    }
    logger.warning("HTTP error: %s %s -> %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Catch-all for unexpected server errors
    logger.exception(
        "Unhandled exception while processing request %s %s",
        request.method,
        request.url.path,
    )
    content = {
        "detail": "Internal Server Error",
        "status_code": 500,
        "path": str(request.url.path),
        "method": request.method,
    }
    return JSONResponse(status_code=500, content=content)
