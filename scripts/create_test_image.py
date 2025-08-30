import base64, os

png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAmMB9b6wGZkAAAAASUVORK5CYII="
out_path = os.path.join(os.path.dirname(__file__), "test_image.png")
with open(out_path, "wb") as f:
    f.write(base64.b64decode(png_b64))
print("created", out_path)
