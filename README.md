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
pip install -r requirements.txt

python demo.py                  # watch the agent run (no API key needed)
pytest --cov=src/doc_intake     # run the suite with a coverage report
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
| Call instrumentation (lightweight observability) | `FakeLLM.calls` records every model call |

## Design note

Nodes never import a concrete model client — they depend on a tiny `LLM`
interface. That dependency injection is the whole reason the agent is testable:
production code passes a real model, tests pass `FakeLLM`, and the graph itself
never knows the difference.

## Running it live

Swap `FakeLLM` for any real client with a `.complete(prompt) -> str` method —
a Claude API wrapper or a local Ollama model both work. Nothing in the graph or
the nodes changes.
