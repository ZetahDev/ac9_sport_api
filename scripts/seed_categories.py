#!/usr/bin/env python3
"""
Seed script: create/update categories with given names and assign them to a macro.

Usage:
  python scripts/seed_categories.py --macro "Deportivo"

If the macro doesn't exist, script will exit with an error. The script is idempotent.
"""
import asyncio
import os
import sys
from pathlib import Path
import argparse

from dotenv import load_dotenv


def _prep_path():
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    return package_root


DEFAULT_CATEGORIES = [
    "tenis",
    "petos",
    "guayos",
    "sintetica",
    "futsal",
    "indumentaria",
]


async def main():
    package_root = _prep_path()
    dotenv_path = package_root / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    parser = argparse.ArgumentParser()
    parser.add_argument("--macro", required=True, help="Macro category name to assign")
    parser.add_argument("--categories", nargs="*", default=DEFAULT_CATEGORIES)
    parser.add_argument(
        "--file",
        help="Optional JSON file with categories array: [{name,slug,description,image}]",
        default=None,
    )
    args = parser.parse_args()

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

    macro = await MacroCategory.find_one({"name": args.macro})
    if not macro:
        print(
            f"Macro '{args.macro}' not found. Run seed_macro_categories first or create the macro."
        )
        await client.close()
        sys.exit(1)

    # Build category definitions
    if args.file:
        import json

        with open(args.file, "r", encoding="utf-8") as fh:
            try:
                cat_defs = json.load(fh)
            except Exception:
                print("Failed to parse JSON file for categories.")
                client.close()
                sys.exit(1)
    else:
        # convert simple names to dicts
        cat_defs = [
            {"name": n, "slug": None, "description": None, "image": None}
            for n in args.categories
        ]

    for cdef in cat_defs:
        cname = cdef.get("name")
        c = await Category.find_one({"name": cname})
        if c:
            updated = False
            if c.macro_category_id != macro.id:
                c.macro_category_id = macro.id
                updated = True
            if cdef.get("description") and c.description != cdef.get("description"):
                c.description = cdef.get("description")
                updated = True
            if updated:
                await c.save()
                print(f"Updated category '{cname}' -> macro id {macro.id}")
            else:
                print(
                    f"Category '{cname}' already assigned to macro {macro.name} ({macro.id})"
                )
            continue

        nc = Category(
            name=cname, macro_category_id=macro.id, description=cdef.get("description")
        )
        await nc.insert()
        print(
            f"Created category '{cname}' id={nc.id} assigned to macro {macro.name} ({macro.id})"
        )

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
