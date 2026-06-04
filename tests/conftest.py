"""Shared pytest fixtures."""

import json

import pytest


@pytest.fixture
def valid_doc_json() -> str:
    """A well-formed extraction the model might return."""
    return json.dumps({
        "doc_type": "invoice",
        "title": "ACME Invoice #42",
        "date": "2026-05-01",
        "entities": ["ACME Corp", "Sam Yandow"],
        "total_amount": 1250.00,
    })


@pytest.fixture
def summary_text() -> str:
    return "An ACME invoice (#42) dated 2026-05-01 for $1,250.00."
