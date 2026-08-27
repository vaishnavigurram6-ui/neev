# Neev — Setup Guide

Zero to a working demo. Written for someone picking this project up fresh.

## What you're setting up

Neev reviews home-construction loans with a 5-agent Gemini pipeline (Google
ADK): it parses a contractor's Bill of Quantities, flags padded rates and
missing scope against CPWD benchmarks, verifies claimed construction stage
from site photos, and recommends RELEASE / HOLD / ESCALATE for each loan
tranche — with an owner-facing and a credit-officer-facing rationale.

```
BoQ pdf + photos + loan context
  → boq_analyst → cost_estimation → visual_inspector → disbursal_risk → explainer
```

Target runtime is **Google Cloud Shell** (everything preinstalled except the
Python packages). Local works too if you have `gcloud`/`bq` set up.

## 1. Prerequisites

| Need | Notes |
|---|---|
| GCP project with billing | BigQuery is the data layer; `asia-south1` |
| Gemini API key | https://aistudio.google.com/apikey — free tier is fine for the demo |
| Python 3.10+ | `google-adk` requires ≥3.10 (Cloud Shell has it) |
| `gcloud` + `bq` CLIs | Preinstalled in Cloud Shell; `gcloud auth login` done |

## 2. Get the code and install

If you received this as a zip:

```bash
unzip neev.zip -d neev && cd neev
pip install -r requirements.txt
```

(From git instead: `git clone <repo-url> neev && cd neev`.)

## 3. Configure

```bash
cp .env.example .env    # then edit .env
```

- `GOOGLE_API_KEY` — your Gemini key. Never commit it; `.env` is git-ignored.
- `GOOGLE_CLOUD_PROJECT` — your GCP project id.

All other knobs (dataset name, model, thresholds, milestone weights) live in
`agents/neev_pipeline/config.py` with comments explaining each one. Default project id
is `buildguard-ai-2026`; the env var overrides it.

## 4. Load the data layer

```bash
bash scripts/load_bigquery.sh
```

This creates dataset `buildguard_data` and loads/creates:

- `rate_benchmarks` (30 rows, from `fixtures/rate_benchmarks.csv`)
- `draw_schedule` (39 rows, 10 loans, from `fixtures/draw_schedule.csv`)
- `portfolio_hotlist` (view — the lender's worst-loans-first screen)

The script then **verifies** two tables it does NOT create — `loan_history`
and `metro_city_prices` — and fails loudly if they're missing. These came
from earlier project work. If you don't have them, create them with these
minimal schemas (the cost agent queries exactly these columns):

```
loan_history:       region STRING, estimated_cost FLOAT,
                    plot_area_sqft FLOAT, estimated_tenure_months FLOAT
metro_city_prices:  city STRING, location STRING, price FLOAT, area FLOAT
```

Rows should cover Hyderabad (the demo city) — a few dozen plausible rows are
enough for the demo math to produce sane medians.

## 5. Sanity-check offline (no GCP needed)

```bash
python3 -m tests.test_offline
```

28 tests must pass. They cover the risk math (golden/clean/escalate cases),
every BoQ check function, config invariants, pipeline wiring, and
cross-validation of both BoQ fixtures against the benchmark table.

## 6. Run it

From the repo's **`agents/`** directory (ADK discovers agent packages in the
directory it is run from):

```bash
cd agents
adk web --allow_origins 'regex:https://.*\.cloudshell\.dev'
```

Pick `neev_pipeline` in the ADK UI, then run the golden case: upload
`fixtures/sample_boq.pdf`, say the location is "Kompally, Hyderabad",
1800 sqft, sanctioned ₹28,00,000, ₹18,00,000 disbursed, claimed stage
"slab", and attach 2–3 slab-stage photos.

**Expected:** 4 flag types + GST_SILENT from the BoQ analyst; exposure
~1.0–1.4; recommendation **HOLD**; a negative cost-to-complete gap the
explainer names in rupees.

Or run all three demo-proof cases programmatically:

```bash
python3 scripts/golden_run.py --all \
  --photos demo_assets/slab1.jpg demo_assets/slab2.jpg \
  --blurry demo_assets/blurry.jpg
```

| Case | Fixture | Loan | Expected |
|---|---|---|---|
| golden | `sample_boq.pdf` (4 seeded flaws) | 1001 | HOLD, ≥4 flags |
| clean | `clean_boq.pdf` (benchmark-aligned) | 1002 | RELEASE |
| escalate | blurry photo | 1001 | ESCALATE |

You need to supply the photos (`demo_assets/` is git-ignored): 2–3 clear
photos of a slab-stage site, plus one deliberately blurry shot.

## 7. Repo map

| Path | What it is |
|---|---|
| `buildguard/agent.py` | The 5-agent SequentialAgent pipeline |
| `buildguard/config.py` | Every constant the math depends on, documented |
| `buildguard/tools/` | Grounding tools — BigQuery lookups + pure arithmetic |
| `fixtures/` | Demo BoQs (seeded + clean), benchmarks, draw schedule |
| `scripts/boq_data.py` | BoQ fixture data — edit seeded flaws here |
| `scripts/make_sample_boq.py` | `--all` regenerates both BoQ PDFs |
| `scripts/golden_run.py` | Programmatic 3-case demo verification |
| `tests/test_offline.py` | The 28-test offline suite |
| `docs/` | Hackathon submission, demo script, implementation plan |
| `HANDOFF.md` | Day-1 drop notes (historical) |

## 8. Design rules (don't break these)

1. **No number from model memory.** Every figure in a flag comes from a tool
   call or the document itself. Rates enter via `rate_benchmarks` only.
2. **No fake precision.** Photo inspection returns banded completion +
   confidence; low confidence always escalates to a human.
3. **Questions, not verdicts.** BoQ flags produce polite questions for the
   contractor, never accusations.
4. **The LTV bands are a lookup prior, never a trained model** — the Kaggle
   dataset has fatal leakage; `config.py` documents this.

## 9. Known gaps

- The 30 benchmark rates are plausible placeholders — verify against the
  actual CPWD DSR 2023 and flip the `verified` column to YES.
- BigQuery paths are untested end-to-end (built without GCP creds);
  `golden_run.py --all` is the acceptance test.
- The clean case (loan 1002) has exposure ≈0.97 against the sanction proxy;
  if `loan_history` yields a low expected cost it may tip over 1.0 — if the
  clean run says HOLD, tune loan 1002's `disbursed_cum` down slightly.

## Troubleshooting

- **`neev_pipeline` not listed in adk web** — run from `agents/`;
  `agents/neev_pipeline/__init__.py` must contain `from . import agent`.
- **`403` / `Could not determine credentials`** — `gcloud auth
  application-default login`, and check `GOOGLE_CLOUD_PROJECT`.
- **`Not found: Dataset ... buildguard_data`** — step 4 didn't run against
  the project you're pointing at.
- **`ModuleNotFoundError: google.adk`** — Python < 3.10 or the venv isn't
  active.
- **Loader exits with "MISSING" table error** — see step 4, create the two
  legacy tables.
