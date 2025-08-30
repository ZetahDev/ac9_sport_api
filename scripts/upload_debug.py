#!/usr/bin/env python3
"""upload_debug.py
Simple script to reproduce and debug macro-category image upload.
Creates clear output (status, response, exception trace) and checks common storage locations.
"""
import argparse
import sys
import traceback
from pathlib import Path
import requests


def mime_for_path(p: Path):
    ext = p.suffix.lower()
    if ext == ".png":
        return "image/png"
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".webp":
        return "image/webp"
    return "application/octet-stream"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--image", default=None)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    script_root = Path(__file__).resolve().parents[1]
    if args.image:
        image_path = Path(args.image).expanduser().resolve()
    else:
        image_path = script_root / "scripts" / "test_image.png"

    if not image_path.exists():
        print(f"ERROR: image not found at {image_path}")
        sys.exit(2)

    base = args.base.rstrip("/")
    headers = {}
    if args.api_key:
        headers["X-API-KEY"] = args.api_key

    print("GET", base + "/health")
    try:
        r = requests.get(base + "/health", timeout=5)
        print("health ->", r.status_code, r.text)
    except Exception as e:
        print("health request failed:", repr(e))
        traceback.print_exc()

    print("GET", base + "/macro-categories")
    try:
        r = requests.get(base + "/macro-categories", headers=headers, timeout=10)
        print("GET /macro-categories ->", r.status_code)
        macros = r.json() if r.status_code == 200 else None
        print("macros count", len(macros) if macros else None)
    except Exception as e:
        print("GET /macro-categories failed:", repr(e))
        traceback.print_exc()
        macros = None

    macro_id = None
    if macros:
        macro_id = macros[0].get("id")
        print("Using macro id:", macro_id)
    else:
        print("No macros available; aborting upload test.")
        sys.exit(3)

    upload_url = f"{base}/macro-categories/{macro_id}/upload-image"
    print("Uploading to:", upload_url)

    mime = mime_for_path(image_path)
    try:
        with image_path.open("rb") as fh:
            files = {"file": (image_path.name, fh, mime)}
            resp = requests.post(upload_url, files=files, headers=headers, timeout=30)
        print("Upload status:", resp.status_code)
        try:
            print("Response JSON:", resp.json())
        except Exception:
            print("Response text:", resp.text)
    except Exception as e:
        print("ERROR: upload request failed:", type(e), e)
        traceback.print_exc()

    # Check multiple storage paths
    image_field = None
    try:
        data = resp.json()
        image_field = data.get("image") or (
            data.get("data") and data.get("data").get("image")
        )
    except Exception:
        pass

    if not image_field:
        print("Server did not return image path; cannot check storage locations.")
        sys.exit(0)

    fname = Path(image_field).name
    candidates = [
        script_root / "app" / "storage" / fname,
        script_root / "storage" / fname,
        script_root.parent / "storage" / fname,
    ]
    print("Looking for file name:", fname)
    for p in candidates:
        print("Candidate:", p, "exists:", p.exists())


if __name__ == "__main__":
    main()
