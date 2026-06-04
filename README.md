# DocIntakeAgent

A small **LangGraph** document-intake agent built to demonstrate **agent testing
discipline** — node-level unit tests, graph-level integration tests, controlled
non-determinism via a mocked model, schema-validated structured output, and
regression coverage.

The entire agent builds and tests **offline with zero API cost**: every test
swaps the real model for a scripted `FakeLLM`, which is exactly how you make
non-deterministic agents deterministic under test.

## What it does

Takes raw document text and runs it through a graph:

```
START → ingest → (empty?) → fail
                    else    → extract → (router)
router:  valid     → summarize → END
         retriable → extract            (loop back, re-extract)
         exhausted → fail → END
```

The `extract` node asks the model for structured JSON, validates it against a
Pydantic schema, and — if the result is malformed — the conditional edge loops
back to retry until it validates or the attempt budget runs out. That retry loop
is why this is a **graph**, not a straight chain.

## Run it

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
playwright install chromium     # one-time, for the E2E test

# --- see it run with zero setup (scripted model, no key) ---
python demo.py

# --- tests (no API key needed) ---
pytest --cov=src/doc_intake     # fast unit + graph suite (E2E + integration excluded)
pytest -m e2e                   # Playwright browser test against the real UI

# --- run it live with a real model ---
cp .env.example .env            # then paste your ANTHROPIC_API_KEY into .env
uvicorn web.app:app --reload    # open http://127.0.0.1:8000; upload samples/sample-invoice.txt
pytest -m integration           # opt-in: calls the real model (costs a few cents)
```

## How it maps to the role

| Requirement | Where it lives |
| --- | --- |
| LangGraph agent workflow | `src/doc_intake/graph.py` — nodes + conditional edges |
| Node unit testing (mocked state) | `tests/test_nodes.py` — each node tested in isolation |
| Graph integration testing (controlled inputs) | `tests/test_graph.py` — full end-to-end runs |
| LLM mocking / controlled non-determinism | `src/doc_intake/llm.py` — `FakeLLM` scripted stub |
| Regression authorship | `tests/test_regression.py` — each test names the bug it guards |
| Structured output / JSON schema validation | `src/doc_intake/schema.py` — Pydantic contract |
| Test coverage reporting | `pytest --cov` (currently 96%) |
| Async agent execution | `tests/test_graph.py::test_async_invoke` (pytest-asyncio) |
| Playwright E2E UI testing | `tests/e2e/` — real browser drives the FastAPI front door |
| Live model integration | `src/doc_intake/providers.py` — `ClaudeLLM`, same interface as the fake |
| Document ingestion (PDF + text) | `web/app.py` — upload parsing (text-based PDFs; OCR not included) |
| Real-model integration test (opt-in) | `tests/integration/` — proves the live model yields a schema-valid result |
| Model-call assertions (test-only) | `FakeLLM.calls` lets tests assert how the model was called — not production observability |
| Cloud Run packaging | `Dockerfile` + `DEPLOY.md` — deploy config, boots locally; not yet deployed live |

## Scope and honest limits

This is a focused proof-of-concept, not a production system. Deliberately out of
scope so far — calling it out rather than implying otherwise:

- **No tool-calling.** The agent extracts and validates; it doesn't call external
  tools, so this doesn't exercise tool-call testing (a large part of real agent testing).
- **No real-model *quality* evaluation.** There's an opt-in integration test that
  the real model returns a schema-valid result, but no eval set scoring extraction
  *accuracy* across many documents.
- **Text-based PDFs only.** PDF text is extracted with `pypdf`; scanned/image PDFs
  would need OCR, which isn't included.
- **No production observability.** No tracing, structured logging, metrics, or
  token/cost tracking. `FakeLLM.calls` is a test helper only.
- **Not deployed live.** The Dockerfile and Cloud Run steps are correct and boot
  locally, but nothing has been deployed to a billed GCP project.
- **No CI yet.** The suite runs locally; there's no automated pipeline.

## Design note

Nodes never import a concrete model client — they depend on a tiny `LLM`
interface. That dependency injection is the whole reason the agent is testable:
production code passes a real model, tests pass `FakeLLM`, and the graph itself
never knows the difference.

## Running it live

`src/doc_intake/providers.py` ships a `ClaudeLLM` adapter — the same
`.complete(prompt) -> str` interface as `FakeLLM`, so it drops straight into
`build_agent(...)` with nothing else changed. Set `ANTHROPIC_API_KEY` in `.env`
and the web UI switches to live mode automatically; without a key it falls back
to scripted demo mode. Any other client (a local Ollama model, etc.) works the
same way — implement one method.
