#!/usr/bin/env python3
"""
Migration: reconcile Category.macro_category_id values to new MacroCategory.id UUIDs.

Strategy:
- For each Category with macro_category_id set:
  - If a MacroCategory exists with id == macro_category_id, OK.
  - Else try to find a MacroCategory where str(m._id) == macro_category_id (old ObjectId), or m.slug == macro_category_id, or m.name == macro_category_id.
  - If a match is found, update Category.macro_category_id to the MacroCategory.id (UUID).

Usage:
  python scripts/migrate_macro_refs.py [--dry-run]

This is conservative and prints actions before modifying.
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


async def main():
    package_root = _prep_path()
    dotenv_path = package_root / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying them"
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

    cats = await Category.find_many({}).to_list()
    macros = await MacroCategory.find_many({}).to_list()
    macro_by_id = {m.id: m for m in macros}
    # old _id mapping (ObjectId) as string
    macro_by_oid = {str(getattr(m, "_id", "")): m for m in macros}
    macro_by_slug = {m.slug: m for m in macros if m.slug}
    macro_by_name = {m.name: m for m in macros}

    changes = []
    for c in cats:
        mid = c.macro_category_id
        if not mid:
            continue
        # already points to new uuid
        if mid in macro_by_id:
            continue
        found = None
        if mid in macro_by_oid:
            found = macro_by_oid[mid]
        if not found and mid in macro_by_slug:
            found = macro_by_slug[mid]
        if not found and mid in macro_by_name:
            found = macro_by_name[mid]
        if found:
            changes.append((c, mid, found.id))

    print(f"Planned changes: {len(changes)}")
    for c, old, new in changes:
        print(f"Category {c.name} ({c.id}): {old} -> {new}")

    if args.dry_run:
        print("Dry run; exiting without applying changes")
        client.close()
        return

    for c, old, new in changes:
        c.macro_category_id = new
        await c.save()
        print(f"Updated category {c.name} ({c.id}) macro -> {new}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
