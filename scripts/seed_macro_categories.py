#!/usr/bin/env python3
"""
Seed script: create default MacroCategory entries if they don't exist.

Usage:
  python scripts/seed_macro_categories.py

This is idempotent: it will skip creating a macro if a macro with the same name exists.
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _prep_path():
    # Ensure app package is importable when running script from repo root
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    return package_root


async def main():
    package_root = _prep_path()
    dotenv_path = package_root / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from app.models import MacroCategory, Category, Subcategory, Product, User

    MONGO_URI = os.getenv("MONGO_URI")
    if MONGO_URI:
        MONGO_URI = MONGO_URI.strip().strip('"').strip("'")
    DB_NAME = os.getenv("MONGO_DB", "ac9_sport")

    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_database(DB_NAME)

    await init_beanie(
        database=db,
        document_models=[Category, Subcategory, Product, User, MacroCategory],
    )

    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Seed macro categories (accepts optional json file)"
    )
    parser.add_argument(
        "--file",
        help="Optional JSON file with array of macros: [{name,slug,description,image}]",
        default=None,
    )
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            try:
                defaults = json.load(fh)
            except Exception:
                print("Failed to parse JSON file.")
                return
    else:
        defaults = [
            {
                "name": "Deportivo",
                "slug": "deportivo",
                "description": "Colección deportiva",
                "image": None,
            },
            {
                "name": "Lifestyle",
                "slug": "lifestyle",
                "description": "Colección lifestyle / casual",
                "image": None,
            },
        ]

    for d in defaults:
        existing = await MacroCategory.find_one({"name": d.get("name")})
        if existing:
            print(f"Macro '{d.get('name')}' already exists -> id={existing.id}")
            # Optionally update fields if different
            updated = False
            if d.get("slug") and existing.slug != d.get("slug"):
                existing.slug = d.get("slug")
                updated = True
            if d.get("description") and existing.description != d.get("description"):
                existing.description = d.get("description")
                updated = True
            if d.get("image") and existing.image != d.get("image"):
                existing.image = d.get("image")
                updated = True
            if updated:
                await existing.save()
                print(f"Updated macro '{existing.name}' fields")
            continue

        m = MacroCategory(
            name=d.get("name"),
            slug=d.get("slug"),
            description=d.get("description"),
            image=d.get("image"),
        )
        await m.insert()
        print(f"Created macro '{m.name}' id={m.id}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
