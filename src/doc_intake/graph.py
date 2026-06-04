"""Assembles the nodes into a compiled LangGraph agent.

This is the piece that makes it an *agent* and not a straight script: the edges
include conditional branches, so the graph can loop back to re-extract on a bad
result and only moves on once the output validates. A plain LangChain chain
(step 1 -> 2 -> 3) cannot express that retry loop; a graph can.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from doc_intake.llm import LLM
from doc_intake.nodes import (
    AgentState,
    fail_node,
    ingest_node,
    make_extract_node,
    make_router,
    make_summarize_node,
    route_after_ingest,
)


def build_agent(llm: LLM, max_attempts: int = 2):
    """Build and compile the document-intake graph.

    Flow:
        START -> ingest -> (empty?) -> fail
                              else   -> extract -> (router)
        router: valid     -> summarize -> END
                retriable -> extract            (loop)
                exhausted -> fail -> END
    """
    g = StateGraph(AgentState)
    g.add_node("ingest", ingest_node)
    g.add_node("extract", make_extract_node(llm))
    g.add_node("summarize", make_summarize_node(llm))
    g.add_node("fail", fail_node)

    g.add_edge(START, "ingest")
    g.add_conditional_edges(
        "ingest", route_after_ingest,
        {"extract": "extract", "fail": "fail"},
    )
    g.add_conditional_edges(
        "extract", make_router(max_attempts),
        {"summarize": "summarize", "extract": "extract", "fail": "fail"},
    )
    g.add_edge("summarize", END)
    g.add_edge("fail", END)
    return g.compile()
