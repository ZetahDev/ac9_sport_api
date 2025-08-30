import os
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .core.security import decode_access_token
from .models import User


API_KEY = os.getenv("API_KEY", "dev-secret-key")

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """Return a User document if a valid Bearer token is provided, otherwise None."""
    if not authorization:
        return None
    token = authorization.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = await User.find_one(User.email == sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_active_superuser(
    x_api_key: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Allow access if X-API-KEY matches API_KEY or the JWT belongs to a superuser."""
    # Admin backdoor via header
    if x_api_key and x_api_key == API_KEY:
        return {"user": "admin"}

    if current_user and getattr(current_user, "is_superuser", False):
        return current_user

    raise HTTPException(status_code=401, detail="Unauthorized")
