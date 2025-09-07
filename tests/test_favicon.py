"""
Tests for favicon and web app manifest functionality.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client for the FastAPI app."""
    return TestClient(app)


def test_favicon_ico_endpoint(client):
    """Test that favicon.ico is served correctly."""
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/x-icon"
    assert len(response.content) > 0


def test_favicon_ico_head_request(client):
    """Test that favicon.ico responds to HEAD requests."""
    response = client.head("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/x-icon"


def test_webmanifest_endpoint(client):
    """Test that site.webmanifest is served correctly."""
    response = client.get("/site.webmanifest")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/manifest+json"
    
    # Verify it's valid JSON with expected structure
    data = response.json()
    assert "name" in data
    assert "short_name" in data
    assert "icons" in data
    assert data["name"] == "AC9 Sport"
    assert data["short_name"] == "AC9Sport"
    assert isinstance(data["icons"], list)
    assert len(data["icons"]) > 0


def test_manifest_json_alternative_endpoint(client):
    """Test that manifest.json serves the same content as site.webmanifest."""
    manifest_response = client.get("/site.webmanifest")
    json_response = client.get("/manifest.json")
    
    assert manifest_response.status_code == 200
    assert json_response.status_code == 200
    assert manifest_response.json() == json_response.json()


def test_static_icons_accessible(client):
    """Test that static icon files are accessible."""
    icons_to_test = [
        "/static/icons/icon-16x16.png",
        "/static/icons/icon-32x32.png", 
        "/static/icons/icon-192x192.png"
    ]
    
    for icon_path in icons_to_test:
        response = client.get(icon_path)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert len(response.content) > 0


def test_head_requests_for_manifest(client):
    """Test that manifest endpoints respond to HEAD requests."""
    response = client.head("/site.webmanifest")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/manifest+json"
    
    response = client.head("/manifest.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/manifest+json"


def test_manifest_icon_paths_are_valid(client):
    """Test that icon paths referenced in manifest are accessible."""
    response = client.get("/site.webmanifest")
    assert response.status_code == 200
    
    data = response.json()
    for icon in data["icons"]:
        icon_path = icon["src"]
        icon_response = client.get(icon_path)
        assert icon_response.status_code == 200, f"Icon {icon_path} should be accessible"
        assert icon_response.headers["content-type"] == "image/png"