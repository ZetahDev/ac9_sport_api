import os
from fastapi import Header, HTTPException

API_KEY = os.getenv("API_KEY", "dev-secret-key")


def get_current_active_superuser(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"user": "admin"}
