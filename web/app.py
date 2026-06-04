"""A minimal web front door for the agent — the surface Playwright tests and the
service we containerize for Cloud Run.

It runs in **demo mode**: the model is scripted (DemoLLM) so the public demo runs
with no API key and no cost. Swapping in a real model client changes nothing else.
"""

from __future__ import annotations

import html
import json

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from doc_intake import build_agent


class DemoLLM:
    """Scripted stand-in so the deployed demo runs free. Clearly labeled in the UI."""

    def complete(self, prompt: str) -> str:
        if prompt.startswith("Summarize"):
            return "Demo summary: an invoice was extracted from the submitted text."
        return json.dumps({
            "doc_type": "invoice",
            "title": "Extracted Document",
            "date": "2026-05-01",
            "entities": ["ACME Corp", "Sam Yandow"],
            "total_amount": "$1,250.00",
        })


app = FastAPI(title="DocIntakeAgent")

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>DocIntakeAgent</title></head>
<body style="font-family: system-ui; max-width: 680px; margin: 40px auto; line-height:1.5">
<h1>Document Intake Agent</h1>
<p style="color:#666">LangGraph agent demo &mdash; <strong>demo mode</strong>
(model responses are scripted so this runs free).</p>
<form method="post" action="/extract">
  <textarea name="doc_text" rows="8" style="width:100%" data-testid="input"
    placeholder="Paste document text...">{doc_text}</textarea><br>
  <button type="submit" data-testid="submit">Extract</button>
</form>
{result}
</body></html>"""


def _render(doc_text: str = "", result_html: str = "") -> str:
    return PAGE.format(doc_text=html.escape(doc_text), result=result_html)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _render()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/extract", response_class=HTMLResponse)
def extract(doc_text: str = Form("")) -> str:
    result = build_agent(DemoLLM()).invoke({"raw_text": doc_text})
    extracted = json.dumps(result.get("extracted"), indent=2)
    result_html = (
        '<div data-testid="result" style="margin-top:24px;padding:16px;'
        'background:#f4f4f5;border-radius:8px">'
        f'<p>Status: <strong data-testid="status">{html.escape(result.get("status", ""))}'
        '</strong></p>'
        f'<pre data-testid="json">{html.escape(extracted)}</pre>'
        f'<p data-testid="summary">{html.escape(result.get("summary", ""))}</p>'
        '</div>'
    )
    return _render(doc_text=doc_text, result_html=result_html)
