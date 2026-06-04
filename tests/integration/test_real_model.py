"""Opt-in integration test against the real Anthropic model.

Skipped unless ANTHROPIC_API_KEY is set AND you run `pytest -m integration`.
Costs a few cents per run. This is the one thing FakeLLM cannot prove: that the
real model's output actually drives the graph to a valid, schema-checked result.
"""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()  # pick up a local .env so the key is visible to the skipif below

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


def test_real_model_extracts_from_image():
    """Vision path: a real model reads an invoice *image* into schema-valid data.

    Asserts on shape/validity (not exact OCR values) so it isn't flaky against a
    non-deterministic model.
    """
    import pathlib

    from doc_intake import Document, build_agent
    from doc_intake.providers import ClaudeLLM

    png = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "sample-invoice.png"
    result = build_agent(ClaudeLLM()).invoke(
        {"document": Document("image", "image/png", png.read_bytes())}
    )

    assert result["status"] == "done"
    assert result["extracted"]["doc_type"] == "invoice"
    assert isinstance(result["extracted"]["total_amount"], (int, float))
    assert result["extracted"]["total_amount"] > 0
