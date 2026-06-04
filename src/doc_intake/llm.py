"""The model interface, plus a fake stand-in for tests.

The single most important testing idea in this project lives here. Nodes never
import a concrete model client — they depend on the small `LLM` interface below.
That dependency injection is what lets every test swap in `FakeLLM` and run the
whole agent with zero network calls and perfectly deterministic output. The
non-determinism of a real LLM is the thing agent tests have to control; mocking
the model out is how you control it.
"""

from __future__ import annotations

from typing import Protocol


class LLM(Protocol):
    """Anything with a `.complete(prompt) -> str` method is a usable model."""

    def complete(self, prompt: str) -> str: ...


class FakeLLM:
    """A scripted model. Returns canned responses in order, one per call.

    It also records every prompt it receives, so a test can assert *how many
    times* and *with what* the agent called the model — a lightweight version of
    the call / token instrumentation the role asks for.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self._responses:
            raise AssertionError(
                "FakeLLM ran out of scripted responses — the agent called the "
                "model more times than this test expected."
            )
        return self._responses.pop(0)
