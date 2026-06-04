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

## Live mode on Cloud Run

By default the deployed app has no `ANTHROPIC_API_KEY`, so it serves scripted
demo mode. To run it live, provide the key as a secret (don't bake it into the
image or pass it as a plain env var):

```bash
echo -n "$ANTHROPIC_API_KEY" | gcloud secrets create anthropic-key --data-file=-
gcloud run deploy doc-intake-agent --source . --region us-central1 \
  --allow-unauthenticated \
  --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest
```

## Cost note

- Cloud Run free tier: 2M requests/month, scales to zero when idle (no traffic →
  no charge).
- The container listens on `$PORT` (Cloud Run injects it; the `Dockerfile`
  defaults to 8080 for local runs).
- In demo mode there are no model calls and no LLM cost. In live mode each request
  makes Claude API calls (a few cents per document).
