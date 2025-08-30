import sys
from pathlib import Path
import pytest
from types import SimpleNamespace

# Ensure project root is on sys.path so `import app` works during pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app import models
import app.routes.auth as auth_module
import app.deps as deps_module
from app.core import security

# Disable startup handlers (init_beanie) to avoid real MongoDB connections during tests
fastapi_app.router.on_startup = []


@pytest.fixture(scope="session")
def app():
    return fastapi_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def fake_user():
    def _make(
        email: str = "test@example.com", password: str = "pwd", is_super: bool = False
    ):
        return SimpleNamespace(
            email=email,
            password_hash=security.hash_password(password),
            id="fakeid",
            is_superuser=is_super,
        )

    return _make


@pytest.fixture
def patch_fake_user_class(monkeypatch):
    """Monkeypatch a FakeUser class into modules that reference `User` to avoid Beanie descriptors during tests."""

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

    monkeypatch.setattr(models, "User", FakeUser)
    monkeypatch.setattr(auth_module, "User", FakeUser)
    monkeypatch.setattr(deps_module, "User", FakeUser)

    yield FakeUser
