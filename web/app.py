"""Web front door for the agent — upload a document (PDF or text) and watch the
agent extract structured fields and summarize it.

Styled to match the SJForge "Nexus" design system (dark theme, blue/gold accents,
Orbitron/Rajdhani/IBM Plex fonts) so it fits the sjforge.dev environment.

Modes (shown as a banner):
  - DEMO: scripted model, free, always available. The public default.
  - LIVE: real Claude, unlocked by entering the PIN. A daily cap is the cost
    backstop; the PIN can override the cap. See web/gating.py.

If no ANTHROPIC_API_KEY is configured, the app stays in demo mode regardless.
"""

from __future__ import annotations

import html
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from doc_intake import build_agent
from doc_intake.llm import LLM, Document
from web import gating

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB cap on uploads
_IMAGE_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}

load_dotenv()


class DemoLLM:
    """Scripted fallback so the page works with no API key (labeled in the UI)."""

    def complete(self, prompt: str, document=None) -> str:
        if prompt.startswith("Summarize"):
            return "Demo summary: an invoice was extracted from the submitted text."
        return json.dumps({
            "doc_type": "invoice",
            "title": "Extracted Document (demo)",
            "date": "2026-05-01",
            "entities": ["ACME Corp", "Sam Yandow"],
            "total_amount": "$1,250.00",
            "transcription": "ACME Corp\nInvoice  -  Date: 2026-05-01\nBill to: Sam Yandow\nTotal due: $1,250.00",
            "key_details": [
                {"label": "Bill to", "value": "Sam Yandow"},
                {"label": "Total due", "value": "$1,250.00"},
            ],
        })


def effective_mode(unlocked: bool, override: bool) -> str:
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


def _resolve_input(pasted: str, upload: UploadFile | None) -> tuple[dict | None, str | None]:
    """Turn the request into agent state ({raw_text} or {document}), or an error.

    Images and PDFs are passed straight to the model (Claude reads them — no OCR
    engine), so scanned and handwritten docs work too.
    """
    if upload is not None and upload.filename:
        raw = upload.file.read()
        if len(raw) > MAX_FILE_BYTES:
            return None, f"File too large (limit {MAX_FILE_BYTES // (1024 * 1024)} MB)."
        ext = upload.filename.lower().rsplit(".", 1)[-1] if "." in upload.filename else ""
        if ext == "pdf":
            return {"document": Document("pdf", "application/pdf", raw)}, None
        if ext in _IMAGE_TYPES:
            return {"document": Document("image", _IMAGE_TYPES[ext], raw)}, None
        if ext in ("heic", "heif"):
            return None, ("HEIC photos aren't supported directly — please upload a "
                          "JPG or PNG (your phone can share/export as JPEG).")
        return {"raw_text": raw.decode("utf-8", errors="replace")}, None
    if pasted and len(pasted.encode("utf-8")) > gating.MAX_INPUT_BYTES:
        return None, f"Pasted text too large (limit {gating.MAX_INPUT_BYTES // 1000} KB)."
    return {"raw_text": pasted}, None


app = FastAPI(title="DocIntakeAgent")

