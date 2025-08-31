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
# Strip surrounding quotes if present in the .env file
if MONGO_URI:
    MONGO_URI = MONGO_URI.strip().strip('"').strip("'")
DB_NAME = os.getenv("MONGO_DB", "ac9_sport")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mark DB as not connected until startup completes. This prevents request handlers
    # from assuming the DB is ready when the attribute hasn't been set yet.
    app.state.db_connected = False

    # Startup: attempt to initialize Motor client and Beanie, but don't crash the whole app
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
        # Shutdown: close motor client if present
        client = getattr(app.state, "mongo_client", None)
        if client:
            try:
                client.close()
            except Exception:
                logging.getLogger("ac9_sport_api").exception(
                    "Error closing Mongo client on shutdown"
                )


app = FastAPI(title="ac9_sport_api", lifespan=lifespan)

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
    # Initialize Motor client and Beanie, but don't crash the whole app if DB is unreachable.
    try:
        if not MONGO_URI:
            logger.warning(
                "MONGO_URI not set; skipping database initialization on startup."
            )
            return

        # Use certifi's CA bundle to ensure TLS works in minimal container images
        # which may lack system CA certificates (common cause of TLS handshake errors).
        client = AsyncIOMotorClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())

        # If the connection string doesn't include a default database name (common with Atlas),
        # use the explicit DB name from MONGO_DB or fallback to 'ac9_sport'.
        db = client.get_database(DB_NAME)
        await init_beanie(
            database=db,
            document_models=[Category, Subcategory, Product, User, MacroCategory],
        )
        # Mark successful connection
        app.state.db_connected = True
        logger.info("Connected to MongoDB and initialized Beanie models.")
    except Exception as e:
        # Don't raise; log the detailed error so deploy logs show the root cause (TLS, network, auth)
        app.state.db_connected = False
        logger.exception("Failed to initialize MongoDB / Beanie on startup: %s", e)


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
app.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
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
    # Ensure CORS headers are present even for error responses (defensive for proxies)
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
    # Add CORS headers to the catch-all error response so browsers don't drop useful
    # error payloads due to missing CORS when the middleware isn't applied.
    return JSONResponse(
        status_code=500,
        content=content,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )
