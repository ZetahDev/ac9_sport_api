from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

package_root = Path(__file__).resolve().parents[1]
dotenv_path = package_root / ".env"
load_dotenv(dotenv_path=dotenv_path)

from .routes.categories import router as categories_router
from .routes.subcategories import router as subcategories_router
from .routes.products import router as products_router
from .models import Category, Subcategory, Product

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


@app.on_event("startup")
async def on_startup():
    # Initialize Motor client and Beanie
    client = AsyncIOMotorClient(MONGO_URI)
    # If the connection string doesn't include a default database name (common with Atlas),
    # use the explicit DB name from MONGO_DB or fallback to 'ac9_sport'.
    db = client.get_database(DB_NAME)
    await init_beanie(database=db, document_models=[Category, Subcategory, Product])


# Include routers
app.include_router(categories_router, prefix="/categories", tags=["categories"])
app.include_router(
    subcategories_router, prefix="/subcategories", tags=["subcategories"]
)
app.include_router(products_router, prefix="/products", tags=["products"])


@app.get("/health")
def health():
    return {"status": "ok"}
