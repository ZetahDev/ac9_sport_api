import os
import base64
from pathlib import Path
from fastapi import UploadFile

STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


async def upload_file_to_local(upload: UploadFile, folder: str = "products") -> str:
    target = STORAGE_DIR / folder
    target.mkdir(parents=True, exist_ok=True)
    dest = target / upload.filename
    content = await upload.read()
    with open(dest, "wb") as f:
        f.write(content)
    return f"/storage/{folder}/{upload.filename}"


def save_base64_image(b64_string: str, filename: str, folder: str = "products") -> str:
    target = STORAGE_DIR / folder
    target.mkdir(parents=True, exist_ok=True)
    dest = target / filename
    header, _, data = b64_string.partition(",")
    raw = base64.b64decode(data if data else b64_string)
    with open(dest, "wb") as f:
        f.write(raw)
    return f"/storage/{folder}/{filename}"


async def delete_file_local(url: str) -> bool:
    try:
        # url expected like /storage/folder/filename
        p = Path(url.lstrip("/"))
        if p.exists():
            p.unlink()
            return True
    except Exception:
        return False
    return False
