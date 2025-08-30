import os
from app.routes.products import resolve_public_image_url


def test_none_and_non_gcs():
    assert resolve_public_image_url(None) is None
    assert (
        resolve_public_image_url("https://example.com/image.jpg")
        == "https://example.com/image.jpg"
    )
    assert resolve_public_image_url("/local/path.jpg") == "/local/path.jpg"


def test_with_s3_public_url(monkeypatch):
    monkeypatch.setenv("S3_PUBLIC_URL", "https://cdn.example.com")
    out = resolve_public_image_url("gcs://products/1.jpg")
    assert out == "https://cdn.example.com/products/1.jpg"


def test_with_bucket(monkeypatch):
    monkeypatch.delenv("S3_PUBLIC_URL", raising=False)
    monkeypatch.setenv("S3_BUCKET", "my-bucket")
    out = resolve_public_image_url("gcs://products/2.jpg")
    assert out == "https://my-bucket.s3.amazonaws.com/products/2.jpg"


def test_fallback_no_env(monkeypatch):
    monkeypatch.delenv("S3_PUBLIC_URL", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)
    out = resolve_public_image_url("gcs://products/3.jpg")
    assert out == "/products/3.jpg"
