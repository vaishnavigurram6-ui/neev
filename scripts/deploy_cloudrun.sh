#!/usr/bin/env bash
# Deploy Neev to Cloud Run: backend first, then the frontend pointed at it.
#
# Run this yourself. It calls `gcloud run deploy`, which CLAUDE.md keeps out of
# agent hands even with the dry run lifted, because two free deploys existed for
# this hackathon and THIS SCRIPT SPENDS BOTH IN ONE INVOCATION.
#
# It deploys LIVE by default (NEEV_MODE=live): uploads are read by the
# five-agent ADK pipeline, which bills about Rs 3.81 per analysis. Set
# NEEV_MODE=fixture in the environment to deploy the recorded-run replay
# instead, which bills nothing.
#
# Everything that can be checked is checked BEFORE the first deploy call, since
# a deploy that succeeds and serves a broken app has still spent one.
#
#   bash scripts/deploy_cloudrun.sh
#
# Prerequisites, once per project:
#   gcloud auth login
#   gcloud config set project buildguard-ai-2026
#   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
#       artifactregistry.googleapis.com
set -euo pipefail

if [ "${NEEV_DEPLOY_SANDBOX:-0}" != "1" ]; then
  echo "Refusing deployment: this build has demo login and ephemeral data only."
  echo "After owner approval, explicitly set NEEV_DEPLOY_SANDBOX=1 for synthetic-data demos."
  exit 1
fi

PROJECT="${GOOGLE_CLOUD_PROJECT:-buildguard-ai-2026}"
REGION="${REGION:-asia-south1}"
BACKEND="${BACKEND_SERVICE:-neev-api}"
FRONTEND="${FRONTEND_SERVICE:-neev-web}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Signs the demo session cookie. Without it the backend picks a random key per
# process, and at --min-instances 0 Cloud Run recycles the instance after about
# fifteen idle minutes: a visitor who reads a page, steps away and comes back
# would be bounced to /login by a cookie signed with a key that no longer
# exists. Pass your own to keep sessions across a redeploy; generated here so
# forgetting cannot leave it empty.
SESSION_SECRET="${NEEV_SESSION_SECRET:-$(openssl rand -hex 32)}"

MODE="${NEEV_MODE:-live}"
SECRET_NAME="${NEEV_SECRET_NAME:-neev-gemini-api-key}"
RUNTIME_SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

# --- preflight ----------------------------------------------------------------
# Nothing below deploys. Every check that can fail is here, in front of the two
# calls that cannot be taken back.
echo "==> Preflight for NEEV_MODE=$MODE"

if [ "$MODE" = "live" ]; then
  # 1. The key. Read from .env rather than the environment so the operator does
  #    not have to export a credential into their shell history.
  KEY="${GOOGLE_API_KEY:-$(sed -n 's/^GOOGLE_API_KEY=//p' "$ROOT/.env" | head -1)}"
  if [ -z "$KEY" ]; then
    echo "  FAIL: no GOOGLE_API_KEY in the environment or $ROOT/.env."
    echo "        Live mode cannot call Gemini without it."
    exit 1
  fi
  echo "  ok  : GOOGLE_API_KEY found (${#KEY} chars)"

  # 2. The runtime service account's BigQuery access. The agents' benchmark
  #    lookups query buildguard_data, and on this project the default compute
  #    service account carries NO role binding at all — so without this the app
  #    deploys clean and then fails on the first analysis, having spent a deploy.
  ROLES="$(gcloud projects get-iam-policy "$PROJECT" \
    --flatten='bindings[].members' \
    --filter="bindings.members:$RUNTIME_SA" \
    --format='value(bindings.role)' 2>/dev/null || true)"
  if ! printf '%s' "$ROLES" | grep -qE 'bigquery|roles/editor|roles/owner'; then
    echo "  FAIL: $RUNTIME_SA cannot read BigQuery."
    echo "        The pipeline's rate lookups would fail on every analysis."
    echo "        Grant it, then re-run this script:"
    echo
    echo "          gcloud projects add-iam-policy-binding $PROJECT \\"
    echo "            --member=serviceAccount:$RUNTIME_SA \\"
    echo "            --role=roles/bigquery.jobUser"
    echo "          gcloud projects add-iam-policy-binding $PROJECT \\"
    echo "            --member=serviceAccount:$RUNTIME_SA \\"
    echo "            --role=roles/bigquery.dataViewer"
    exit 1
  fi
  echo "  ok  : $RUNTIME_SA can read BigQuery"

  # 3. The key in Secret Manager, never in --set-env-vars: an env var sits in
  #    the service's config and in the output of `gcloud run services describe`.
  if ! gcloud secrets describe "$SECRET_NAME" --project "$PROJECT" >/dev/null 2>&1; then
    echo "  ..  : creating secret $SECRET_NAME"
    gcloud secrets create "$SECRET_NAME" --project "$PROJECT" --replication-policy=automatic
  fi
  printf '%s' "$KEY" | gcloud secrets versions add "$SECRET_NAME" --project "$PROJECT" --data-file=- >/dev/null
  gcloud secrets add-iam-policy-binding "$SECRET_NAME" --project "$PROJECT" \
    --member="serviceAccount:$RUNTIME_SA" --role=roles/secretmanager.secretAccessor >/dev/null
  echo "  ok  : $SECRET_NAME holds the key, readable by the runtime account"
