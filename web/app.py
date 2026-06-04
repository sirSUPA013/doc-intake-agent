"""Web front door for the agent — upload a document (PDF or text) and watch the
agent extract structured fields and summarize it.

Modes (shown as a banner):
  - DEMO: scripted model, free, always available. The public default.
  - LIVE: real Claude, unlocked by entering the PIN. A daily cap is the cost
    backstop; the PIN can override the cap when needed. See web/gating.py.

If no ANTHROPIC_API_KEY is configured, the app stays in demo mode regardless, so
it can never faceplant (e.g. no network at an interview).
"""

from __future__ import annotations

import html
import io
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from doc_intake import build_agent
from doc_intake.llm import LLM
from web import gating

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


def effective_mode(unlocked: bool, override: bool) -> str:
    """Mode actually used, accounting for both the gate and key availability."""
    mode = gating.decide_mode(unlocked, override)
    if mode == "live" and not os.environ.get("ANTHROPIC_API_KEY"):
        return "demo"
    return mode


def pick_llm(mode: str) -> LLM:
    if mode == "live" and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from doc_intake.providers import ClaudeLLM

            return ClaudeLLM()
        except Exception:
            return DemoLLM()
    return DemoLLM()


def _extract_text(pasted: str, upload: UploadFile | None) -> tuple[str, str | None]:
    """Resolve input to plain text. Returns (text, error_message)."""
    if upload is not None and upload.filename:
        raw = upload.file.read()
        if upload.filename.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(raw))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as exc:  # noqa: BLE001 - surface any parse failure
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
<hr style="margin-top:32px;border:none;border-top:1px solid #e5e5e5">
<form method="post" action="/unlock" style="color:#666;font-size:0.9em">
  <strong>Live mode</strong> (real Claude) &mdash; enter PIN:
  <input type="password" name="pin" data-testid="pin" style="width:120px">
  <label><input type="checkbox" name="override" value="1" data-testid="override"> override daily cap</label>
  <button type="submit" data-testid="unlock">Unlock</button>
  {unlock_msg}
</form>
</body></html>"""


def _banner(mode: str) -> str:
    if mode == "live":
        used, cap = gating.live_used_today(), gating.DAILY_LIVE_CAP
        return ('<p data-testid="mode" style="padding:8px 12px;background:#dcfce7;'
                f'border-radius:6px">Live mode &mdash; powered by Claude. '
                f'({used}/{cap} live extractions used today)</p>')
    return ('<p data-testid="mode" style="padding:8px 12px;background:#fef9c3;'
            'border-radius:6px">Demo mode &mdash; scripted responses. Unlock live '
            'mode with the PIN below.</p>')


def _render(doc_text: str = "", result_html: str = "", mode: str = "demo",
            unlock_msg: str = "") -> str:
    return PAGE.format(banner=_banner(mode), doc_text=html.escape(doc_text),
                       result=result_html, unlock_msg=unlock_msg)


def _gate(request: Request) -> tuple[bool, bool]:
    return gating.read_cookie(request.cookies.get(gating.COOKIE_NAME))


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> str:
    unlocked, override = _gate(request)
    return _render(mode=effective_mode(unlocked, override))


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/unlock")
def unlock(request: Request, pin: str = Form(""), override: str = Form("")):
    if not gating.pin_ok(pin):
        msg = '<span style="color:#b91c1c"> &mdash; incorrect PIN</span>'
        return HTMLResponse(_render(mode="demo", unlock_msg=msg))
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        gating.COOKIE_NAME, gating.make_cookie(override=bool(override)),
        httponly=True, samesite="lax", max_age=8 * 3600,
    )
    return resp


@app.post("/extract", response_class=HTMLResponse)
def extract(request: Request, doc_text: str = Form(""),
            upload: UploadFile | None = File(None)) -> str:
    unlocked, override = _gate(request)
    mode = effective_mode(unlocked, override)

    text, error = _extract_text(doc_text, upload)
    if not error and len(text.encode("utf-8")) > gating.MAX_INPUT_BYTES:
        error = f"Input too large (limit {gating.MAX_INPUT_BYTES // 1000} KB)."

    if error:
        result_html = (
            '<div data-testid="result" style="margin-top:24px;padding:16px;'
            f'background:#fee2e2;border-radius:8px">{html.escape(error)}</div>'
        )
        return _render(doc_text=doc_text, result_html=result_html, mode=mode)

    llm = pick_llm(mode)
    if mode == "live":
        gating.record_live_call()
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
