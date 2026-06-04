"""Unit tests for provider helpers that don't need the live model."""

import io

from PIL import Image

from doc_intake.providers import _MAX_IMAGE_DIM, _downscale_image


def _png(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_downscale_shrinks_large_image():
    big = _png(4000, 3000)
    out, media = _downscale_image(big, "image/png")
    w, h = Image.open(io.BytesIO(out)).size
    assert max(w, h) <= _MAX_IMAGE_DIM
    assert len(out) < len(big)
    assert media == "image/jpeg"


def test_downscale_leaves_small_image_unchanged():
    small = _png(800, 600)
    out, media = _downscale_image(small, "image/png")
    assert out == small
    assert media == "image/png"