STYLE = """
:root{
  --void:#07080a;--midnight:#0f1118;--slate:#12141f;--charcoal:#1a1d2e;
  --blue:#3b82f6;--blue-light:#60a5fa;--blue-core:#1e40af;--blue-pale:#93c5fd;
  --gold:#f59e0b;--gold-light:#fbbf24;--success:#10b981;--error:#ef4444;
  --text:#e2e8f0;--text-2:#94a3b8;--text-muted:#64748b;
}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--text);font-family:'IBM Plex Sans',system-ui,sans-serif;
  background:linear-gradient(145deg,var(--void) 0%,#0a0a0f 50%,var(--midnight) 100%);
  background-attachment:fixed;line-height:1.6;}
.grid{position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:linear-gradient(rgba(59,130,246,.03) 1px,transparent 1px),
  linear-gradient(90deg,rgba(59,130,246,.03) 1px,transparent 1px);background-size:40px 40px;}
.wrap{position:relative;z-index:1;max-width:760px;margin:0 auto;padding:48px 20px 40px;}
.brand{font-family:'Rajdhani',sans-serif;font-size:.78rem;letter-spacing:.28em;
  text-transform:uppercase;color:var(--blue-light);}
h1{font-family:'Orbitron',sans-serif;font-weight:700;font-size:1.85rem;margin:.15em 0 .15em;
  background:linear-gradient(90deg,var(--text),var(--blue-light));
  -webkit-background-clip:text;background-clip:text;color:transparent;}
.sub{color:var(--text-2);margin:0;}
.card{background:linear-gradient(135deg,var(--midnight) 0%,var(--slate) 100%);
  border:1px solid rgba(59,130,246,.2);border-radius:10px;padding:24px;margin-top:22px;
  box-shadow:inset 0 0 30px rgba(59,130,246,.05);}
label{display:block;color:var(--text-2);font-size:.9rem;margin-bottom:6px;}
input[type=file],textarea{width:100%;background:var(--void);color:var(--text);
  border:1px solid rgba(59,130,246,.25);border-radius:6px;padding:10px;font-family:inherit;}
textarea{font-family:'IBM Plex Mono',monospace;font-size:.85rem;resize:vertical;margin-top:4px;}
.divider{color:var(--text-muted);text-align:center;font-size:.85rem;margin:14px 0;}
button{font-family:'Rajdhani',sans-serif;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  background:linear-gradient(135deg,var(--blue-core),var(--blue));color:#fff;border:none;
  border-radius:6px;padding:10px 24px;cursor:pointer;font-size:.95rem;margin-top:14px;}
button:hover{background:linear-gradient(135deg,var(--blue),var(--blue-light));}
.banner{padding:11px 15px;border-radius:8px;font-size:.92rem;margin-top:18px;border:1px solid;}
.banner.live{background:rgba(16,185,129,.08);border-color:rgba(16,185,129,.4);color:#6ee7b7;}
.banner.demo{background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.4);color:var(--gold-light);}
.badge{font-family:'Rajdhani',sans-serif;font-weight:600;text-transform:uppercase;
  padding:2px 10px;border-radius:4px;font-size:.85rem;}
.badge.done{background:rgba(16,185,129,.15);color:#6ee7b7;}
.badge.failed{background:rgba(239,68,68,.15);color:#fca5a5;}
pre{background:var(--void);border:1px solid rgba(59,130,246,.15);border-radius:6px;padding:14px;
  overflow:auto;font-family:'IBM Plex Mono',monospace;font-size:.85rem;color:var(--blue-pale);}
.summary{color:var(--text);}
.error{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.4);color:#fca5a5;
  border-radius:8px;padding:16px;}
.unlock{margin-top:28px;padding-top:18px;border-top:1px solid rgba(59,130,246,.15);
  color:var(--text-muted);font-size:.85rem;}
.unlock input[type=password]{width:120px;background:var(--void);color:var(--text);
  border:1px solid rgba(59,130,246,.25);border-radius:4px;padding:4px 8px;font-family:inherit;}
.unlock button{padding:5px 14px;font-size:.78rem;margin-top:0;}
footer{position:relative;z-index:1;text-align:center;color:var(--text-muted);font-size:.8rem;padding:18px;}
a{color:var(--blue-light);text-decoration:none;}
a:hover{color:var(--blue-pale);}
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Document Intake Agent — SJForge</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono&display=swap" rel="stylesheet">
<style>__STYLE__</style></head>
<body>
<div class="grid"></div>
<div class="wrap">
  <div class="brand">SJForge &middot; AI Agent Demo</div>
  <h1>Document Intake Agent</h1>
  <p class="sub">A LangGraph agent that extracts structured fields from a document, validates them against a schema, and summarizes it.</p>
  __BANNER__
  <div class="card">
    <form method="post" action="/extract" enctype="multipart/form-data">
      <label for="up">Upload a document — photo, scan, PDF, or .txt</label>
      <input id="up" type="file" name="upload" accept=".pdf,.txt,.jpg,.jpeg,.png,.webp" data-testid="file">
      <div class="divider">— or paste text —</div>
      <textarea name="doc_text" rows="8" data-testid="input"
        placeholder="Paste document text...">__DOC__</textarea>
      <button type="submit" data-testid="submit">Extract</button>
    </form>
  </div>
  __RESULT__
  <form class="unlock" method="post" action="/unlock">
    <strong style="color:var(--text-2)">Live mode</strong> (real Claude) — enter PIN:
    <input type="password" name="pin" data-testid="pin">
    <label style="display:inline;color:var(--text-muted)"><input type="checkbox" name="override" value="1" data-testid="override"> override daily cap</label>
    <button type="submit" data-testid="unlock">Unlock</button>
    __UNLOCK__
  </form>
</div>
<footer>Part of the <a href="https://portfolio.sjforge.dev">SJForge</a> ecosystem &middot;
<a href="https://github.com/sirSUPA013/doc-intake-agent">source on GitHub</a></footer>
</body></html>"""


def _banner(mode: str) -> str:
    if mode == "live":
        used, cap = gating.live_used_today(), gating.DAILY_LIVE_CAP
        return ('<div class="banner live" data-testid="mode">Live mode — powered by Claude '
                f'({used}/{cap} live extractions used today). '
                '<form method="post" action="/lock" style="display:inline;margin-left:8px">'
                '<button type="submit" data-testid="lock" style="background:transparent;'
                'border:1px solid rgba(110,231,183,.5);color:#6ee7b7;padding:2px 10px;border-radius:5px;'
                'font-size:.75rem;cursor:pointer;text-transform:uppercase;letter-spacing:.04em;'
                'font-family:Rajdhani,sans-serif">Turn off</button></form></div>')
    return ('<div class="banner demo" data-testid="mode">Demo mode — scripted responses. '
            'Unlock live mode with the PIN below.</div>')


