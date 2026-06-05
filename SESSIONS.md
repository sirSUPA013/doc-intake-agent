# Sessions — DocIntakeAgent

Dated log of work sessions touching this project. Appended by `/sjend` at session close — one entry per session.

A new Claude session resuming this project should read this file's most recent entries + the active plan in `plans/` + the MCP task `docintake--red-team-fixes`.

---

## 2026-06-04 16:30 — Built the agent end-to-end: multimodal, tested, deployed, red-teamed

**What happened:**
- Built from scratch: LangGraph document-intake agent (ingest→extract→route→summarize w/ retry loop) + full pytest suite (node/graph/regression, FakeLLM DI mocking), Playwright E2E, opt-in eval set; public repo `github.com/sirSUPA013/doc-intake-agent`.
- Added multimodal vision (Claude Sonnet — photos/scans/PDFs/handwriting), verbatim transcription + flexible `key_details`, image downscaling, hardened JSON parse, `max_tokens` 4096.
- FastAPI demo: PIN-gated live mode + daily cap + "Turn off" lock, failure-reason UI, loading spinner, Nexus theme. Deployed to GCP Cloud Run (revision 9) at `doc-agent.sjforge.dev`.
- 5 field-found bugs fixed + guarded (notes failing, dropped info, truncation, etc.). Ran a 4-agent red-team review.

**Decisions made:**
- Vision-only (no offline OCR — accurate handwriting requires AI vision); Sonnet for reliability; testing kept as the headline throughout.
- Plans: `plans/live-demo-deploy-v01.md` (done), `plans/multimodal-vision-v01.md` (done).

**Next steps:**
1. Work MCP task `docintake--red-team-fixes` — P1 first: GCP budget alert + Anthropic spend cap, then cap/gate hardening.
2. P2: CI, web-layer tests, real eval (expected values), observability.
