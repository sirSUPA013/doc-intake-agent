"""Run the agent end-to-end with a scripted model — no API key, no cost.

    python demo.py

Swap the FakeLLM for a real model client (Claude, a local Ollama model, etc.)
to run it live; nothing else in the graph changes, because the nodes only
depend on the small LLM interface.
"""

import json

from doc_intake import build_agent
from doc_intake.llm import FakeLLM

SAMPLE = """
ACME Corp
Invoice #42  -  Date: 2026-05-01
Bill to: Sam Yandow
Total due: $1,250.00
"""


def main() -> None:
    # What a real model would have returned for this document:
    extraction = json.dumps({
        "doc_type": "invoice",
        "title": "ACME Invoice #42",
        "date": "2026-05-01",
        "entities": ["ACME Corp", "Sam Yandow"],
        "total_amount": "$1,250.00",  # currency-formatted on purpose
    })
    summary = "ACME invoice #42 dated 2026-05-01, total $1,250.00 billed to Sam Yandow."

    agent = build_agent(FakeLLM([extraction, summary]))
    result = agent.invoke({"raw_text": SAMPLE})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