def _render(doc_text: str = "", result_html: str = "", mode: str = "demo",
            unlock_msg: str = "") -> str:
    return (PAGE.replace("__STYLE__", STYLE)
                .replace("__BANNER__", _banner(mode))
                .replace("__DOC__", html.escape(doc_text))
                .replace("__RESULT__", result_html)
                .replace("__UNLOCK__", unlock_msg))


def _h3(text: str) -> str:
    return (f'<h3 style="margin:18px 0 6px;font-family:Rajdhani,sans-serif;color:var(--blue-light);'
            f'font-size:.9rem;letter-spacing:.08em;text-transform:uppercase">{text}</h3>')


def _result_panel(result: dict) -> str:
    ex = result.get("extracted") or {}
    status = result.get("status", "")
    badge = "done" if status == "done" else "failed"
    parts = [f'<p>Status: <span class="badge {badge}" data-testid="status">{html.escape(status)}</span></p>']

    if status != "done":
        errs = result.get("validation_errors") or []
        detail = str(errs[0]) if errs else "the model didn't return usable output"
        parts.append(
            '<div class="error" data-testid="failure-reason" style="margin-top:12px">'
            "Couldn't complete extraction — the document may be hard to read, or the model's "
            "output didn't match the expected format after several tries."
            '<div style="margin-top:8px;font-family:IBM Plex Mono,monospace;font-size:.8rem;'
            f'color:var(--text-muted);white-space:pre-wrap">{html.escape(detail)}</div></div>'
        )

    if result.get("summary"):
        parts.append(f'<p class="summary" data-testid="summary">{html.escape(result["summary"])}</p>')

    if ex.get("transcription"):
        parts.append(_h3("Transcription"))
        parts.append('<div data-testid="transcription" style="white-space:pre-wrap;background:var(--void);'
                     'border:1px solid rgba(59,130,246,.15);border-radius:6px;padding:14px;'
                     'font-family:IBM Plex Mono,monospace;font-size:.85rem;color:var(--text)">'
                     f'{html.escape(ex["transcription"])}</div>')

    rows = []
    for label, val in (("Type", ex.get("doc_type")), ("Title", ex.get("title")), ("Date", ex.get("date")),
                       ("Entities", ", ".join(ex.get("entities") or []) or None), ("Total", ex.get("total_amount"))):
        if val not in (None, ""):
            rows.append((label, val))
    rows += [(d.get("label", ""), d.get("value", "")) for d in (ex.get("key_details") or [])]
    if rows:
        parts.append(_h3("Details"))
        trs = "".join(
            f'<tr><td style="padding:4px 14px 4px 0;color:var(--text-2);vertical-align:top;'
            f'white-space:nowrap;font-family:Rajdhani,sans-serif">{html.escape(str(l))}</td>'
            f'<td style="padding:4px 0;color:var(--text)">{html.escape(str(v))}</td></tr>'
            for l, v in rows
        )
        parts.append(f'<table data-testid="details" style="border-collapse:collapse;font-size:.9rem;width:100%">{trs}</table>')

    parts.append('<details style="margin-top:16px"><summary style="cursor:pointer;color:var(--text-muted);'
                 'font-size:.85rem">Raw structured output (JSON)</summary>'
                 f'<pre data-testid="json">{html.escape(json.dumps(ex, indent=2))}</pre></details>')

    return '<div class="card result" data-testid="result">' + "".join(parts) + "</div>"


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
        return HTMLResponse(_render(
            mode="demo",
            unlock_msg='<span style="color:#fca5a5"> — incorrect PIN</span>',
        ))
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        gating.COOKIE_NAME, gating.make_cookie(override=bool(override)),
        httponly=True, samesite="lax", max_age=8 * 3600,
    )
    return resp


@app.post("/lock")
def lock():
    """Turn live mode off — clear the unlock cookie, back to demo mode."""
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(gating.COOKIE_NAME)
    return resp


@app.post("/extract", response_class=HTMLResponse)
def extract(request: Request, doc_text: str = Form(""),
            upload: UploadFile | None = File(None)) -> str:
    unlocked, override = _gate(request)
    mode = effective_mode(unlocked, override)

    state, error = _resolve_input(doc_text, upload)
    if error:
        result_html = f'<div class="result error" data-testid="result">{html.escape(error)}</div>'
        return _render(doc_text=doc_text, result_html=result_html, mode=mode)

    llm = pick_llm(mode)
    if mode == "live":
        gating.record_live_call()
    result = build_agent(llm).invoke(state)
    return _render(doc_text=state.get("raw_text", ""),
                   result_html=_result_panel(result), mode=mode)
