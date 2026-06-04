"""Graph-level tests across a VARIETY of document shapes.

The handwritten-note bug (2026-06-04) happened because the schema assumed every
document has a title and date — true for invoices, false for notes. These tests
run the graph against representative shapes, *including sparse ones*, so a
field that's wrongly made required again fails here immediately — deterministically,
with no real model and no cost. (A note-shaped case here would have caught the bug.)
"""

import json

import pytest

from doc_intake import build_agent
from doc_intake.llm import FakeLLM

# What the model might plausibly return for each kind of document. The point is
# the spread of present/absent fields — notes/forms/cards legitimately lack a
# date, title, or amount.
SHAPES = {
    "invoice": {"doc_type": "invoice", "title": "INV-100", "date": "2026-01-01",
                "entities": ["ACME Corp"], "total_amount": 100.0},
    "receipt": {"doc_type": "receipt", "title": None, "date": "2026-01-02",
                "entities": ["Corner Store"], "total_amount": 12.50},
    "letter":  {"doc_type": "letter", "title": "A short letter", "date": "2026-01-03",
                "entities": ["Jane", "John"], "total_amount": None},
    "note":    {"doc_type": "note", "title": None, "date": None,
                "entities": ["Mom", "Dave"], "total_amount": None},
    "form":    {"doc_type": "form", "title": "Intake Form", "date": None,
                "entities": [], "total_amount": None},
    "card":    {"doc_type": "business card", "title": None, "date": None,
                "entities": ["Dana Lee", "Globex"], "total_amount": None},
}


@pytest.mark.parametrize("name,shape", list(SHAPES.items()))
def test_graph_accepts_document_shape(name, shape):
    llm = FakeLLM([json.dumps(shape), f"A {name}."])
    result = build_agent(llm).invoke({"raw_text": f"a {name}"})
    assert result["status"] == "done", f"{name} failed: {result.get('validation_errors')}"
    assert result["extracted"]["doc_type"] == shape["doc_type"]
