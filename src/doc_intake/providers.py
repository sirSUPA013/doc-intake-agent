"""Real model adapters that satisfy the `LLM` interface.

Kept separate so the core package (graph, nodes, tests) never imports the
Anthropic SDK — only code that talks to a live model does. `ClaudeLLM` drops in
anywhere `FakeLLM` goes, including for image/PDF (vision) input.
"""

from __future__ import annotations

import base64
import os

from doc_intake.llm import Document

# Sonnet by default — more reliable on messy photos/scans for the live demo.
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"


class ClaudeLLM:
    """Anthropic-backed model implementing `.complete(prompt, document=None)`.

    With a `Document`, it sends an image or PDF content block alongside the prompt
    — Claude reads the document itself (no separate OCR engine), including scanned
    or handwritten pages.
    """

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 4096) -> None:
        from anthropic import Anthropic  # lazy import: only needed in live mode

        self._client = Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str, document: Document | None = None) -> str:
        if document is None:
            content: object = prompt
        else:
            b64 = base64.standard_b64encode(document.data).decode("ascii")
            if document.kind == "pdf":
                block = {"type": "document",
                         "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
            else:
                block = {"type": "image",
                         "source": {"type": "base64", "media_type": document.media_type, "data": b64}}
            content = [block, {"type": "text", "text": prompt}]

        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(b.text for b in message.content if b.type == "text")
