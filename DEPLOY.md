# Deploying to GCP Cloud Run

The app is containerized (`Dockerfile`) and ready for Cloud Run. Cloud Run can
build the image from source for you, so **a local Docker install is not
required** — Cloud Build does the build in the cloud.

## Prerequisites

1. **Google Cloud SDK (`gcloud`)** installed locally — https://cloud.google.com/sdk/docs/install
2. **A GCP project with billing enabled.** Cloud Run has a generous always-free
   tier, but Google still requires a billing account (a card on file) to be
   attached before any deploy. This is the one step with a cost gate.

## Deploy

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

gcloud run deploy doc-intake-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

`--source .` hands the repo to Cloud Build, which builds the `Dockerfile` and
deploys the resulting image. On success, `gcloud` prints the public URL.

## Cost note

- Cloud Run free tier: 2M requests/month, scales to zero when idle (no traffic →
  no charge).
- The container listens on `$PORT` (Cloud Run injects it; the `Dockerfile`
  defaults to 8080 for local runs).
- The demo runs in scripted "demo mode" — no model API calls, so there is no
  per-request LLM cost.
