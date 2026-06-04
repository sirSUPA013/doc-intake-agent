# Multimodal (Vision) Upgrade — v01

**Date:** 2026-06-04
**Status:** active (approved — building)
**Goal:** Let the agent accept a photo or PDF (incl. scanned/handwritten) and extract
the same structured fields + summary — powered by Claude vision, with the new path
held to the same testing bar as the rest of the agent.

## Decisions locked (Sam)

- **Vision-only** via Claude. No offline OCR (Tesseract et al.) — it's bad at
  handwriting and adds a heavy dependency for no real gain. The accurate
  handwriting transcription Sam remembers from SamIndex *was* AI vision.
- **Model: Sonnet** (`claude-sonnet-4-6`) for reliability on messy photos/scans.
- **Testing is first-class**, not a bolt-on — the vision path gets node, graph,
  and (opt-in) real-model integration tests. Testing stays the headline.
- Keep scope tight: vision input + its tests + guardrail retune. Not a doc-management product.

## Design

**Model interface goes multimodal (preserves the test seam):**
- `LLM.complete(prompt, document=None)` — `document` is an optional `Document(kind, media_type, data)`.
- `ClaudeLLM`: with a document, sends an image or PDF content block + the prompt; Sonnet reads it.
- `FakeLLM`: **ignores** `document` and returns scripted output → tests stay deterministic regardless of modality.

**Agent flow:** state carries an optional `document`. `ingest` accepts either a
document or pasted text (empty + no doc → fail). `extract` sends the document to
the model when present, else the text. Routing/retry/summarize unchanged.

**Web upload:** accept images (JPG/PNG/WebP) + PDFs (text *and* scanned) + .txt + pasted text.
PDFs and images go straight to Claude as document/image blocks (no pypdf needed for the real path).

**Guardrail retune:** replace the 20 KB *text* cap with a **file-size cap (~10 MB)**
for uploads (keep a text cap for pasted text). Keep PIN gate + 50/day cap.

**HEIC note:** iOS Safari web uploads generally deliver JPEG already, so JPG/PNG/WebP
covers "snap a photo." If a raw HEIC arrives, return a friendly "use JPG/PNG" message
rather than pulling in libheif/system deps. (Can add server-side HEIC conversion later if needed.)

## Phases (each tested before the next)

1. **Multimodal core:** `Document` type; `LLM`/`FakeLLM`/`ClaudeLLM` updated (Sonnet default);
   `ingest`/`extract`/state handle a document. Node + graph tests for the document path (mocked). Run suite.
2. **Web upload:** image/PDF upload + guard retune in `web/app.py`. Local smoke test with a real image.
3. **Integration test:** a sample document image fixture + an opt-in real-Sonnet test asserting a schema-valid extraction.
4. **Docs + deploy:** README (drop "no OCR", document image/PDF support, updated limits); redeploy to Cloud Run; verify live.
5. **Commit/push** (DocIntakeAgent repo) + update the portfolio card to say "multimodal" (in PR #6 branch).

## Cost / risk

- Vision (Sonnet) calls cost more than text (~a few cents/doc with an image) — bounded by the 50/day cap.
- Risk: an untested feature would *undercut* the testing story → mitigated by Phase 1 + 3 tests.
- Risk: narrative drifting to "document scanner" → keep README/pitch leading with testing.
