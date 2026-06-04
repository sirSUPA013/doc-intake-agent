"""Node-level unit tests — every node exercised in isolation with mocked state.

No graph runs here. Each test hand-builds a state dict, calls a single node with
a FakeLLM, and asserts on the partial update it returns. This is the "every node
tested in isolation before it ships" requirement.
"""

from doc_intake.llm import FakeLLM
from doc_intake.nodes import (
    ingest_node,
    make_extract_node,
    make_router,
    make_summarize_node,
)


def test_ingest_normalizes_whitespace():
    out = ingest_node({"raw_text": "  hello world  "})
    assert out["raw_text"] == "hello world"
    assert out["status"] == "ingested"
    assert out["attempts"] == 0


def test_ingest_flags_empty_input():
    out = ingest_node({"raw_text": "   "})
    assert out["status"] == "empty"
    assert out["validation_errors"]


def test_extract_success_with_mocked_llm(valid_doc_json):
    node = make_extract_node(FakeLLM([valid_doc_json]))
    out = node({"raw_text": "some invoice text", "attempts": 0})
    assert out["extracted"]["doc_type"] == "invoice"
    assert out["extracted"]["total_amount"] == 1250.0
    assert out["validation_errors"] == []
    assert out["attempts"] == 1


def test_extract_handles_bad_json():
    node = make_extract_node(FakeLLM(["this is not json"]))
    out = node({"raw_text": "x", "attempts": 0})
    assert out["extracted"] is None
    assert out["validation_errors"]
    assert out["attempts"] == 1


def test_extract_handles_schema_violation():
    # Missing the required 'title' field -> Pydantic rejects it.
    node = make_extract_node(FakeLLM(['{"doc_type": "memo", "date": "2026-01-01"}']))
    out = node({"raw_text": "x", "attempts": 0})
    assert out["extracted"] is None
    assert out["validation_errors"]


def test_router_branches():
    route = make_router(max_attempts=2)
    assert route({"extracted": {"x": 1}, "validation_errors": []}) == "summarize"
    assert route({"extracted": None, "validation_errors": ["e"], "attempts": 1}) == "extract"
    assert route({"extracted": None, "validation_errors": ["e"], "attempts": 2}) == "fail"


def test_summarize_node():
    node = make_summarize_node(FakeLLM(["A short summary."]))
    out = node({"extracted": {"doc_type": "invoice"}})
    assert out["summary"] == "A short summary."
    assert out["status"] == "done"
