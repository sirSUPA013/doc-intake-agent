"""The individual graph nodes and the routing logic between them.

Each node is a plain function: it takes the current state and returns a partial
state update that LangGraph merges in. Keeping them as small, independent
functions is exactly what makes them unit-testable in isolation — a test can
hand-build a state dict, call one node, and assert on the result without ever
running the full graph.
"""

from __future__ import annotations

import json
from typing import Callable, Optional, TypedDict

from pydantic import ValidationError

from doc_intake.llm import LLM, Document
from doc_intake.schema import ExtractedDoc


class AgentState(TypedDict, total=False):
    """Shared state that flows through the whole graph and accumulates."""

    raw_text: str
    document: Optional[Document]   # image/PDF input, if not pasted text
    extracted: Optional[dict]
    validation_errors: list[str]
    attempts: int
    summary: str
    status: str


def ingest_node(state: AgentState) -> AgentState:
    """Accept either an attached document or pasted text; flag empty input early."""
    if state.get("document") is not None:
        return {"status": "ingested", "attempts": 0, "validation_errors": []}
    text = (state.get("raw_text") or "").strip()
    if not text:
        return {"raw_text": "", "status": "empty",
                "validation_errors": ["document is empty"]}
    return {"raw_text": text, "status": "ingested", "attempts": 0,
            "validation_errors": []}


_FIELDS = (
    "Extract these fields as JSON:\n"
    "  doc_type      - string: invoice, letter, report, receipt, note, contact list, etc.\n"
    "  title         - string, or null if there's no clear title\n"
    "  date          - ISO-8601 (YYYY-MM-DD), or null if no date is present\n"
    "  entities      - array of strings: people or organizations named (may be empty)\n"
    "  total_amount  - number, or null if there's no monetary total\n"
    "  transcription - a faithful, verbatim transcription of ALL text in the document\n"
    "  key_details   - array of {label, value} objects capturing every concrete detail not\n"
    "                  covered above (phone numbers, addresses, line items, directions);\n"
    "                  pair each value with the name or label it belongs to. May be empty.\n\n"
    "Use null or an empty array for anything not present. Respond with ONLY a single valid "
    "JSON object using exactly those keys. No markdown, no code fences, no explanation."
)


def _extract_prompt(text: str) -> str:
    return f"You are a document-extraction service. {_FIELDS}\n\nDOCUMENT:\n{text}"


def _extract_prompt_doc() -> str:
    return (
        "You are a document-extraction service. Read the attached document "
        "(it may be a photo, scan, or PDF, possibly handwritten). " + _FIELDS
    )


def _parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Forgiving fallback: pull out the outermost { ... } if the model wrapped
        # the JSON in prose ("Here is the data: {...}. Hope that helps!").
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def make_extract_node(llm: LLM) -> Callable[[AgentState], AgentState]:
    """Build the extract node bound to a specific (injected) model."""

    def extract_node(state: AgentState) -> AgentState:
        attempts = state.get("attempts", 0) + 1
        doc = state.get("document")
        if doc is not None:
            raw = llm.complete(_extract_prompt_doc(), document=doc)
        else:
            raw = llm.complete(_extract_prompt(state["raw_text"]))
        try:
            doc = ExtractedDoc(**_parse_json(raw))
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            return {"extracted": None, "attempts": attempts,
                    "validation_errors": [str(exc)]}
        return {"extracted": doc.model_dump(), "attempts": attempts,
                "validation_errors": []}

    return extract_node


def _summary_prompt(doc: dict) -> str:
    return "Summarize this document in one sentence:\n" + json.dumps(doc)


def make_summarize_node(llm: LLM) -> Callable[[AgentState], AgentState]:
    """Build the summarize node bound to a specific (injected) model."""

    def summarize_node(state: AgentState) -> AgentState:
        summary = llm.complete(_summary_prompt(state["extracted"]))
        return {"summary": summary.strip(), "status": "done"}

    return summarize_node


def fail_node(state: AgentState) -> AgentState:
    """Terminal node when extraction never validates within the retry budget."""
    return {"status": "failed"}


def route_after_ingest(state: AgentState) -> str:
    """Conditional edge: skip straight to fail on empty input."""
    return "fail" if state.get("status") == "empty" else "extract"


def make_router(max_attempts: int) -> Callable[[AgentState], str]:
    """Build the post-extract conditional edge.

    success -> summarize, retriable failure -> extract (loop), exhausted -> fail.
    """

    def route_after_extract(state: AgentState) -> str:
        if state.get("extracted") and not state.get("validation_errors"):
            return "summarize"
        if state.get("attempts", 0) < max_attempts:
            return "extract"
        return "fail"

    return route_after_extract
