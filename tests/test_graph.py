"""Graph-level integration tests — full end-to-end runs with controlled inputs.

The whole compiled agent runs here, but the model is still a scripted FakeLLM,
so the runs are completely deterministic. This is the "full end-to-end graph
runs with controlled inputs" requirement.
"""

from doc_intake import build_agent
from doc_intake.llm import FakeLLM


def test_happy_path(valid_doc_json, summary_text):
    llm = FakeLLM([valid_doc_json, summary_text])
    agent = build_agent(llm)
    result = agent.invoke({"raw_text": "ACME invoice ..."})
    assert result["status"] == "done"
    assert result["extracted"]["title"] == "ACME Invoice #42"
    assert result["summary"] == summary_text
    assert result["attempts"] == 1
    assert len(llm.calls) == 2  # one extract call, one summarize call


def test_retry_then_success(valid_doc_json, summary_text):
    # First extraction is malformed, second is valid -> the graph loops once.
    llm = FakeLLM(["broken json", valid_doc_json, summary_text])
    agent = build_agent(llm, max_attempts=2)
    result = agent.invoke({"raw_text": "..."})
    assert result["status"] == "done"
    assert result["attempts"] == 2


def test_exhausts_retries_and_fails():
    llm = FakeLLM(["bad", "still bad"])
    agent = build_agent(llm, max_attempts=2)
    result = agent.invoke({"raw_text": "..."})
    assert result["status"] == "failed"
    assert result["attempts"] == 2


def test_empty_document_short_circuits():
    llm = FakeLLM([])  # model must never be called for empty input
    agent = build_agent(llm)
    result = agent.invoke({"raw_text": "   "})
    assert result["status"] == "failed"
    assert llm.calls == []


async def test_async_invoke(valid_doc_json, summary_text):
    # Exercises LangGraph's async execution path under pytest-asyncio.
    llm = FakeLLM([valid_doc_json, summary_text])
    agent = build_agent(llm)
    result = await agent.ainvoke({"raw_text": "..."})
    assert result["status"] == "done"
