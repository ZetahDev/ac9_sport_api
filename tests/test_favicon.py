"""Test favicon functionality."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_favicon_exists():
    """Test that favicon.ico returns a valid response."""
    client = TestClient(app)
    response = client.get("/favicon.ico")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/x-icon"
    assert len(response.content) > 0


def test_favicon_content_type():
    """Test that favicon.ico has correct MIME type."""
    client = TestClient(app)
    response = client.get("/favicon.ico")
    
    assert response.headers["content-type"] == "image/x-icon"


def test_favicon_not_in_openapi_schema():
    """Test that favicon endpoint is not included in OpenAPI schema."""
    client = TestClient(app)
    response = client.get("/openapi.json")
    
    assert response.status_code == 200
    openapi_schema = response.json()
    
    # Favicon should not be in the paths since include_in_schema=False
    assert "/favicon.ico" not in openapi_schema.get("paths", {})