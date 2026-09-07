#!/bin/bash
# Load the Neev fixture tables into BigQuery. Run from repo root in Cloud Shell.
# Assumes: gcloud auth done, GOOGLE_CLOUD_PROJECT set (or edit PROJECT below).
set -euo pipefail
PROJECT="${GOOGLE_CLOUD_PROJECT:-buildguard-ai-2026}"
DATASET="buildguard_data"

bq --project_id="$PROJECT" mk --force --dataset --location=asia-south1 "$DATASET" || true

# rate_benchmarks now carries alias rows -- several keywords per priced item, so
# that "damp proof course" and "dpc" resolve to the same rate. Rows sharing a
# description must agree on unit and effective_rate; tests/test_offline.py
# enforces that. RELOAD THIS TABLE after editing the CSV or the synonyms have no
# effect in BigQuery. A bq load is not a Cloud Run deploy and costs you nothing.
bq --project_id="$PROJECT" load --replace --source_format=CSV --skip_leading_rows=1 \
  "$DATASET.rate_benchmarks" fixtures/rate_benchmarks.csv \
  "keyword:STRING,description:STRING,unit:STRING,dsr_rate:FLOAT,hyd_factor:FLOAT,effective_rate:FLOAT,verified:STRING"

bq --project_id="$PROJECT" load --replace --source_format=CSV --skip_leading_rows=1 \
  "$DATASET.draw_schedule" fixtures/draw_schedule.csv \
  "loan_id:INTEGER,tranche_no:INTEGER,milestone:STRING,planned_cum_pct:FLOAT,sanctioned:INTEGER,disbursed_cum:INTEGER,inspection_date:DATE,observed_stage:STRING"

echo "Loaded rate_benchmarks (62 rows) and draw_schedule (39 rows) into $PROJECT:$DATASET"

# Beat 4: portfolio hotlist view (see scripts/portfolio_view.sql for caveats).
sed "s/__PROJECT__/$PROJECT/g" "$(dirname "$0")/portfolio_view.sql" \
  | bq --project_id="$PROJECT" query --use_legacy_sql=false
echo "Created view $DATASET.portfolio_hotlist"

# Guard: cost_estimation_tool.py queries these pre-existing tables. If they've
# been dropped, the pipeline's cost agent will crash mid-demo — fail loudly NOW.
MISSING=0
for t in loan_history metro_city_prices; do
  if ! bq --project_id="$PROJECT" show "$DATASET.$t" >/dev/null 2>&1; then
    echo "ERROR: $PROJECT:$DATASET.$t is MISSING." >&2
    echo "       cost_estimation_tool.py queries it; reload it before the demo." >&2
    MISSING=1
  fi
done
[ "$MISSING" -eq 0 ] && echo "Verified loan_history and metro_city_prices exist." \
  || exit 1
