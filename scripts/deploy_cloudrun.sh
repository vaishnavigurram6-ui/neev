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
# Live mode goes through VERTEX AI, not the Gemini API, and that is a cost
# decision rather than a technical one. The Gemini API's free tier allows 20
# generateContent requests per day per model -- about two analyses -- and
# raising it means putting a card on an AI Studio account. Vertex AI runs the
# same models, authenticates as the Cloud Run service account (so there is no
# key to leak or rotate), and bills against the project's Cloud Billing
# account, which is where hackathon credits live. Set
# NEEV_GENAI_BACKEND=apikey to use a Gemini API key from Secret Manager
# instead.
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
# exists.
#
# Three sources, in order: the environment, then .env, then a fresh one. .env is
# in the list because the previous version read only the environment, so
# "generate one and record it" -- which is what keeps sessions alive across a
# redeploy -- worked only if you also remembered to export it. Forgetting was
# silent: the deploy succeeded, and every session from the last one died. Same
# file and same pattern as GOOGLE_API_KEY below.
SESSION_SECRET="${NEEV_SESSION_SECRET:-}"
if [ -z "$SESSION_SECRET" ] && [ -f "$ROOT/.env" ]; then
  SESSION_SECRET="$(sed -n 's/^NEEV_SESSION_SECRET=//p' "$ROOT/.env" | head -1)"
fi
if [ -z "$SESSION_SECRET" ]; then
  SESSION_SECRET="$(openssl rand -hex 32)"
  echo "==> No NEEV_SESSION_SECRET in the environment or $ROOT/.env."
  echo "    Generated a fresh one. Sessions from an earlier deploy will be"
  echo "    signed out. To keep them, record one in .env before redeploying:"
  echo "      echo \"NEEV_SESSION_SECRET=\$(openssl rand -hex 32)\" >> .env"
else
  echo "==> Session secret: reusing the recorded one (sessions survive this deploy)."
fi

MODE="${NEEV_MODE:-live}"
GENAI_BACKEND="${NEEV_GENAI_BACKEND:-vertex}"
VERTEX_LOCATION="${NEEV_VERTEX_LOCATION:-global}"
SECRET_NAME="${NEEV_SECRET_NAME:-neev-gemini-api-key}"
RUNTIME_SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

# --- preflight ----------------------------------------------------------------
# Nothing below deploys. Every check that can fail is here, in front of the two
# calls that cannot be taken back.
echo "==> Preflight for NEEV_MODE=$MODE"

# 0. The APIs and the roles `gcloud run deploy --source` itself needs. Learned
#    the hard way on 2026-09-09: cloudbuild.googleapis.com was not enabled, and
#    the default compute service account -- which is also Cloud Build's build
#    account -- carried NO role binding at all, so the build could not read its
#    own uploaded source tarball. `--source` would have failed before it ever
#    reached a revision.
for API in cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com; do
  if ! gcloud services list --enabled --project "$PROJECT" 2>/dev/null | grep -q "^$API"; then
    echo "  FAIL: $API is not enabled. Enable it, then re-run:"
    echo "          gcloud services enable $API --project $PROJECT"
    exit 1
  fi
done
echo "  ok  : cloudbuild, run and artifactregistry are enabled"

BUILD_ROLES="$(gcloud projects get-iam-policy "$PROJECT" \
  --flatten='bindings[].members' \
  --filter="bindings.members:$RUNTIME_SA" \
  --format='value(bindings.role)' 2>/dev/null || true)"
if ! printf '%s' "$BUILD_ROLES" | grep -qE 'cloudbuild.builds.builder|roles/editor|roles/owner'; then
  echo "  FAIL: $RUNTIME_SA cannot build."
  echo "        Cloud Build runs as this account and cannot read the source it"
  echo "        just uploaded. Grant it, then re-run this script:"
  echo
  echo "          gcloud projects add-iam-policy-binding $PROJECT \\"
  echo "            --member=serviceAccount:$RUNTIME_SA \\"
  echo "            --role=roles/cloudbuild.builds.builder"
  exit 1
fi
echo "  ok  : $RUNTIME_SA can build and push"

if [ "$MODE" = "live" ] && [ "$GENAI_BACKEND" = "vertex" ]; then
  # 1. Vertex AI, and the one role it needs. No key at all: the service account
  #    is the credential.
  if ! gcloud services list --enabled --project "$PROJECT" 2>/dev/null | grep -q '^aiplatform'; then
    echo "  FAIL: aiplatform.googleapis.com is not enabled. Enable it, then re-run:"
    echo "          gcloud services enable aiplatform.googleapis.com --project $PROJECT"
    exit 1
  fi
  VERTEX_ROLES="$(gcloud projects get-iam-policy "$PROJECT" \
    --flatten='bindings[].members' \
    --filter="bindings.members:$RUNTIME_SA" \
    --format='value(bindings.role)' 2>/dev/null || true)"
  if ! printf '%s' "$VERTEX_ROLES" | grep -qE 'aiplatform.user|roles/editor|roles/owner'; then
    echo "  FAIL: $RUNTIME_SA cannot call Vertex AI. Grant it, then re-run:"
    echo
    echo "          gcloud projects add-iam-policy-binding $PROJECT \\"
    echo "            --member=serviceAccount:$RUNTIME_SA \\"
    echo "            --role=roles/aiplatform.user"
    exit 1
  fi
  echo "  ok  : Vertex AI reachable as $RUNTIME_SA (no API key needed)"

