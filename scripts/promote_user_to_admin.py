#!/usr/bin/env python3
"""
Promote a user to superuser (is_superuser=True) by email.

Usage:
  python scripts/promote_user_to_admin.py --email admin@ac9sport.com

If the user does not exist, script will exit with a non-zero code unless --create is provided.
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
    parser.add_argument("--email", required=False, default="admin@ac9sport.com")
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create the user if it doesn't exist (password required via --password)",
    )
    parser.add_argument(
        "--password",
        required=False,
        help="Password for created user (only used with --create)",
    )
    args = parser.parse_args()

    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from app.models import User, Category, Subcategory, Product, MacroCategory
    from datetime import datetime, timezone

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

    u = await User.find_one({"email": args.email})
    if not u:
        if not args.create:
            print(f"User with email {args.email} not found.")
            client.close()
            sys.exit(1)
        # create user
        if not args.password:
            print("--password is required when using --create")
            client.close()
            sys.exit(1)
        # Note: password hashing should match your auth implementation; here we store a placeholder hash.
        # For safety, you may want to integrate with your existing password hasher.
        from hashlib import sha256

        ph = sha256(args.password.encode("utf-8")).hexdigest()
        u = User(
            email=args.email,
            password_hash=ph,
            is_active=True,
            is_superuser=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await u.insert()
        print(f"Created and promoted user {args.email} as superuser (id={u.id})")
        client.close()
        return

    if u.is_superuser:
        print(f"User {args.email} is already superuser (id={u.id})")
        client.close()
        return

    u.is_superuser = True
    u.updated_at = datetime.now(timezone.utc)
    await u.save()
    print(f"Promoted {args.email} to superuser (id={u.id})")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
