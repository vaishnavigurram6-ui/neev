# Neev — Day-1 Implementation Drop

## What's in this package (mirror of repo layout)

| Path | Status vs repo | What changed |
|---|---|---|
| buildguard/config.py | REPLACES (repo copy is empty) | All constants: tables, thresholds, MILESTONE_WEIGHTS, LTV bands, cumulative_weight(), ltv_default_prior() |
| buildguard/agent.py | REPLACES | Workflow(edges=...) → SequentialAgent (Workflow isn't the ADK API); boq_analyst_agent prepended; output_key on all five agents; model name from config |
| buildguard/tools/boq_analyst_tool.py | NEW | 5 grounding tools: benchmark lookup (BigQuery), rate deviation, steel/RCC ratio, missing scope, payment schedule |
| buildguard/tools/disbursal_risk_tool.py | REPLACES | Flat scalar params (no nested dicts → no KeyError); exposure ratio + cost-to-complete gap + live LTV; RELEASE/HOLD/ESCALATE |
| buildguard/tools/visual_inspector_tool.py | REPLACES | Bug fix: `prompt` was used before definition and a second call used undefined `model`; stages renamed to match MILESTONE_WEIGHTS keys |
| buildguard/tools/cost_estimation_tool.py | REPLACES | YOUR_PROJECT_ID placeholder → config; added completed_value_estimate from metro_city_prices (locality median w/ city fallback) |
| fixtures/sample_boq.pdf | NEW | 40-item Ravi BoQ, total ₹28.5L, 4 seeded flaws + GST silence |
| fixtures/rate_benchmarks.csv | NEW | 30 items, keyword-matched. Rates are INDICATIVE — verify against CPWD DSR 2023 (see 'verified' column) |
| fixtures/draw_schedule.csv | NEW | 39 rows, 10 loans; loan 1001 = golden Ravi case (18L disbursed at slab) |
| scripts/make_sample_boq.py | NEW | Regenerates the BoQ PDF (edit flaws here) |
| scripts/load_bigquery.sh | NEW | bq mk + 2 loads |

## Apply to your repo (Cloud Shell)
```bash
cd ~/PatchaMommaProject
unzip -o ~/neev_day1.zip           # or copy files in
bash scripts/load_bigquery.sh
adk web --allow_origins 'regex:https://.*\.cloudshell\.dev'   # from parent dir as usual
```

## Verified here (no GCP creds in this sandbox, so BigQuery paths untested)
- All 7 Python files: syntax-checked
- Risk math: golden case → exposure 1.03, gap −₹7.5L, HOLD ✓ · clean case → RELEASE ✓ · low-confidence → ESCALATE ✓
- sample_boq.pdf renders (2 pages)

## You still need to
1. Rotate the API key + GitHub token (shared in chat = compromised)
2. Verify the 30 benchmark rates against the actual CPWD DSR 2023 PDF and flip 'verified' to YES — they're plausible placeholders, and a judge asking "where's this ₹8,036 from?" deserves a real answer
3. Take 5–10 site photos → demo_assets/
4. Golden-run in adk web with fixtures/sample_boq.pdf and loan 1001

## Note on the golden numbers
With the seeded BoQ totalling ₹28.5L and benchmark re-pricing pushing expected cost
to ~₹35L, the demo numbers land near the storyboard (exposure ~1.0–1.4 depending on
your expected-cost figure). If you want exposure exactly 1.4, set expected_total_cost
≈ ₹25.7L or disbursed ≈ ₹24.5L — or just present the real computed values.
