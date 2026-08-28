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

## The application

Three packages, one direction of dependency:

```
src/frontend  →  src/backend  →  authored, pipeline-shaped fixtures
src/agents    →  standalone, driven by `adk web`
```

- **`src/agents/neev_pipeline/`** — the ADK pipeline above. Run `adk web` from
  `src/agents/`; it discovers `neev_pipeline.agent.root_agent`. Unchanged by the
  application work.
- **`src/backend/`** — FastAPI + SQLAlchemy + SQLite. 17 API paths, 115 tests.
  Declares **no** Google dependency: there is no `google` package in its venv, so
  it cannot make a billed call.
- **`src/frontend/`** — Next.js App Router + Tailwind v4. 17 routes, all 15
  handoff screens, role enforcement in `proxy.ts`.

### Run it

```bash
bash scripts/dev.sh          # both servers, seeded, fixture mode
```

Prints the four demo URLs. See **`docs/Neev_Demo_Runbook.md`** for what to say at
each one.

### Test it

```bash
python3 -m tests.test_offline                                  # 28, no venv, no network
cd src/backend && .venv/bin/python -m pytest tests/ -q         # 115
cd src/frontend && npm run verify                              # typecheck, lint, no-raw-hex, build
```

`src/backend/tests/test_golden_path.py` walks all four demo beats through the real
HTTP surface, and asserts structurally that no billed call is reachable.

### Fixture mode, and why

`NEEV_MODE` defaults to `fixture` and falls back to `fixture` for any
unrecognised value, so a typo cannot select the live path. Live mode additionally
requires `NEEV_ALLOW_BILLED_CALLS=1`; without it, constructing the live runner
raises. Backend tests block outbound sockets.

The fixtures are **shaped like the pipeline's real output** — the five ADK
`output_key` shapes — not like the screens, and
`src/backend/tests/test_fixture_contract.py` proves every fixture validates
against the schemas a live run must emit. So going live changes where the object
comes from and nothing else. `scripts/record_golden_run.py` captures a real run
into the same schema; it refuses to start unless billed calls are explicitly
permitted.

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
  `rate_benchmarks.csv` (30 CPWD-DSR-derived rates — see `verified` column),
  `draw_schedule.csv` (10 loans; 1001 = golden HOLD case, 1002 = clean case)
- `scripts/` — `dev.sh` (start both servers, seeded, fixture mode),
  `load_bigquery.sh` (loads fixtures + portfolio view), `boq_data.py` +
  `make_sample_boq.py --all` (regenerate both BoQ PDFs), `golden_run.py`
  (programmatic pipeline test loop, needs GCP), `record_golden_run.py`
  (captures a live run into the fixture schema — refuses to run unless billed
  calls are explicitly permitted)
- `tests/` — offline suite, no GCP creds needed: `python3 -m tests.test_offline`
- `docs/` — `Neev_Demo_Runbook.md` (start here to demo), setup guide,
  `superpowers/specs/` and `superpowers/plans/` for the design and build plan
- `figures/` — 6 pitch diagrams
- `HANDOFF.md` — day-1 drop notes and remaining to-dos

## Run the pipeline alone (Cloud Shell)

Separate from the web app, and the only part that spends credits:

```bash
python3.11 -m venv src/agents/.venv && source src/agents/.venv/bin/activate
pip install -e src/agents
cp .env.example .env        # fill in GOOGLE_API_KEY
bash scripts/load_bigquery.sh
cd src/agents && adk web --allow_origins 'regex:https://.*\.cloudshell\.dev'
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
