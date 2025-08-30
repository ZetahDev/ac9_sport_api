from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import timedelta, datetime, timezone
from typing import Optional, Annotated

from ..models import User
from ..core.security import hash_password, verify_password, create_access_token
import inspect
from ..deps import get_current_user

router = APIRouter()


NOT_AUTHENTICATED = "Not authenticated"
INVALID_CREDENTIALS = "Invalid credentials"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    # Accept either email (preferred) or legacy username (some clients still send this)
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str


class UpdateProfileIn(BaseModel):
    # Allow partial updates: any of these may be omitted
    email: Optional[EmailStr] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    country: Optional[str] = None


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/register", response_model=dict)
async def register(data: RegisterIn):
    existing = await User.find_one(User.email == data.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(email=data.email, password_hash=hash_password(data.password))
    inserted = user.insert()
    if inspect.isawaitable(inserted):
        await inserted
    return {"email": user.email, "id": str(user.id)}


@router.post("/token", response_model=TokenOut)
async def token(data: LoginIn):
    # Support either email or legacy username field
    identifier = data.email or data.username
    if not identifier:
        raise HTTPException(status_code=422, detail="email or username required")

    user = await User.find_one(User.email == identifier)
    if not user:
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    access_token = create_access_token(
        subject=user.email, expires_delta=timedelta(hours=1)
    )
    return {"access_token": access_token, "token_type": "bearer"}


from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import timedelta, datetime, timezone
from typing import Optional
import inspect

from ..models import User
from ..core.security import hash_password, verify_password, create_access_token
from ..deps import get_current_user

router = APIRouter()


NOT_AUTHENTICATED = "Not authenticated"
INVALID_CREDENTIALS = "Invalid credentials"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileIn(BaseModel):
    # Allow partial updates: any of these may be omitted
    email: Optional[EmailStr] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    country: Optional[str] = None


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/register", response_model=dict)
async def register(data: RegisterIn):
    existing = await User.find_one(User.email == data.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(email=data.email, password_hash=hash_password(data.password))
    # support both sync and async insert implementations (tests may patch sync fakes)
    inserted = user.insert()
    if inspect.isawaitable(inserted):
        await inserted
    return {"email": user.email, "id": str(user.id)}


@router.post("/token", response_model=TokenOut)
async def token(data: LoginIn):
    user = await User.find_one(User.email == data.email)
    if not user:
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    access_token = create_access_token(
        subject=user.email, expires_delta=timedelta(hours=1)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=TokenOut)
async def login_alias(data: LoginIn):
    """Alias for /token for clients that expect /login."""
    return await token(data)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "is_superuser": current_user.is_superuser,
        "firstName": getattr(current_user, "first_name", None),
        "lastName": getattr(current_user, "last_name", None),
        "phone": getattr(current_user, "phone", None),
        "address": getattr(current_user, "address", None),
        "city": getattr(current_user, "city", None),
        "state": getattr(current_user, "state", None),
        "zipCode": getattr(current_user, "zip_code", None),
        "country": getattr(current_user, "country", None),
    }


# Compatibility endpoints expected by older frontend paths
@router.get("/users/me/profile")
async def users_me_profile(current_user: User = Depends(get_current_user)):
    """Compatibility wrapper: GET /users/me/profile -> returns similar payload as /me"""
    if not current_user:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "fullName": (
            (getattr(current_user, "first_name", "") or "")
            + " "
            + (getattr(current_user, "last_name", "") or "")
        ).strip()
        or None,
        "firstName": getattr(current_user, "first_name", None),
        "lastName": getattr(current_user, "last_name", None),
        "phone": getattr(current_user, "phone", None),
        "address": getattr(current_user, "address", None),
        "city": getattr(current_user, "city", None),
        "state": getattr(current_user, "state", None),
        "zipCode": getattr(current_user, "zip_code", None),
        "country": getattr(current_user, "country", None),
    }


@router.put("/users/me/profile")
async def users_me_profile_update(
    data: UpdateProfileIn, current_user: User = Depends(get_current_user)
):
    """Compatibility wrapper: PUT /users/me/profile -> reuse update_me logic"""
    return await update_me(data, current_user)


@router.get("/users/me/checkout-info")
async def users_me_checkout_info(current_user: User = Depends(get_current_user)):
    """Return minimal checkout info compatible with frontend expectation."""
    if not current_user:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)
    # Provide fields that frontend expects, defaulting to empty strings
    return {
        "firstName": "",
        "lastName": "",
        "email": current_user.email,
        "phone": "",
        "address": "",
        "city": "",
        "state": "",
        "zipCode": "",
        "country": "",
    }


@router.put("/me")
async def update_me(
    data: UpdateProfileIn,
    current_user: Annotated[Optional[User], Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)

    # allow changing email if not used by another user
    if data.email and data.email != current_user.email:
        existing = await User.find_one(User.email == data.email)
        # if an existing user is returned, allow if it's the same user (id match)
        if existing and str(getattr(existing, "id", "")) != str(
            getattr(current_user, "id", "")
        ):
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = data.email

    # Map camelCase input fields to model snake_case attributes
    field_map = {
        "firstName": "first_name",
        "lastName": "last_name",
        "phone": "phone",
        "address": "address",
        "city": "city",
        "state": "state",
        "zipCode": "zip_code",
        "country": "country",
    }

    # Apply partial updates only for fields explicitly provided
    for input_field, model_field in field_map.items():
        if getattr(data, input_field, None) is not None:
            setattr(current_user, model_field, getattr(data, input_field))

    current_user.updated_at = datetime.now(tz=timezone.utc)
    # Some test fakes use simple objects without save(); call save only when present
    if hasattr(current_user, "save"):
        saved = current_user.save()
        if inspect.isawaitable(saved):
            await saved
    # Return an extended profile payload to reflect updated fields
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "firstName": getattr(current_user, "first_name", None),
        "lastName": getattr(current_user, "last_name", None),
        "phone": getattr(current_user, "phone", None),
        "address": getattr(current_user, "address", None),
        "city": getattr(current_user, "city", None),
        "state": getattr(current_user, "state", None),
        "zipCode": getattr(current_user, "zip_code", None),
        "country": getattr(current_user, "country", None),
    }


@router.post("/change-password")
async def change_password(
    data: ChangePasswordIn,
    current_user: Annotated[Optional[User], Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)
    # verify old password
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    # set new password
    current_user.password_hash = hash_password(data.new_password)
    current_user.updated_at = datetime.now(tz=timezone.utc)
    # Some test fakes use simple objects without save(); call save only when present
    if hasattr(current_user, "save"):
        saved = current_user.save()
        if inspect.isawaitable(saved):
            await saved
    return {"ok": True}
