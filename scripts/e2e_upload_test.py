#!/usr/bin/env python3
"""
e2e_upload_test.py

Simple, standalone script to test macro category image upload endpoint.

Usage examples:
  python scripts/e2e_upload_test.py
  python scripts/e2e_upload_test.py --base http://127.0.0.1:8000 --image ../ac9_sport_front/public/images/logo.jpg
  python scripts/e2e_upload_test.py --api-key mykey

The script will:
 - GET /macro-categories
 - pick the first macro's id
 - POST multipart/form-data file to /macro-categories/{id}/upload-image
 - print response JSON
 - verify that the returned image path exists under the API `storage/` folder

Note: This script only creates and runs local HTTP requests. It does not modify the repo files except reading the image and checking storage.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import requests


def main():
    parser = argparse.ArgumentParser(
        description="E2E upload tester for macro category image endpoint"
    )
    parser.add_argument(
        "--base",
        default="http://127.0.0.1:8000",
        help="Base URL of the API (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Path to image file to upload (default: workspace ac9_sport_front/public/images/logo.jpg)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional X-API-KEY header value for admin access",
    )
    parser.add_argument("--email", default=None, help="Admin email to login (optional)")
    parser.add_argument(
        "--password", default=None, help="Admin password to login (optional)"
    )
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write a .env file with minimal credentials (developer only)",
    )
    args = parser.parse_args()

    # Resolve sensible defaults relative to this script location
    script_root = Path(__file__).resolve().parents[1]  # ac9_sport_api/
    workspace_root = script_root.parent  # ac_store/

    default_image = (
        workspace_root / "ac9_sport_front" / "public" / "images" / "logo.jpg"
    )
    image_path = (
        Path(args.image).expanduser().resolve() if args.image else default_image
    )

    if not image_path.exists():
        print(f"ERROR: image not found at {image_path}")
        sys.exit(2)

    base = args.base.rstrip("/")

    headers = {}
    if args.api_key:
        headers["X-API-KEY"] = args.api_key
    # Login with credentials to obtain Bearer token if provided
    email = args.email
    password = args.password
    if email and password:
        login_url = base + "/auth/login"
        try:
            lr = requests.post(
                login_url, json={"email": email, "password": password}, timeout=10
            )
        except Exception as e:
            print("ERROR: login request failed:", e)
            sys.exit(10)
        if lr.status_code != 200:
            print("Login failed:", lr.status_code, lr.text)
            sys.exit(11)
        try:
            lj = lr.json()
        except Exception:
            print("Login response not JSON:", lr.text)
            sys.exit(12)
        token = lj.get("access_token") or (
            lj.get("data") and lj.get("data").get("access_token")
        )
        if not token:
            print("Login did not return access_token; aborting")
            sys.exit(13)
        headers["Authorization"] = f"Bearer {token}"
        print("Logged in as", email)

    # Optionally write .env to store credentials locally (developer convenience)
    if args.write_env:
        env_path = script_root / ".env"
        print("Writing credentials to:", env_path)
        # Only write the minimal keys; avoid echoing password
        content_lines = [
            f"API_BASE={base}",
            f"ADMIN_EMAIL={email or ''}",
            f"# ADMIN_PASS is present — keep this file out of version control\n",
        ]
        # write password in a separate line if provided
        if password:
            content_lines.insert(2, f"ADMIN_PASS={password}")
        env_path.write_text("\n".join(content_lines))
        print("Wrote .env (ensure it's added to .gitignore)")

    print("GET", base + "/macro-categories")
    try:
        r = requests.get(base + "/macro-categories", headers=headers, timeout=10)
    except Exception as e:
        print("ERROR: could not reach API:", e)
        sys.exit(3)

    if r.status_code != 200:
        print("GET /macro-categories ->", r.status_code, r.text)
        sys.exit(4)

    macros = r.json()
    if not macros:
        print("No macro categories available to test.")
        sys.exit(5)

    macro_id = macros[0].get("id")
    print("Using macro id:", macro_id)

    upload_url = f"{base}/macro-categories/{macro_id}/upload-image"
    print("Uploading to:", upload_url)

    # choose mime type from extension for correct server validation
    ext = image_path.suffix.lower()
    mime = "application/octet-stream"
    if ext in (".png",):
        mime = "image/png"
    elif ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif ext in (".webp",):
        mime = "image/webp"
    with image_path.open("rb") as fh:
        files = {"file": (image_path.name, fh, mime)}
        try:
            resp = requests.post(upload_url, files=files, headers=headers, timeout=30)
        except Exception as e:
            print("ERROR: upload request failed:", e)
            sys.exit(6)

    print("Upload status:", resp.status_code)
    try:
        data = resp.json()
    except Exception:
        print("Upload response text:", resp.text)
        sys.exit(7)

    print("Response JSON:", data)
    image_field = (
        data.get("image") or data.get("data") and data.get("data").get("image")
    )
    if not image_field:
        print("No image path returned by server; aborting check.")
        sys.exit(8)

    # Expect image_field like /storage/filename.ext
    fname = Path(image_field).name

    # Check multiple plausible storage locations (app/storage, api/storage, repo root storage)
    candidates = [
        script_root / "app" / "storage" / fname,
        script_root / "storage" / fname,
        script_root.parent / "storage" / fname,
    ]
    found = False
    for p in candidates:
        print("Checking:", p)
        if p.exists():
            print("Found at:", p)
            found = True
            break

    if found:
        print("SUCCESS: file uploaded and present in storage")
        sys.exit(0)
    else:
        print("FAIL: file not found in any known storage locations")
        sys.exit(9)


if __name__ == "__main__":
    main()
