from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from contextlib import asynccontextmanager
from beanie import init_beanie
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

package_root = Path(__file__).resolve().parents[1]
dotenv_path = package_root / ".env"
load_dotenv(dotenv_path=dotenv_path)

from .routes.categories import router as categories_router
from .routes.subcategories import router as subcategories_router
from .routes.products import router as products_router
from .models import Category, Subcategory, Product, User, MacroCategory
from .routes.auth import router as auth_router
from .routes.macro_categories import router as macro_categories_router
from .routes.uploads import router as uploads_router

MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    MONGO_URI = MONGO_URI.strip().strip('"').strip("'")
DB_NAME = os.getenv("MONGO_DB", "ac9_sport")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_connected = False

    try:
        if not MONGO_URI:
            logging.getLogger("ac9_sport_api").warning(
                "MONGO_URI not set; skipping database initialization on startup."
            )
        else:
            client = AsyncIOMotorClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
            app.state.mongo_client = client
            db = client.get_database(DB_NAME)
            await init_beanie(
                database=db,
                document_models=[Category, Subcategory, Product, User, MacroCategory],
            )
            app.state.db_connected = True
            logging.getLogger("ac9_sport_api").info(
                "Connected to MongoDB and initialized Beanie models."
            )
    except Exception as e:
        app.state.db_connected = False
        logging.getLogger("ac9_sport_api").exception(
            "Failed to initialize MongoDB / Beanie on startup: %s", e
        )

    try:
        yield
    finally:
        client = getattr(app.state, "mongo_client", None)
        if client:
            try:
                client.close()
            except Exception:
                logging.getLogger("ac9_sport_api").exception(
                    "Error closing Mongo client on shutdown"
                )


app = FastAPI(title="ac9_sport_api", lifespan=lifespan)

origins = [
    "https://www.ac9sport.com",
    "https://ac9sport.com",         
    "http://localhost:3000",      
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


@app.on_event("startup")
async def on_startup():
    try:
        if not MONGO_URI:
            logger.warning(
                "MONGO_URI not set; skipping database initialization on startup."
            )
            return
        client = AsyncIOMotorClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())

        db = client.get_database(DB_NAME)
        await init_beanie(
            database=db,
            document_models=[Category, Subcategory, Product, User, MacroCategory],
        )

        app.state.db_connected = True
        logger.info("Connected to MongoDB and initialized Beanie models.")
    except Exception as e:
        app.state.db_connected = False
        logger.exception("Failed to initialize MongoDB / Beanie on startup: %s", e)



app.include_router(categories_router, prefix="/categories", tags=["categories"])
app.include_router(
    macro_categories_router, prefix="/macro-categories", tags=["macro-categories"]
)
app.include_router(
    subcategories_router, prefix="/subcategories", tags=["subcategories"]
)
app.include_router(products_router, prefix="/products", tags=["products"])
app.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}


logger = logging.getLogger("ac9_sport_api")

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    content = {
        "detail": exc.detail if hasattr(exc, "detail") else str(exc),
        "status_code": exc.status_code,
        "path": str(request.url.path),
        "method": request.method,
    }
    logger.warning("HTTP error: %s %s -> %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
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

    return JSONResponse(
        status_code=500,
        content=content,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )