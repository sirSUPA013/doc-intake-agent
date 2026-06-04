"""Eval set — runs every document image in tests/fixtures/ through the REAL model.

This is the guard that mocked tests can't be: it exercises the live model on a
spread of real document types (invoice, receipt, letter, handwritten note) and
asserts each reaches a schema-valid result. It's what would have caught the
handwritten-note bug before a user did — a real note, through the real model,
must end in `done`.

Opt-in: skipped without a key; run with `pytest -m integration` (costs a few
cents per image). Asserts on shape/validity, not exact OCR values, so it isn't flaky.
"""

import os
import pathlib

import pytest
from dotenv import load_dotenv

load_dotenv()

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"
IMAGES = sorted(FIXTURES.glob("*.png"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="set ANTHROPIC_API_KEY to run the eval set",
    ),
]


@pytest.mark.parametrize("image", IMAGES, ids=[p.stem for p in IMAGES])
def test_real_model_handles_document(image):
    from doc_intake import Document, build_agent
    from doc_intake.providers import ClaudeLLM

    result = build_agent(ClaudeLLM()).invoke(
        {"document": Document("image", "image/png", image.read_bytes())}
    )
    assert result["status"] == "done", f"{image.name}: {result.get('validation_errors')}"
    assert result["extracted"]["doc_type"], f"{image.name}: empty doc_type"
    assert result["summary"].strip(), f"{image.name}: empty summary"
