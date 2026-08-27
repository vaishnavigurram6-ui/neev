# Neev

AI agent pipeline that protects self-construction home loans — for the owner
(catches BoQ padding, missing scope, front-loaded payment schedules) and the
lender (verifies build stage from site photos before releasing each tranche).

Built on Google ADK: a `SequentialAgent` of five specialists sharing state via
`output_key`, with every number grounded in a tool call (BigQuery benchmarks,
pure-arithmetic risk math) — never model memory.

## Pipeline

```
BoQ pdf + photos + loan context
  → boq_analyst      (flags: RATE_OUTLIER, MISSING_SCOPE, UNDERSPECIFIED, FRONT_LOADED, GST_SILENT)
  → cost_estimation  (expected cost, completed-value estimate, sanction gap)
  → visual_inspector (stage checklist + banded confidence, human-review fallback)
  → disbursal_risk   (exposure ratio → RELEASE / HOLD / ESCALATE, cost-to-complete gap)
  → explainer        (owner view + credit-officer view, numbers from upstream state only)
```

## Layout

- `buildguard/` — the agent package (`adk web` discovers `buildguard.agent.root_agent`)
- `buildguard/tools/` — grounding tools; all thresholds live in `buildguard/config.py`
- `fixtures/` — `sample_boq.pdf` (Ravi golden case: 40 items, 4 seeded flaws),
  `clean_boq.pdf` (negative test: benchmark-aligned, full scope, GST stated),
  `rate_benchmarks.csv` (30 CPWD-DSR-derived rates — see `verified` column),
  `draw_schedule.csv` (10 loans; 1001 = golden HOLD case, 1002 = clean case)
- `scripts/` — `load_bigquery.sh` (loads fixtures + portfolio view),
  `boq_data.py` + `make_sample_boq.py --all` (regenerate both BoQ PDFs),
  `golden_run.py` (programmatic §3 test loop, needs GCP)
- `tests/` — offline suite, no GCP creds needed: `python3 -m tests.test_offline`
- `docs/` — hackathon submission, demo plan, implementation plan, data inventory
- `figures/` — 6 pitch diagrams
- `HANDOFF.md` — day-1 drop notes and remaining to-dos

## Run (Cloud Shell)

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in GOOGLE_API_KEY
bash scripts/load_bigquery.sh
adk web --allow_origins 'regex:https://.*\.cloudshell\.dev'   # from the parent dir
```

Then run the three demo-proof cases in one command (after putting 2–3 site
photos + one blurry photo in `demo_assets/`):

```bash
python3 scripts/golden_run.py --all \
  --photos demo_assets/slab1.jpg demo_assets/slab2.jpg \
  --blurry demo_assets/blurry.jpg
# golden   sample_boq.pdf + loan 1001 -> HOLD, >=4 flags
# clean    clean_boq.pdf  + loan 1002 -> RELEASE
# escalate blurry photo              -> ESCALATE
```

Or interactively: upload `fixtures/sample_boq.pdf` for loan 1001 (₹18L
disbursed at slab) in `adk web` → 4 flags + GST_SILENT, exposure ~1.0–1.4, HOLD.

Beat 4 (lender portfolio): `load_bigquery.sh` also creates the
`portfolio_hotlist` view — a sanction-proxy screen, worst loans first
(loan 1001 surfaces at exposure 1.29):

```sql
SELECT * FROM `<project>.buildguard_data.portfolio_hotlist` LIMIT 10
```

## Tests (anywhere, offline)

```bash
python3 -m tests.test_offline
```

28 checks: risk math golden/clean/escalation cases, all BoQ check functions,
config invariants, pipeline wiring, portfolio-view/SQL-config lockstep, and
cross-validation of BOTH BoQ fixtures against the benchmark table (the Ravi
BoQ triggers exactly its seeded flaws; the clean BoQ triggers none).

## Live Google Docs (polished, share these)

- Idea Submission: https://docs.google.com/document/d/1JYcsxk8gSDNYBVRSKt3crod9Y1vm0gMUkrvz9cVM1YE/edit
- Demo Plan: https://docs.google.com/document/d/1UbmU8ff2jM7ZcD1E19HslLIPuDyOZtOXFG_dEy0f8YI/edit

(Set sharing to "anyone with link → Viewer" before submitting.)
