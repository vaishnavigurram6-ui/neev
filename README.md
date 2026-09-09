# Neev (नींव)

AI agent pipeline that protects self-construction home loans — for the home
builder (catches BoQ padding, missing scope, front-loaded payment schedules) and
for the lender (verifies build stage from site photographs before releasing each
disbursement).

Built on Google ADK: a `SequentialAgent` of five specialists sharing state via
`output_key`, with every number grounded in a tool call (BigQuery benchmarks,
pure-arithmetic risk math) — never model memory.

*नींव is the foundation of a building. It is also the first stage of
construction the system verifies.*

## Pipeline

```
BoQ pdf + photos + loan context
  → boq_analyst      (flags: RATE_OUTLIER, MISSING_SCOPE, UNDERSPECIFIED, FRONT_LOADED, GST_SILENT)
  → cost_estimation  (expected cost, completed-value estimate, sanction gap)
  → visual_inspector (stage checklist + banded confidence, human-review fallback)
  → disbursal_risk   (exposure ratio → RELEASE / HOLD / ESCALATE, cost-to-complete gap)
  → explainer        (owner view + credit-officer view, numbers from upstream state only)
```

## The application

Three packages, one direction of dependency:

```
src/frontend  →  src/backend  →  SQLite, seeded from captured pipeline runs
src/agents    →  the ADK pipeline, driven by the backend or by `adk web`
```

- **`src/agents/neev_pipeline/`** — the pipeline above. `adk web` from
  `src/agents/` discovers `neev_pipeline.agent.root_agent`.
- **`src/backend/`** — FastAPI + SQLAlchemy + SQLite. 22 API paths, 239 tests.
- **`src/frontend/`** — Next.js App Router + Tailwind v4. 16 routes, role
  enforcement in `proxy.ts`.

### Run it

```bash
bash scripts/dev.sh          # both servers, seeded, fixture mode
```

Prints the demo URLs. Sign in with a username and password — the demo accounts
are listed in **`docs/Neev_Demo_Runbook.md`**, which is also what to say at each
screen.

### Test it

```bash
python3 -m tests.test_offline                             # 60, no venv, no network
cd src/backend && .venv/bin/python -m pytest tests/ -q    # 239
cd src/frontend && npm run verify                         # typecheck, lint, no-raw-hex, build, 13 tests
```

## Two modes, and what actually stops a billed call

`NEEV_MODE` defaults to `fixture` and falls back to `fixture` for any
unrecognised value, so a typo cannot select the live path. Live mode
**additionally** requires `NEEV_ALLOW_BILLED_CALLS=1`; without it, constructing
the live runner raises. `app/services/runner.py::get_runner` is the only place
in the backend that reads the mode, and `test_no_service_but_the_runner_factory_reads_the_mode`
keeps it that way.

The backend venv and the deployed image **do** carry `google-adk` and
`google-genai`, because the live runner needs them. So the guard is not absence
of the library — it is that nothing imports it until a live run starts: the
imports sit inside method bodies, and `test_no_google_import_at_module_scope`
plus `test_serving_the_whole_app_loads_no_billed_library` fail if one escapes to
module scope. Backend tests also block outbound sockets outright
(`tests/conftest.py`, autouse).

A deployed service is capped as well — `NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY` and
`NEEV_MAX_ANALYSES_PER_DAY` — because the demo is public and a live analysis
costs real money.

### The fixtures are captured runs, not mockups

`app/fixtures/loan_*_pipeline.json` are ten **real** pipeline runs, recorded
through `scripts/record_golden_run.py` and validated against the same schemas a
live run must emit (`tests/test_fixture_contract.py`). The raw ADK session state
for each is in `.golden_runs/` — saved *before* parsing, so
`record_golden_run.py --from-raw <file>` re-parses one at no cost. Going live
changes where the object comes from and nothing else.

Loan 1001 is the golden HOLD case; 1002 is clean. The other eight came out of
the same live pipeline over synthetic BoQs, and two of them reached ESCALATE on
their own.

## Layout

- `src/agents/neev_pipeline/` — the agent package; thresholds in `config.py`,
  grounding tools in `tools/`
- `src/backend/app/` — `api/routes/`, `db/`, `schemas/`, `services/` (the
  `PipelineRunner` seam), `mappers/` (the only presentation-aware layer),
  `fixtures/`
- `src/frontend/` — `app/` (route groups `(marketing)`, `(owner)`, `(bank)`),
  `components/ui/` (the shared kit), `lib/`
- `fixtures/` — `sample_boq.pdf` (Ravi golden case: 40 items, 4 seeded flaws),
  `clean_boq.pdf` (negative test: benchmark-aligned, full scope, GST stated),
  `rate_benchmarks.csv` (30 CPWD-DSR-derived rates — see the `verified` column),
  `draw_schedule.csv` (10 loans), `site_photos/` (the golden case's real site
  photographs, served only through an authorizing endpoint), `synthetic/`
- `scripts/` — `dev.sh` (both servers, seeded), `deploy_cloudrun.sh` (Cloud
  Run, Vertex AI), `load_bigquery.sh`, `boq_data.py` + `make_sample_boq.py`
  (regenerate the BoQ PDFs), `synthetic_boqs.py`, `record_golden_run.py`
  (capture a live run into the fixture schema), `golden_run.py`,
  `verify_against_bigquery.py`
- `tests/` — offline suite, no GCP creds needed
- `docs/` — `Neev_Demo_Runbook.md` (start here to demo),
  `Neev_Idea_Submission.md` (the pitch), `Neev_Setup_Guide.md`,
  `Neev_Prod_Deploy_Plan.md`, `Neev_Two_Week_Plan.md` (cost arithmetic),
  `Neev_Demo_Video_Plan.md`, `Neev_Data_Inventory.md`, `Review_Remediation.md`
- `design_handoff_neev/` — the 16 hi-fi screen prototypes the frontend implements
- `figures/` — pitch diagrams and the landing hero

## Run the pipeline alone

Separate from the web app:

```bash
python3.11 -m venv src/agents/.venv && source src/agents/.venv/bin/activate
pip install -e src/agents
cp .env.example .env        # fill in GOOGLE_API_KEY
bash scripts/load_bigquery.sh
cd src/agents && adk web
```

Upload `fixtures/sample_boq.pdf` for loan 1001 (₹18L disbursed at slab) →
4 flags + GST_SILENT, HOLD.

A deployment authenticates to **Vertex AI** as the Cloud Run service account
rather than using an API key, because the Gemini API's free tier allows 20
`generateContent` requests per day per model — about two analyses — while Vertex
bills the project's Cloud Billing account. Three environment variables, no code
change.

Beat 4 (lender portfolio) also has a BigQuery form: `load_bigquery.sh` creates
the `portfolio_hotlist` view, worst loans first.

```sql
SELECT * FROM `<project>.buildguard_data.portfolio_hotlist` LIMIT 10
```

## Submission documents

- Idea Submission: https://docs.google.com/document/d/1JYcsxk8gSDNYBVRSKt3crod9Y1vm0gMUkrvz9cVM1YE/edit
- Demo Plan: https://docs.google.com/document/d/1UbmU8ff2jM7ZcD1E19HslLIPuDyOZtOXFG_dEy0f8YI/edit