elif [ "$MODE" = "live" ]; then
  # 1b. The Gemini API key path, kept for anyone who wants it. Read from .env so
  #     the operator does not have to export a credential into their shell.
  KEY="${GOOGLE_API_KEY:-$(sed -n 's/^GOOGLE_API_KEY=//p' "$ROOT/.env" | head -1)}"
  if [ -z "$KEY" ]; then
    echo "  FAIL: no GOOGLE_API_KEY in the environment or $ROOT/.env."
    echo "        Live mode cannot call the Gemini API without it."
    exit 1
  fi
  echo "  ok  : GOOGLE_API_KEY found (${#KEY} chars)"
  echo "  NOTE: the Gemini API free tier allows 20 requests per day per model,"
  echo "        which is about two analyses. Vertex AI has no such cap."

  # 3. The key in Secret Manager, never in --set-env-vars: an env var sits in
  #    the service's config and in the output of `gcloud run services describe`.
  #    Only reached on the api-key path; Vertex needs no secret.
  if ! gcloud secrets describe "$SECRET_NAME" --project "$PROJECT" >/dev/null 2>&1; then
    echo "  ..  : creating secret $SECRET_NAME"
    gcloud secrets create "$SECRET_NAME" --project "$PROJECT" --replication-policy=automatic
  fi
  printf '%s' "$KEY" | gcloud secrets versions add "$SECRET_NAME" --project "$PROJECT" --data-file=- >/dev/null
  gcloud secrets add-iam-policy-binding "$SECRET_NAME" --project "$PROJECT" \
    --member="serviceAccount:$RUNTIME_SA" --role=roles/secretmanager.secretAccessor >/dev/null
  echo "  ok  : $SECRET_NAME holds the key, readable by the runtime account"
fi

# The runtime account's BigQuery access, whichever credential route live mode
# takes. It sat inside the api-key branch, so a Vertex deploy -- the default --
# skipped the check entirely: the app would have deployed clean and then failed
# on the first analysis, having spent a deploy. The agents' benchmark lookups
# query buildguard_data, and on this project the default compute service account
# started with no role binding at all.
if [ "$MODE" = "live" ]; then
  BQ_ROLES="$(gcloud projects get-iam-policy "$PROJECT" \
    --flatten='bindings[].members' \
    --filter="bindings.members:$RUNTIME_SA" \
    --format='value(bindings.role)' 2>/dev/null || true)"
  if ! printf '%s' "$BQ_ROLES" | grep -qE 'bigquery|roles/editor|roles/owner'; then
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
# The daily analysis cap travels with the deployment, because the thing it
# guards against is the deployment: a public URL whose sign-in accepts any
# ten-digit number, in a mode where every upload spends about Rs 3.81.
BACKEND_ENV="NEEV_MODE=$MODE,NEEV_DEMO_AUTH=true,NEEV_SESSION_SECRET=$SESSION_SECRET,GOOGLE_CLOUD_PROJECT=$PROJECT"
BACKEND_ENV="$BACKEND_ENV,NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY=${NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY:-12}"
BACKEND_ENV="$BACKEND_ENV,NEEV_MAX_ANALYSES_PER_DAY=${NEEV_MAX_ANALYSES_PER_DAY:-60}"
# The runbook tells the operator they can override the demo password here, and
# for a while that was a lie: this variable was never sent, so the deployment
# used the default whatever they exported.
BACKEND_ENV="$BACKEND_ENV,NEEV_DEMO_PASSWORD=${NEEV_DEMO_PASSWORD:-password}"
# Pin the model the pipeline was actually proven end to end on, rather than
# inheriting a default that can move under it.
BACKEND_ENV="$BACKEND_ENV,NEEV_GEMINI_MODEL=${NEEV_GEMINI_MODEL:-gemini-3.7-flash}"
if [ "$MODE" = "live" ]; then
  BACKEND_ENV="$BACKEND_ENV,NEEV_ALLOW_BILLED_CALLS=1"
  if [ "$GENAI_BACKEND" = "vertex" ]; then
    # google-genai reads these three; ADK inherits the client it builds, so the
    # whole pipeline moves to Vertex with no code change.
    BACKEND_ENV="$BACKEND_ENV,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_LOCATION=$VERTEX_LOCATION"
  fi
fi

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
  $([ "$MODE" = "live" ] && [ "$GENAI_BACKEND" = "apikey" ] && echo "--set-secrets GOOGLE_API_KEY=$SECRET_NAME:latest")

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
echo "Mode: $MODE via $GENAI_BACKEND. In live mode every 'Start the check' runs the five-agent"
echo "pipeline against Gemini -- about Rs 3.81 and 107 seconds per analysis,"
echo "capped at ${NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY:-12} per loan and ${NEEV_MAX_ANALYSES_PER_DAY:-60} per day across the service."
echo
echo "Sign in as ravi (loan 1001), prasad (loan 1002) or officer (the whole"
echo "book). Password: ${NEEV_DEMO_PASSWORD:-password}. These are named demo"
echo "accounts, not identity -- see src/backend/app/api/accounts.py."
