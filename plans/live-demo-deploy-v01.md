# Live Demo Deploy — v01

**Date:** 2026-06-04
**Status:** active (awaiting Sam's review)
**Goal:** Deploy DocIntakeAgent as a persistent, PIN-gated live demo on GCP Cloud
Run, reachable at a sjforge.dev subdomain and linked from the portfolio, with
cost guardrails so a leaked link can't run up an Anthropic bill.

---

## Decisions locked (by Sam)

- **Host:** GCP Cloud Run (reuses the existing `Dockerfile`).
- **Exposure:** public visitors get **demo mode** (scripted, free). **Live Claude**
  is unlocked by entering a **PIN**. A **guardrail** (daily live-call cap +
  input-size limit) is the backstop even for PIN users.
- **Key handling:** `ANTHROPIC_API_KEY` and the PIN live in **GCP Secret Manager**,
  never baked into the image or committed.

## Naming (locked)

**`doc-agent.sjforge.dev`**

---

## How the gating works (the money-protection design)

1. **Default = demo mode.** No PIN, no real model, $0. Banner says "Demo mode."
2. **Unlock = PIN.** A visitor enters the PIN → server sets a signed session cookie
   → their submissions run **live Claude**. Banner says "Live mode (unlocked)."
3. **Guardrail backstop (applies even with a valid PIN):**
   - A **global daily cap** on live extractions (**50/day**, locked). When hit,
     live mode falls back to demo mode with a clear message until the daily reset.
   - An **input-size cap** (e.g. 20 KB of text) to bound per-call cost.
   - A **GCP budget alert** on the project as a second, external safety net.
4. PIN is a *light gate for a demo*, not real auth — documented as such.

> **Single-instance note:** the daily counter is in-memory, so the Cloud Run
> service will be pinned to **`--max-instances=1`** to keep the count reliable.
> Fine for a demo; called out so it's a conscious choice, not a bug.

---

## Components / changes

| # | Change | Files |
|---|--------|-------|
| 1 | PIN unlock + session cookie + daily cap + size limit | `web/gating.py` (new), `web/app.py` |
| 2 | Tests for the gate (locked/unlocked/cap-exceeded) | `tests/test_gating.py` (new) |
| 3 | Secrets in GCP Secret Manager (`anthropic-key`, `demo-pin`) | deploy step |
| 4 | Cloud Run deploy with `--set-secrets`, `--max-instances=1` | `DEPLOY.md` update |
| 5 | DNS + Cloud Run domain mapping for the subdomain | DNS provider + GCP |
| 6 | Portfolio project card linking to demo + GitHub | SJForge `apps/portfolio` (separate Vercel deploy) |
| 7 | Docs | `README.md`, `DEPLOY.md` |

## Who does what

- **Sam (interactive — I can't automate these):**
  - Install Google Cloud SDK.
  - Create / sign in to a GCP account, **enable billing** (card on file), create a project.
  - Run `gcloud auth login` (interactive).
  - Set a GCP **budget alert** (e.g. $5/month) — I'll give exact steps.
  - Add the DNS record for the subdomain (I'll give the exact record).
- **Claude (me):**
  - Write the gating code + tests (Phase 1, fully local, reviewable before any deploy).
  - Write deploy scripts; create Secret Manager entries (once you're authed); run the deploy.
  - Configure the Cloud Run domain mapping; add the portfolio card; update docs.

## Cost

- Cloud Run: free tier, scales to zero when idle → ~$0 hosting.
- Anthropic: only PIN-unlocked, size-bounded, daily-capped calls — pennies each,
  hard-capped per day by the in-app counter, with a GCP budget alert behind it.

## Risks / assumptions

- In-memory counter resets on container restart and doesn't span instances →
  mitigated by `--max-instances=1`.
- PIN is a light gate, not authentication — acceptable and documented for a demo.
- Cloud Run custom-domain mapping requires domain ownership verification in GCP;
  may add a step. DNS propagation can take time.
- Portfolio change deploys via Vercel (the portfolio's own pipeline), separate
  from the Cloud Run deploy.

## Sequence (phased — each phase is shippable and reviewed before the next)

- **Phase 1 — Gating + guardrails + tests, locally.** No deploy. You review the code.
- **Phase 2 — You set up GCP** (account, billing, gcloud, project, budget alert), guided.
- **Phase 3 — Secrets + first Cloud Run deploy.** Public demo mode live; PIN unlocks live. Verify on the run.app URL.
- **Phase 4 — Subdomain mapping + DNS.** Verify `doc-agent.sjforge.dev`.
- **Phase 5 — Portfolio card/link.** Deploy portfolio.
- **Phase 6 — Docs + final end-to-end verification.**

## Open questions for Sam

1. ~~Subdomain~~ → **doc-agent.sjforge.dev** (locked)
2. ~~Daily cap~~ → **50/day** (locked)
3. The PIN value — you set it at Phase 3; I'll store it in Secret Manager, never in git/chat.