fi
echo

echo "Project : $PROJECT"
echo "Region  : $REGION"
echo

# --- backend -----------------------------------------------------------------
# Context is the repo root, because the image needs both src/backend/ and
# fixtures/ (the seed reads fixtures/draw_schedule.csv via a repo-root path).
# `gcloud run deploy --source` builds with the Dockerfile at the root of the
# context, which is why ./Dockerfile is the backend's and the frontend keeps its
# own under src/frontend/.
#
# max-instances=1 IS a correctness requirement: SQLite lives on the instance's
# own disk, so two instances would serve two different databases and a decision
# written on one would be invisible to the other.
#
# min-instances=0 is a cost one. Keeping an instance warm for a fortnight bills
# about 1.2M vCPU-seconds against a 180k free tier -- roughly Rs 2,530 to answer
# nobody at 3am. The price is a 3-6 second cold start (the entrypoint reseeds on
# boot); hit the URL once before presenting and no viewer sees it. Decisions
# recorded during a session are lost when the instance recycles after 15 idle
# minutes, which for a demo is arguably right: every visitor gets clean state.
echo "==> Building and deploying $BACKEND"
# min-instances=1, and the arithmetic behind it. The comment this replaces
# priced a warm instance at the ACTIVE CPU rate and concluded Rs 2,530 a
# fortnight. Cloud Run bills a min-instance at the "Min Instance CPU" SKU
# instead, which in asia-south1 is Rs 0.000238862/vCPU-s against Rs 0.00229308
# active -- 9.6x less. Fourteen days of one warm 1-vCPU/2-GiB instance, free
# tier applied, is about Rs 740. Worth it: with ADK in the image a cold start
# pays the import plus a reseed, and 15-30 seconds of blank screen in front of a
# judge costs more than Rs 740.
#
# max-instances=1 is still a CORRECTNESS requirement, not a cost one: SQLite
# lives on the instance's own disk, so two instances would serve two different
# databases and a decision written on one would be invisible to the other.
#
# timeout 600: a measured live run is 107 seconds, and the SSE stream is held
# open for the whole of it.
BACKEND_ENV="NEEV_MODE=$MODE,NEEV_DEMO_AUTH=true,NEEV_SESSION_SECRET=$SESSION_SECRET,GOOGLE_CLOUD_PROJECT=$PROJECT"
[ "$MODE" = "live" ] && BACKEND_ENV="$BACKEND_ENV,NEEV_ALLOW_BILLED_CALLS=1"

gcloud run deploy "$BACKEND" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --memory 2Gi \
  --cpu 1 \
  --timeout 600 \
  --set-env-vars "$BACKEND_ENV" \
  $([ "$MODE" = "live" ] && echo "--set-secrets GOOGLE_API_KEY=$SECRET_NAME:latest")

API_URL="$(gcloud run services describe "$BACKEND" \
  --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
echo "Backend URL: $API_URL"

# Fail here rather than deploying a frontend pointed at a broken API.
echo "==> Checking $API_URL/api/health"
curl -fsS "$API_URL/api/health" && echo

# --- frontend ----------------------------------------------------------------
# NEEV_API_BASE is server-side only: lib/api.ts imports 'server-only' and the
# variable has no NEXT_PUBLIC_ prefix, so the browser never learns the backend's
# address and every call is a server-to-server hop inside Cloud Run. That is
# also why no CORS configuration is needed.
echo "==> Building and deploying $FRONTEND"
# min-instances 0 here, deliberately: a Next standalone server boots in a
# second or two, which nobody notices, and keeping it warm would double the
# fortnight's bill for no perceptible gain. The backend is the slow starter.
gcloud run deploy "$FRONTEND" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source src/frontend \
  --allow-unauthenticated \
  --min-instances 0 \
  --memory 1Gi \
  --timeout 600 \
  --set-env-vars "NEEV_API_BASE=$API_URL"

WEB_URL="$(gcloud run services describe "$FRONTEND" \
  --project "$PROJECT" --region "$REGION" --format='value(status.url)')"

echo
echo "──────────────────────────────────────────────────────────────"
echo "  Neev is live:  $WEB_URL"
echo "  API:           $API_URL"
echo "──────────────────────────────────────────────────────────────"
echo
echo "Mode: $MODE. In live mode every 'Start the check' runs the five-agent"
echo "pipeline against Gemini -- about Rs 3.81 and 107 seconds per analysis."
echo
echo "Sign in with any 10-digit number. 'Home owner' lands on loan 1001;"
echo "'Bank officer' opens the portfolio. Auth is a demo session, not a"
echo "credential -- see src/backend/app/api/deps.py."
