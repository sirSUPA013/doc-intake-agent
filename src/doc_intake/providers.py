"""Real model adapters that satisfy the `LLM` interface.

Kept in a separate module so the core package (graph, nodes, and the whole test
suite) never has to import the Anthropic SDK — only code that actually talks to a
live model pulls it in. This is the payoff of the dependency-injection seam:
`ClaudeLLM` drops in anywhere `FakeLLM` goes, and nothing else changes.
"""

from __future__ import annotations

import os

# Defaults to a fast, cheap model; override with the CLAUDE_MODEL env var.
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL") or "claude-haiku-4-5-20251001"


class ClaudeLLM:
    """Anthropic-backed model implementing `.complete(prompt) -> str`."""

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 1024) -> None:
        from anthropic import Anthropic  # lazy import: only needed in live mode

        self._client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # The messages API returns a list of content blocks; join the text ones.
        return "".join(b.text for b in message.content if b.type == "text")
