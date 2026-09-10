#!/usr/bin/env bash
# Build both images into Artifact Registry, tagged with the commit.
#
# This is a BUILD, not a deploy: it spends Cloud Build minutes and Artifact
# Registry storage but creates no Cloud Run revision, so it does not consume one
# of the hackathon's deploys. Run it as many times as it takes to get a green
# build, then do the single `gcloud run services replace` once.
#
#   bash deploy/build-images.sh
#   bash deploy/render-service.sh > /tmp/neev.yaml
#   gcloud run services replace /tmp/neev.yaml --region asia-south1
#
# The two build contexts differ, and both are load-bearing:
#   backend  = repo root, because the image needs src/backend/, src/agents/ and
#              fixtures/ (the seed reads fixtures/draw_schedule.csv by a
#              repo-root path). .gcloudignore governs what is uploaded.
#   frontend = src/frontend, which needs no repo-root file.
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT="${GOOGLE_CLOUD_PROJECT:-buildguard-ai-2026}"
REGION="${REGION:-asia-south1}"
REPO="${AR_REPO:-neev}"
TAG="${TAG:-$(git rev-parse --short HEAD)}"
BASE="$REGION-docker.pkg.dev/$PROJECT/$REPO"

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree is dirty. The tag is a commit sha, so an image built from"
  echo "uncommitted code would be labelled as something it is not. Commit first."
  exit 1
fi

if ! gcloud artifacts repositories describe "$REPO" \
      --project "$PROJECT" --location "$REGION" >/dev/null 2>&1; then
  echo "Artifact Registry repo '$REPO' does not exist in $REGION. Create it:"
  echo
  echo "  gcloud artifacts repositories create $REPO \\"
  echo "    --repository-format=docker --location=$REGION --project=$PROJECT"
  exit 1
fi

echo "==> backend  -> $BASE/neev-api:$TAG"
gcloud builds submit . \
  --project "$PROJECT" \
  --tag "$BASE/neev-api:$TAG"

echo "==> frontend -> $BASE/neev-web:$TAG"
gcloud builds submit src/frontend \
  --project "$PROJECT" \
  --tag "$BASE/neev-web:$TAG"

echo
echo "Both images pushed at tag $TAG. Next:"
echo "  bash deploy/render-service.sh > /tmp/neev.yaml"
echo "  gcloud run services replace /tmp/neev.yaml --region $REGION"
