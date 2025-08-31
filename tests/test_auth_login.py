import os
import pytest

# Ensure the app doesn't try to connect to a real MongoDB during import
os.environ.setdefault("MONGO_URI", "")

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def patch_auth_dependencies(monkeypatch):
    """Patch DB and security helpers so tests run deterministically without a DB."""

    # Import the auth module after MONGO_URI is set
    from ac9_sport_api.app.routes import auth as auth_module

    # Create a MockUser that safely supports attribute access like `User.email` and
    # provides an async `find_one` that returns a mock instance.
    class _Field:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            # Return a simple tuple that our fake find_one can accept
            return (self.name, other)

    class MockUser:
        email = _Field("email")
        password_hash = "fake-hash"
        id = "mock-id"
        is_superuser = True

        def __init__(self):
            self.email = "admin@ac9sport.com"
            self.password_hash = "fake-hash"
            self.id = "mock-id"

        def save(self):
            return None

        @classmethod
        async def find_one(cls, query):
            # Accept either a tuple (field, value) or any other query and return an instance
            return MockUser()

    async def fake_verify_password(password, stored_hash):
        return True

    def fake_create_access_token(subject, expires_delta=None):
        return "mock-token"

    # Replace the module's User with our MockUser
    monkeypatch.setattr(auth_module, "User", MockUser)
    monkeypatch.setattr(auth_module, "verify_password", fake_verify_password)
    monkeypatch.setattr(auth_module, "create_access_token", fake_create_access_token)

    yield


def test_login_success_caps_logs(caplog):
    """POST valid JSON -> returns token and logs nothing critical."""
    from ac9_sport_api.app.main import app

    client = TestClient(app)

    payload = {"email": "admin@ac9sport.com", "password": "ac9sportKstro+"}

    with caplog.at_level("INFO"):
        resp = client.post("/auth/login", json=payload)

    # Should succeed and return a token
    assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data.get("access_token") == "mock-token"
    assert data.get("token_type") == "bearer"

    # Print captured log records to the test output for debugging visibility
    for rec in caplog.records:
        print(f"LOG [{rec.levelname}] {rec.name}: {rec.getMessage()}")


def test_login_malformed_json_logs(caplog):
    """Send an invalid JSON body and assert the server returns 422 and logs appropriately."""
    from ac9_sport_api.app.main import app

    client = TestClient(app)

    with caplog.at_level("WARNING"):
        # send invalid JSON (plain text) with JSON content-type
        resp = client.post(
            "/auth/login",
            data="not-a-json",
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 422

    # Print captured logs so we can inspect what happened on the server
    for rec in caplog.records:
        print(f"LOG [{rec.levelname}] {rec.name}: {rec.getMessage()}")
