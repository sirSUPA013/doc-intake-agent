"""Web front door for the agent — upload a document (PDF or text) and watch the
agent extract structured fields and summarize it.

Runs in one of two modes, shown as a banner on the page:
  - LIVE: if ANTHROPIC_API_KEY is set, a real Claude model drives the agent.
  - DEMO: otherwise it falls back to a scripted model, so the page always works
    (e.g. if there's no network at an interview). The mode is never hidden.
"""

from __future__ import annotations

import html
import io
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse

from doc_intake import build_agent
from doc_intake.llm import LLM

load_dotenv()  # pick up a local .env if present


class DemoLLM:
    """Scripted fallback so the page works with no API key (labeled in the UI)."""

    def complete(self, prompt: str) -> str:
        if prompt.startswith("Summarize"):
            return "Demo summary: an invoice was extracted from the submitted text."
        return json.dumps({
            "doc_type": "invoice",
            "title": "Extracted Document (demo)",
            "date": "2026-05-01",
            "entities": ["ACME Corp", "Sam Yandow"],
            "total_amount": "$1,250.00",
        })


def current_mode() -> str:
    return "live" if os.environ.get("ANTHROPIC_API_KEY") else "demo"


def get_llm() -> tuple[LLM, str]:
    """Live Claude model if a key is present, else the scripted fallback."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from doc_intake.providers import ClaudeLLM

            return ClaudeLLM(), "live"
        except Exception:
            return DemoLLM(), "demo"
    return DemoLLM(), "demo"


def _extract_text(pasted: str, upload: UploadFile | None) -> tuple[str, str | None]:
    """Resolve input to plain text. Returns (text, error_message)."""
    if upload is not None and upload.filename:
        raw = upload.file.read()
        if upload.filename.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(raw))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as exc:  # noqa: BLE001 - surface any parse failure to the user
                return "", f"Could not read PDF: {exc}"
            if not text.strip():
                return "", ("No text found in the PDF — it may be a scanned/image "
                            "PDF. OCR isn't supported in this demo.")
            return text, None
        return raw.decode("utf-8", errors="replace"), None
    return pasted, None


app = FastAPI(title="DocIntakeAgent")

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>DocIntakeAgent</title></head>
<body style="font-family: system-ui; max-width: 720px; margin: 40px auto; line-height:1.5">
<h1>Document Intake Agent</h1>
{banner}
<form method="post" action="/extract" enctype="multipart/form-data">
  <p><label>Upload a document (PDF or .txt):<br>
    <input type="file" name="upload" accept=".pdf,.txt" data-testid="file"></label></p>
  <p style="color:#666">&mdash; or paste text &mdash;</p>
  <textarea name="doc_text" rows="8" style="width:100%" data-testid="input"
    placeholder="Paste document text...">{doc_text}</textarea><br>
  <button type="submit" data-testid="submit">Extract</button>
</form>
{result}
</body></html>"""


def _banner(mode: str) -> str:
    if mode == "live":
        return ('<p data-testid="mode" style="padding:8px 12px;background:#dcfce7;'
                'border-radius:6px">Live mode &mdash; powered by Claude (real model).</p>')
    return ('<p data-testid="mode" style="padding:8px 12px;background:#fef9c3;'
            'border-radius:6px">Demo mode &mdash; scripted responses (no API key found).</p>')


def _render(doc_text: str = "", result_html: str = "", mode: str = "demo") -> str:
    return PAGE.format(banner=_banner(mode), doc_text=html.escape(doc_text),
                       result=result_html)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _render(mode=current_mode())


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/extract", response_class=HTMLResponse)
def extract(doc_text: str = Form(""), upload: UploadFile | None = File(None)) -> str:
    text, error = _extract_text(doc_text, upload)
    _, mode = get_llm()

    if error:
        result_html = (
            '<div data-testid="result" style="margin-top:24px;padding:16px;'
            f'background:#fee2e2;border-radius:8px">{html.escape(error)}</div>'
        )
        return _render(doc_text=doc_text, result_html=result_html, mode=mode)

    llm, mode = get_llm()
    result = build_agent(llm).invoke({"raw_text": text})
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
    return _render(doc_text=text, result_html=result_html, mode=mode)
