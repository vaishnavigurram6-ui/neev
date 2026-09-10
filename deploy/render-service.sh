#!/usr/bin/env bash
# Render deploy/service.yaml with this project's values and print it.
#
# Prints, never applies. Applying is `gcloud run services replace`, which is a
# deploy, and CLAUDE.md keeps deploys in the owner's hands. Review the output,
# then pipe it yourself:
#
#   bash deploy/render-service.sh > /tmp/neev.yaml   # read it
#   gcloud run services replace /tmp/neev.yaml --region asia-south1
#
# Images must exist in Artifact Registry first -- see deploy/build-images.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT="${GOOGLE_CLOUD_PROJECT:-buildguard-ai-2026}"
REGION="${REGION:-asia-south1}"
REPO="${AR_REPO:-neev}"
TAG="${TAG:-$(git rev-parse --short HEAD)}"
MODE="${NEEV_MODE:-live}"
GEMINI_MODEL="${NEEV_GEMINI_MODEL:-gemini-3.7-flash}"
DEMO_PASSWORD="${NEEV_DEMO_PASSWORD:-password}"
MAX_PER_LOAN="${NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY:-12}"
MAX_PER_DAY="${NEEV_MAX_ANALYSES_PER_DAY:-60}"

# Same three sources as deploy_cloudrun.sh, and the same reason: a secret that
# changes on every deploy signs everyone out of the running demo.
SESSION_SECRET="${NEEV_SESSION_SECRET:-}"
if [ -z "$SESSION_SECRET" ] && [ -f .env ]; then
  SESSION_SECRET="$(sed -n 's/^NEEV_SESSION_SECRET=//p' .env | head -1)"
fi
if [ -z "$SESSION_SECRET" ]; then
  echo "No NEEV_SESSION_SECRET in the environment or .env." >&2
  echo "  echo \"NEEV_SESSION_SECRET=\$(openssl rand -hex 32)\" >> .env" >&2
  exit 1
fi

BASE="$REGION-docker.pkg.dev/$PROJECT/$REPO"
export REGION PROJECT MODE GEMINI_MODEL DEMO_PASSWORD MAX_PER_LOAN MAX_PER_DAY SESSION_SECRET
export WEB_IMAGE="$BASE/neev-web:$TAG"
export API_IMAGE="$BASE/neev-api:$TAG"

# Live mode needs the billing flag and, on Vertex, two more variables. Indented
# to sit inside the sidecar's env list; empty in fixture mode, where the
# absence of NEEV_ALLOW_BILLED_CALLS is itself the guard.
if [ "$MODE" = "live" ]; then
  export LIVE_ENV="            - name: NEEV_ALLOW_BILLED_CALLS
              value: \"1\"
            - name: GOOGLE_GENAI_USE_VERTEXAI
              value: \"true\"
            - name: GOOGLE_CLOUD_LOCATION
              value: \"${GOOGLE_CLOUD_LOCATION:-global}\""
else
  export LIVE_ENV=""
fi

# envsubst would also eat anything else that looks like a variable; naming the
# set keeps $PORT and friends in the YAML literal.
envsubst '$REGION $PROJECT $MODE $GEMINI_MODEL $DEMO_PASSWORD $MAX_PER_LOAN $MAX_PER_DAY $SESSION_SECRET $WEB_IMAGE $API_IMAGE $LIVE_ENV' \
  < deploy/service.yaml
