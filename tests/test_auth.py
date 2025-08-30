import sys
from pathlib import Path

# Ensure project root is on sys.path so `import app` works during pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from types import SimpleNamespace
from fastapi.testclient import TestClient
from app import models
from app.core import security
from app.main import app as fastapi_app
import app.routes.auth as auth_module
import app.deps as deps_module

# Disable startup handlers (init_beanie) to avoid real MongoDB connections during tests
fastapi_app.router.on_startup = []

client = TestClient(fastapi_app)


def _make_fake_user(email: str, password_plain: str):
    pw_hash = security.hash_password(password_plain)
    u = SimpleNamespace(
        email=email, password_hash=pw_hash, id="fakeid", is_superuser=False
    )
    return u


def test_register_creates_user(monkeypatch):
    # Provide a FakeUser class that supports class attribute `email` (for query expr)
    class FieldProxy:
        def __eq__(self, other):
            return ("eq", other)

    class FakeUser:
        email = FieldProxy()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def insert(self):
            self.id = "newid"
            return self

        @classmethod
        async def find_one(cls, *args, **kwargs):
            return None

    # Patch modules that reference User directly
    monkeypatch.setattr(models, "User", FakeUser)
    monkeypatch.setattr(auth_module, "User", FakeUser)
    monkeypatch.setattr(deps_module, "User", FakeUser)

    resp = client.post(
        "/auth/register", json={"email": "x@test.com", "password": "secret"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "x@test.com"
    assert "id" in data


def test_login_returns_token(monkeypatch):
    fake = _make_fake_user("login@test.com", "mypwd")

    class FieldProxy:
        def __eq__(self, other):
            return ("eq", other)

    class FakeUser:
        email = FieldProxy()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        @classmethod
        async def find_one(cls, *args, **kwargs):
            return fake

    monkeypatch.setattr(models, "User", FakeUser)
    monkeypatch.setattr(auth_module, "User", FakeUser)
    monkeypatch.setattr(deps_module, "User", FakeUser)

    resp = client.post(
        "/auth/login", json={"email": "login@test.com", "password": "mypwd"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_me_requires_valid_token(monkeypatch):
    fake = _make_fake_user("me@test.com", "pwd")

    class FieldProxy:
        def __eq__(self, other):
            return ("eq", other)

    class FakeUser:
        email = FieldProxy()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        @classmethod
        async def find_one(cls, *args, **kwargs):
            return fake

    monkeypatch.setattr(models, "User", FakeUser)
    monkeypatch.setattr(auth_module, "User", FakeUser)
    monkeypatch.setattr(deps_module, "User", FakeUser)

    token = security.create_access_token(subject=fake.email)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == fake.email
    assert data["id"] == "fakeid"


def test_update_profile_changes_email(monkeypatch):
    fake = _make_fake_user("old@test.com", "pwd")

    class FieldProxy:
        def __eq__(self, other):
            return ("eq", other)

    class FakeUser:
        email = FieldProxy()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def save(self):
            return self

        @classmethod
        async def find_one(cls, *args, **kwargs):
            # return the fake user for lookup by email
            return fake

    monkeypatch.setattr(models, "User", FakeUser)
    monkeypatch.setattr(auth_module, "User", FakeUser)
    monkeypatch.setattr(deps_module, "User", FakeUser)

    token = security.create_access_token(subject=fake.email)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.put("/auth/me", headers=headers, json={"email": "new@test.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "new@test.com"


def test_change_password_verifies_old_password(monkeypatch):
    fake = _make_fake_user("changepwd@test.com", "oldpwd")

    class FieldProxy:
        def __eq__(self, other):
            return ("eq", other)

    class FakeUser:
        email = FieldProxy()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def save(self):
            # emulate saving
            return self

        @classmethod
        async def find_one(cls, *args, **kwargs):
            return fake

    monkeypatch.setattr(models, "User", FakeUser)
    monkeypatch.setattr(auth_module, "User", FakeUser)
    monkeypatch.setattr(deps_module, "User", FakeUser)

    token = security.create_access_token(subject=fake.email)
    headers = {"Authorization": f"Bearer {token}"}
    # correct old password
    resp_ok = client.post(
        "/auth/change-password",
        headers=headers,
        json={"old_password": "oldpwd", "new_password": "newpwd"},
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json().get("ok") is True

    # incorrect old password should fail
    resp_fail = client.post(
        "/auth/change-password",
        headers=headers,
        json={"old_password": "wrong", "new_password": "newpwd"},
    )
    assert resp_fail.status_code == 401
