"""Real model adapters that satisfy the `LLM` interface.

Kept separate so the core package (graph, nodes, tests) never imports the
Anthropic SDK — only code that talks to a live model does. `ClaudeLLM` drops in
anywhere `FakeLLM` goes, including for image/PDF (vision) input.
"""

from __future__ import annotations

import base64
import io
import os

from doc_intake.llm import Document

# Sonnet by default — more reliable on messy photos/scans for the live demo.
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"

# Claude downsizes images to ~1568px on the long edge anyway, so sending a full
# multi-MB phone photo just wastes upload time. Shrink large images first.
_MAX_IMAGE_DIM = 1568


def _downscale_image(data: bytes, media_type: str) -> tuple[bytes, str]:
    """Return (bytes, media_type), downscaled to <=_MAX_IMAGE_DIM on the long edge
    if larger. Falls back to the original on any error or if Pillow is missing."""
    try:
        from PIL import Image
    except Exception:
        return data, media_type
    try:
        img = Image.open(io.BytesIO(data))
        if max(img.size) <= _MAX_IMAGE_DIM:
            return data, media_type
        img.thumbnail((_MAX_IMAGE_DIM, _MAX_IMAGE_DIM))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return data, media_type


class ClaudeLLM:
    """Anthropic-backed model implementing `.complete(prompt, document=None)`.

    With a `Document`, it sends an image or PDF content block alongside the prompt
    — Claude reads the document itself (no separate OCR engine), including scanned
    or handwritten pages. Large images are downscaled first for speed.
    """

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 4096) -> None:
        from anthropic import Anthropic  # lazy import: only needed in live mode

        self._client = Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str, document: Document | None = None) -> str:
        if document is None:
            content: object = prompt
        elif document.kind == "pdf":
            b64 = base64.standard_b64encode(document.data).decode("ascii")
            block = {"type": "document",
                     "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
            content = [block, {"type": "text", "text": prompt}]
        else:
            data, media_type = _downscale_image(document.data, document.media_type)
            b64 = base64.standard_b64encode(data).decode("ascii")
            block = {"type": "image",
                     "source": {"type": "base64", "media_type": media_type, "data": b64}}
            content = [block, {"type": "text", "text": prompt}]

        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(b.text for b in message.content if b.type == "text")
