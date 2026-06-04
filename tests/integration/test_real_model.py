"""Opt-in integration test against the real Anthropic model.

Skipped unless ANTHROPIC_API_KEY is set AND you run `pytest -m integration`.
Costs a few cents per run. This is the one thing FakeLLM cannot prove: that the
real model's output actually drives the graph to a valid, schema-checked result.
"""

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="set ANTHROPIC_API_KEY to run the live integration test",
    ),
]

SAMPLE = """ACME Corp
Invoice #42   Date: 2026-05-01
Bill to: Sam Yandow
Total due: $1,250.00
"""


def test_real_model_extracts_valid_doc():
    from doc_intake import build_agent
    from doc_intake.providers import ClaudeLLM

    result = build_agent(ClaudeLLM()).invoke({"raw_text": SAMPLE})

    assert result["status"] == "done"
    assert result["extracted"]["doc_type"]          # non-empty type
    assert result["summary"].strip() != ""          # a real summary came back
