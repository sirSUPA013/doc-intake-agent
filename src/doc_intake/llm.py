"""The model interface, plus a fake stand-in for tests.

The agent depends only on the small `LLM` interface here — production passes a
real client, tests pass `FakeLLM`, and the graph runs identically either way.
That seam is what makes the whole suite deterministic and free.

This holds for multimodal input too: a `Document` (image or PDF) can be attached
to a call, and `FakeLLM` simply ignores it — so vision tests stay just as
deterministic as text tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class Document:
    """A non-text input for the model: an image or a PDF."""

    kind: str          # "image" or "pdf"
    media_type: str    # e.g. "image/jpeg", "image/png", "application/pdf"
    data: bytes


class LLM(Protocol):
    """Anything with a `.complete(prompt, document=None) -> str` method."""

    def complete(self, prompt: str, document: Optional[Document] = None) -> str: ...


class FakeLLM:
    """A scripted model. Returns canned responses in order, one per call, and
    ignores any attached document (so multimodal tests stay deterministic).

    Records every prompt it receives so a test can assert how the agent called
    the model. (Test-only helper — not production observability.)
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str, document: Optional[Document] = None) -> str:
        self.calls.append(prompt)
        if not self._responses:
            raise AssertionError(
                "FakeLLM ran out of scripted responses — the agent called the "
                "model more times than this test expected."
            )
        return self._responses.pop(0)
