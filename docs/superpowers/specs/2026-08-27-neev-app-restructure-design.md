# Neev — Application Restructure & Build (Design Spec)

*Date: 2026-08-27 · Status: awaiting review · Supersedes the UI portions of `docs/Neev_Implementation_Plan.md` §4*

Turn the repo from a single ADK agent package into a four-package application:
a dependency-free core, the AI pipeline, a FastAPI backend, and a Next.js
frontend built from the screens in `design_handoff_neev/`.

---

## 1. Decisions taken

| Decision | Choice | Consequence |
|---|---|---|
| Existing `buildguard/` | **Relocate and rename**, keep working | `adk web`, `golden_run.py`, 28 offline tests survive |
| Landing | **Straight to `main`** | No PR gate; each wave commits independently |
| App database | **SQLite via SQLAlchemy** | Zero-setup, seeded from `fixtures/`; swap to Postgres later behind the ORM |
| Screen scope | **8 demo screens fully built, 7 scaffolded** | Matches the four demo beats |
| Auth | **Mocked session, real boundary** | Role cookie + `get_current_user` dependency; OTP drops in later |
| Pipeline execution | **Async job + SSE progress** | Feeds the Analyzing screen's 5-phase design |
| Timeline | **Hackathon demo soon** | Every demo path needs an offline fallback |
| **Google spend** | **Zero — dry run throughout** | No Gemini, no BigQuery calls during the entire build |
| Python environments | **Per-package venvs** | `agents/.venv` and `backend/.venv` on Python 3.11; `neev_core` installed editable into both |

**Non-negotiable:** `adk web` must keep working. The demo plan states the agent
trace *"is the proof of a real multi-agent pipeline, worth more to an ADK panel
than a polished UI."* The new UI is a second surface, never a replacement.

---

## 2. Environment prerequisites (blocking — do first)

This machine cannot currently run either stack:

| Missing | Detail | Fix |
|---|---|---|
| Node.js / npm | Not installed at all | `brew install node` |
| Python ≥ 3.10 | System Python is 3.9.6; `google-adk` requires ≥ 3.10 | `brew install python@3.11` |
| `gcloud` / `bq` | Not installed | Cloud Shell, or `brew install --cask google-cloud-sdk` |

Homebrew 6.0.1 and Docker 29.7.2 are present. Until Node exists, no subagent can
run, lint, or typecheck frontend code — and unverified code at hackathon time is
the primary risk this plan guards against. Wave 0 installs the toolchain and
proves both stacks boot before any fan-out.

### 2.1 Virtual environments

Never install into system Python. Each Python package gets its own venv on 3.11,
because their dependency sets are disjoint — the backend must not carry
`google-adk` transitively, and the agents package must not carry FastAPI.

```bash
# agents — ADK pipeline (only venv that carries google-adk)
cd agents && /opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate && pip install -e ../core && pip install -e .

# backend — fixture mode needs NO ADK
cd backend && /opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate && pip install -e ../core && pip install -e .
# live mode only, when credits are approved:  pip install -e ../agents
```

Each package ships a `pyproject.toml` — without one, `pip install -e` fails
outright, and the repo currently has none. `neev_core` declares **no
dependencies at all**; `neev_pipeline` declares the ADK stack; the backend
declares FastAPI plus `neev_core`, and takes `neev_pipeline` as an optional
`[live]` extra. That is what makes "the backend does not carry `google-adk`"
literally true rather than aspirational: the default backend install cannot
import ADK, so it cannot accidentally make a billed call.

Editable installs also remove the `sys.path` hack in `golden_run.py`. Both venvs
are git-ignored; `.python-version` pins 3.11.

Frontend uses plain `npm` with a committed `package-lock.json`.

---

## 3. Target structure

```
neev/
├── core/                            # `neev_core` — pure Python, ZERO third-party deps
│   ├── neev_core/
│   │   ├── config.py                # thresholds, weights, LTV bands
│   │   ├── risk.py                  # assess_tranche
│   │   ├── boq_checks.py            # the 4 pure BoQ checks
│   │   └── boq_fixtures.py          # moved from scripts/boq_data.py
│   ├── tests/                       # pure-math tests, no stubs needed
│   └── pyproject.toml
├── agents/                          # AI pipeline — no knowledge of HTTP or DB
│   ├── neev_pipeline/
│   │   ├── __init__.py              # `from . import agent` — ADK discovery contract
│   │   ├── agent.py                 # root_agent: SequentialAgent of 5
│   │   ├── config.py                # re-exports neev_core.config for compatibility
│   │   └── tools/                   # I/O-bearing ADK tools; wrap neev_core
│   ├── tests/test_offline.py        # wiring + stubbed-import tests
│   └── pyproject.toml               # depends on neev_core
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── api/routes/              # auth, loans, boq, tranches, portfolio, jobs
│   │   ├── db/                      # models.py, session.py, seed.py
│   │   ├── schemas/                 # Pydantic — the shared contract
│   │   └── services/
│   │       ├── pipeline_runner.py   # ADK Runner wrapper (live mode)
│   │       ├── fixture_runner.py    # authored replay (fixture mode, default)
│   │       └── jobs.py              # in-process job registry + SSE broker
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/(marketing)/             # landing, login
│   ├── app/(owner)/                 # onboarding, analyzing, boq, sanction, progress, changes
│   ├── app/(bank)/                  # portfolio, tranche, contractors, setup
│   ├── components/{ui,owner,bank}/
│   └── lib/{api.ts,format.ts,types.ts}
├── fixtures/  design_handoff_neev/  docs/  scripts/
```

**Dependency rule, strictly one-directional:**

```
frontend → backend → neev_core
                  ↘ neev_pipeline (optional, live mode only) → neev_core
```

`neev_core` depends on nothing but the standard library. `neev_pipeline` never
imports backend code. The backend imports `neev_core` always and `neev_pipeline`
**only inside the live runner's function body**, so a fixture-mode install needs
no ADK at all.

**Why `neev_core` is a separate top-level package, not `neev_pipeline/core/`.**
Python executes a package's `__init__.py` before any submodule, and
`neev_pipeline/__init__.py` must keep `from . import agent` for ADK discovery.
So `import neev_pipeline.core.risk` would execute `agent.py` and therefore
`import google.adk`. Verified against the current code:

```
$ python3 -c "from buildguard.tools.disbursal_risk_tool import assess_tranche"
ModuleNotFoundError: No module named 'google'
```

The failure comes from the package `__init__`, not the tool module. A nested
`core/` would therefore deliver none of its promised benefit — the backend would
still need the full ADK stack, and the "no stubs" claim would be false. A sibling
package is the only layout that actually decouples the math from ADK.

**Naming caution:** the string `buildguard` also names the *GCP project*
(`buildguard-ai-2026`) and the *BigQuery dataset* (`buildguard_data`). These are
independent of the Python package name. A blind `sed` across the repo would
rename the data layer and break BigQuery. Only the Python package is renamed.

---

## 4. Migrating the pipeline

### 4.1 The move

`buildguard/` → `agents/neev_pipeline/`, with the pure modules lifted out to
`core/neev_core/`. The package is internally relative-import clean, so the
`buildguard.`-prefixed breakage is **6 absolute-import lines across 2 files**:
five in `tests/test_offline.py` (lines 71, 72, 73, 202, 211) and one in
`scripts/golden_run.py` (line 31).

A **seventh** import breaks without naming `buildguard` at all:
`tests/test_offline.py:293` does `from scripts.boq_data import …`, which works
today only because the suite runs from the repo root. Once tests move under
`agents/`, it fails and takes all seven `TestFixtureBoQs` tests with it — and an
editable install of `neev_pipeline` does not fix it, because `scripts/` is not
part of that package. This is why `boq_data.py` moves into `neev_core`.

Path-relative references to `../fixtures/` and `../scripts/`
(`test_offline.py:221, 223, 288`, `golden_run.py:33`) also shift and must be
repointed at the repo root. Note the existing suite has no `sys.path` hack — it
manipulates `sys.modules` to stub the Google libraries; only `golden_run.py:30`
touches `sys.path`, and the editable installs remove the need for it.

`adk web` then runs from `agents/`, discovering `neev_pipeline.agent.root_agent`.
`__init__.py` must keep `from . import agent` or discovery breaks.

### 4.2 Two refactors the backend requires

**(a) Lazy Gemini client — mandatory.** `tools/visual_inspector_tool.py:12`
executes `client = genai.Client()` at module import time. Because
`__init__.py` imports `agent`, which imports the tools, *any* process that
imports the package constructs a Gemini client and demands `GOOGLE_API_KEY`. A
FastAPI app would fail at startup with no key. Fix: adopt the lazy `_client()`
singleton pattern the two BigQuery tools already use. This also lets the offline
tests shed most of their 50 lines of `sys.modules` stubbing.

**(b) Extract the pure core into `neev_core`.** Seven functions are pure
arithmetic with zero I/O: `assess_tranche`, the four BoQ checks
(`check_rate_deviation`, `check_steel_rcc_ratio`, `check_missing_scope`,
`check_payment_schedule`), and `cumulative_weight` / `ltv_default_prior`.

They are unreachable today not because of their own imports —
`disbursal_risk_tool.py` imports only `..config`, and `config.py` imports only
`os` — but because reaching them means executing `buildguard/__init__.py`, which
pulls in ADK. Moving them into the standalone `neev_core` package (§3) is what
lets the backend import and unit-test the money math with no GCP, no credentials,
and no stubs. The ADK tools become thin wrappers that re-export them, so agent
behavior is unchanged.

`scripts/boq_data.py` moves too, becoming `neev_core.boq_fixtures`. It is pure
data with no imports, and both `tests/test_offline.py:293` and
`scripts/make_sample_boq.py` import it — an import that survives neither the
package move nor an editable install of `neev_pipeline`. Making it part of
`neev_core` fixes both callers permanently.

### 4.3 Known hazards to handle

- **`exposure_ratio` can be `float("inf")`** when `expected_total_cost` is 0 (a
  passing test exercises this). `Infinity` is not valid JSON. The Pydantic
  response model must serialize it as `null` with an explicit `exposure_undefined: true`.
- **Pipeline output is *strings*, not dicts.** Results live in
  `session.state["boq_findings"]` etc. as raw model text. `golden_run.py` verifies
  them by substring matching and counts flags with `boq.count('"type"')`. The
  backend must JSON-parse and validate each of the five `output_key` values, with
  a repair path for malformed model output.
- **Three exposure formulas are in circulation — see §4.4.** This is the single
  most dangerous ambiguity in the project and must be settled before any screen
  is built.
- **`loan_history` and `metro_city_prices` are not created by any script.**
  `load_bigquery.sh` only verifies they exist. `estimate_construction_cost`
  depends on them. Fixture mode must cover this gap.

---

### 4.4 The golden-case numbers do not agree — decide before building

⚠️ **Open decision. Blocks wave 2. Needs the owner's call.**

Loan 1001 (Ravi) is the demo's spine, and four different number sets for it are
in circulation. All were recomputed from the code and fixtures:

| Formula | Verified value | Exposure | Cost-to-complete gap | Where it lives |
|---|---|---|---|---|
| `assess_tranche` — `expected_cost × pct_complete` | ₹17.50L | **1.03** | **−₹7.50L** | `disbursal_risk_tool.py`, tested |
| `portfolio_hotlist` — `sanctioned × pct` (proxy) | ₹14.00L | **1.29** | **−₹4.00L** | `portfolio_view.sql`, tested |
| The designs | ₹13.90L | **1.29** | **−₹5.80L** | Tranche Decision screen |
| `Neev_Implementation_Plan.md` | — | **1.4** | **−₹4.20L** | Doc only — matches no formula |

The designs use a *third* model: cost-to-complete as "remaining BoQ items ×
current Kompally rates" (₹15.80L), implying a ₹29.70L total. Neither the Python
nor the SQL implements that. The Implementation Plan's 1.4 / −₹4.20L is derivable
from nothing and traces back to a speculative line in `HANDOFF.md:41`.

The BoQ total conflicts too: `RAVI_ITEMS` sums to **₹28,47,930**, while the
designs *and* the Demo Plan both say **₹32,00,000**. The designs are internally
consistent around ₹32L (45% before slab = ₹14.40L; GST at 18% = ₹5.76L), so here
the fixture is the outlier, not the designs.

**Recommendation.** Make the code authoritative for *formulas* and the fixture
authoritative for *inputs*, then reconcile the fixture upward:

1. Regenerate the Ravi BoQ so it totals **₹32,00,000**, matching the Demo Plan
   and every design. This is a fixture edit, not a code change, and it makes
   three of the four sources agree by construction.
2. Serve **`assess_tranche` (1.03 / −₹7.50L) on the per-loan Tranche Decision
   screen** and `portfolio_hotlist` (1.29 / −₹4.00L) **only on the portfolio
   table**, labelled as a screen. `portfolio_view.sql:5-8` demands exactly this
   — *"this is a SCREEN, not the per-loan verdict"* — so putting the sanction
   proxy on the verdict screen inverts the code's own stated intent.
3. Correct `Neev_Implementation_Plan.md`'s 1.4 / −₹4.20L, or mark that document
   historical.

**Cost of the recommendation:** the demo's headline exposure drops from a
dramatic 1.29 to 1.03. Still a HOLD, still correct, less punchy. The alternative —
keeping 1.29 on the per-loan screen — means either re-pricing the fixture so
`assess_tranche` genuinely returns it (expected cost ≈ ₹27.9L, which contradicts
the ₹35L "realistic cost" the whole Sanction Check beat rests on) or knowingly
showing a screen number the pipeline did not produce. The second is exactly the
"no fake precision" failure the project's own judge-proofing section forbids.

### 4.5 Portfolio rows are invented, not computed

The Portfolio design's ten rows do **not** follow from `draw_schedule.csv`. The
disbursed amounts and stages are real, but the ratios and gaps were authored.
Recomputing gives materially different values and three status flips:

| Loan | Design | Computed | Flip |
|---|---|---|---|
| 1003 | 1.42, −₹6.90L | **2.40, −₹11.22L** | — |
| 1004 | 1.35, −₹8.20L | **1.88, −₹17.57L** | — |
| 1009 | 1.04, INSPECT | **0.97** | → OK |
| 1010 | 0.96, ON TRACK | **1.01** | → REVIEW |
| 1006 | 0.98, INSPECT | **1.04** | — |

Only 1001 and 1002 match. Sort order differs too: the SQL orders by gap ascending
(1004, 1003, 1001…), the design by exposure descending (1003, 1004, 1001…).

**Decision:** the portfolio table renders **computed** values, and the design's
row figures are treated as placeholder. Ranking follows the SQL. An implementer
must not "fix" a mismatch against the mockup — the mockup is wrong here.

---

## 5. Backend design

### 5.1 Execution modes — dry run by default

`NEEV_MODE=fixture|live`, **default `fixture`**.

- **fixture** — the only mode used during this entire build. Serves authored
  pipeline output and emits the same SSE phase events with realistic pacing.
  Makes **zero network calls**: no Gemini, no BigQuery, no billed API of any kind.
- **live** — real ADK `InMemoryRunner`, Gemini, BigQuery. Mirrors `golden_run.py`:
  one multimodal user message (text + PDF bytes + photo bytes), stream events,
  read the five `output_key`s from session state. Written and type-checked, but
  **never executed during the build.**

Both satisfy one `PipelineRunner` protocol, so routes never branch on mode.

**Spend guard.** Because no Google credits may be consumed, fixture mode is not
merely the default — live mode is fenced:

- `NEEV_MODE` defaults to `fixture` when unset or unrecognized.
- Live mode additionally requires `NEEV_ALLOW_BILLED_CALLS=1`. Without it,
  constructing the live runner raises immediately with a message naming the
  variable. A typo in `NEEV_MODE` can therefore never silently start billing.
- Backend tests run with `NEEV_MODE=fixture` and a `socket`-blocking autouse
  fixture, so any accidental outbound call fails the test rather than costing money.

**The fixture data is authored, not recorded.** Recording a golden run would
itself spend credits, so the fixture is hand-built from sources already in the
repo and already consistent with each other:

| Field | Source |
|---|---|
| Line items, quantities, rates | `scripts/boq_data.py` — `RAVI_ITEMS` (40), `CLEAN_ITEMS` (43) |
| Flags and their evidence | The four seeded flaws (F1 rate outliers on 2.3/3.1/3.2; F2 missing waterproofing, external plaster, anti-termite; F3 ungraded TMT on 4.2; F4 45% before slab; GST silent) |
| Benchmark rates | `fixtures/rate_benchmarks.csv` |
| Loan/tranche context | `fixtures/draw_schedule.csv` (loan 1001 golden, 1002 clean) |
| Risk numbers | Computed live by the **pure** `assess_tranche` — real math, no I/O |
| Display figures | The design screens' own values (₹32,00,000 quoted, 9 flags, exposure 1.29, −₹5,80,000 gap) |

Risk and BoQ-check numbers are genuinely computed by the extracted pure core
rather than typed in, so the fixture path exercises real logic. What gets
substituted is exactly the billed surface: the five agents' Gemini completions,
the vision call in `verify_construction_stage`, and the BigQuery lookups in
`lookup_benchmark_rate` and `estimate_construction_cost`. Owner and officer
narrative text is authored prose stored alongside the fixture.

Once credits are available, `scripts/record_golden_run.py` (wave 3, not run)
overwrites the authored fixture with a real captured run in the same schema.

### 5.2 API surface

| Method | Path | Feeds |
|---|---|---|
| `POST` | `/api/auth/session` | Login — role + phone, sets cookie |
| `GET` | `/api/me` | ProfileChip |
| `POST` | `/api/loans/{id}/boq` | Onboarding upload → `{job_id}` |
| `GET` | `/api/jobs/{job_id}/events` | **SSE** → Analyzing |
| `GET` | `/api/loans/{id}/boq/latest` | BoQ Review |
| `GET` | `/api/loans/{id}/sanction-check` | Sanction Check |
| `POST` | `/api/loans/{id}/questions/send` | "Send 4 questions" |
| `GET` | `/api/loans/{id}/progress` | Build Progress |
| `POST` | `/api/loans/{id}/milestones` | Update Progress (photos + EXIF) |
| `GET` | `/api/portfolio` | Portfolio Hotlist |
| `GET` | `/api/loans/{id}/tranches/{n}` | Tranche Decision |
| `POST` | `/api/loans/{id}/tranches/{n}/decision` | Release / Hold / Escalate |
| `GET` | `/api/contractors` | Contractor Scorecard |

**The Analyzing screen's five phases are not the five agents.** The handoff README
claims they "map 1:1 to the ADK agents"; they do not. All five phases in the
design — reading the document, checking rates, looking for missing scope,
checking specifications, reviewing the payment schedule — are sub-steps *inside*
`boq_analyst` alone. So live mode cannot drive this screen by streaming agent
events; it needs an explicit map from ADK tool-call events to display phases:

| Phase | Advanced by |
|---|---|
| 1 Reading the document | `boq_analyst` first response with parsed line items |
| 2 Checking every rate | first `lookup_benchmark_rate` / `check_rate_deviation` call |
| 3 Looking for missing scope | `check_missing_scope` call |
| 4 Checking specifications | `check_steel_rcc_ratio` call |
| 5 Reviewing payment schedule | `check_payment_schedule` call |

The remaining four agents run after the screen has already navigated away; their
progress belongs to the screens that consume their output. Fixture mode emits
this same sequence on a timer.

SSE event shape, matching the Analyzing screen exactly:

```json
{"type":"phase","index":2,"status":"running","name":"Looking for missing scope"}
{"type":"finding","flag":"Rate +22%","tone":"danger","text":"RCC M25 is priced at ₹9,800/cum…"}
{"type":"progress","pct":38,"detail":"item 17 of 40 · section 6, plastering","eta_s":40}
{"type":"done","redirect":"/owner/boq/1001"}
```

### 5.3 Data model (SQLite)

`Loan`, `BoqRevision`, `LineItem`, `Flag`, `Question`, `Tranche`, `Photo`,
`ChangeOrder`, `Decision`, `Contractor`, `Job`.

Seeded from `fixtures/draw_schedule.csv` (10 loans, 1001–1010) and
`scripts/boq_data.py` (`RAVI_ITEMS` 40 items, `CLEAN_ITEMS` 41). Borrower names
and localities come from the Portfolio design's `loans[]` array so the seeded
book matches the screens exactly (1003 K. Srinivas 1.42, 1004 P. Anjali 1.35,
1001 Ravi Kumar 1.29, …).

Seeding is idempotent and rerunnable — `python -m app.db.seed --reset`.

---

## 6. Frontend design

### 6.1 What the `.dc.html` files are

Prototype markup for a canvas runtime. `<x-dc>`, `<helmet>`, and the referenced
`support.js` (which does not exist in the bundle) are all scaffolding — discard
them. Only the inner `<div data-screen-label>` and each file's `renderVals()`
matter. Conversion is mechanical: `<sc-for>` → `.map()`, `<sc-if>` → `&&`,
`{{ expr }}` → `{expr}`, `style-hover="…"` → a Tailwind `hover:` variant.

**Critical porting rule:** `renderVals()` mixes domain data with presentation
tokens in the same objects — a table row carries `desc` and `figures` alongside
`pillBg` and `pillFg`. Split them. Domain fields come from the pipeline; color
fields collapse into a `tone: 'danger'|'warn'|'success'|'neutral'` enum resolved
by the theme. Every `pillBg`/`pillFg` pair in the designs must disappear.

Money is stored pre-formatted in the prototypes (`"₹32,00,000"`,
`"12 cum × ₹9,800 = ₹1,17,600"`). Never persist display strings — store numbers,
render through one `formatINR()` helper with full Indian grouping.

### 6.1a Fidelity: directional reference, not a pixel contract

The `.dc.html` files are **partial mockup fragments generated in Claude Design** —
selected pieces of a larger intended product, not a finished or exhaustive
specification. The handoff README's instruction to "recreate pixel-perfectly" is
therefore read as *honor the visual language*, not *reproduce each file byte for
byte*. This is the correct reading of the evidence: the files disagree with each
other in ways only fragments do — three different logo treatments, a nav item
present on one bank screen and deleted from two others, a designed officer tab
with no copy behind it, dead `href="#"` links, and pre-formatted display strings
standing in for computed values.

Consequences for the build:

- **The component kit is the source of truth, not any individual file.** Where
  screens disagree, the kit wins and the odd screen is brought into line — never
  the reverse, and never by forking a component.
- **Gaps are filled by extending existing patterns**, not by inventing new ones.
  Screens the mockups never covered (empty states, error states, the officer
  rationale panel) are composed from the same primitives so they look native to
  the system rather than bolted on.
- **Consistency outranks fidelity to any single mockup.** If matching one file
  exactly would make it inconsistent with the rest, match the rest.

### 6.2 Shared components (built in wave 0, before any screen)

`TopBar` (owner/bank/pre-auth skins), `NavTabs`, `ProfileChip`,
`AccessibilityCluster`, `StatusPill`, `StatCard`, `SegmentedToggle`, `CardTable`
(generic `columns` prop), `StickyRail` + `KeyValueCard`, `PageHeader`,
`Dropzone`, `StageStrip`, `PhotoSlot`, `Logo`, `formatINR`.

The top bar recurs near-identically across ten files, differing only in which
nav tab carries the active styling — so one component with `role` and `active`
props replaces all of it. `StatusPill` is the most
repeated atom in the bundle (10+ files, six different vocabularies).

**Reuse is enforced, not encouraged.** The mockups hardcode hex hundreds of times
across fifteen files; if that survives the port, retoning becomes impossible and
the screens drift apart. So:

- **No inline hex in any screen.** Colors come only from theme tokens. A lint
  rule fails the build on a raw `#rrggbb` outside the theme file.
- **No bespoke per-screen components.** A screen may compose and lay out kit
  components; it may not define its own pill, card, table, or bar. Needing a new
  variant means extending the kit with a prop, in the kit's own file, so every
  other screen inherits it.
- **One vocabulary per concept.** `tone` is the only status dimension
  (`danger | warn | success | neutral`), used identically by flags, tranche
  status, question status, bank actions, contractor tiers, and confidence. Six
  different vocabularies in the mockups collapse into this one.
- **One formatter.** Every rupee figure renders through `formatINR()`; no screen
  stores or emits a pre-formatted money string.
- **Two skins, one system.** Owner (warm neutral, 20–24px radii) and bank (dark
  `#111827` chrome, 10px radii) are props on the same components, never parallel
  component trees. This is what keeps the two consoles recognizably one product.

Screens are reviewed for kit compliance in wave 3: any screen importing something
the kit should own is a defect, including the scaffolded ones.

### 6.3 Theme

Only `Neev Landing.dc.html` uses CSS custom properties (`--bg --card --ink --sub
--faint --line --act --actHover`) with a working `body.dark`. The other 15 files
hardcode hex inline hundreds of times. Wave 0 lifts Landing's variable block plus
the handoff README's token table into a single Tailwind theme, because the README
warns the palette was still under discussion — retoning must stay cheap.

Fonts: Baloo 2 (headings/brand/CTAs, chosen for Devanagari support), Instrument
Sans (body/UI), JetBrains Mono (all numbers, ids, ratios).

### 6.4 `PhotoSlot` replaces `image-slot.js`

The prototype element stores data-URLs in a sidecar JSON file via
`window.omelette` — pure design-runtime infrastructure with no production role.
Keep three behaviors: client-side downscale before upload, the image accept-list
(png/jpeg/webp/avif), and a crop/fit notion for same-angle comparison. Add what
production needs: real upload, and **EXIF geotag + timestamp extraction**, which
feeds the `visual_inspector` agent and renders as the verdict chips the designs
already show ("✓ Geotag matches Plot 47", "✓ Timestamp 10 Aug, 11:42").

12 slot ids across 4 screens become `{loanId, tranche, slotKey}`.

### 6.5 Screen scope

**Fully built (8)** — the four demo beats: Landing, Login, Owner Onboarding,
Analyzing, BoQ Review, Sanction Check, Portfolio Hotlist, Tranche Decision.

**Scaffolded (7)** — routed, real layout, placeholder data, clearly marked
preview: Upload Revision, Revised Contract, Build Progress, Update Progress,
Change Orders, Contractor Scorecard, Bank Onboarding.

That is all 15 screens. The 16th file, Logo Explorations, is a reference
artboard rather than a screen — extract SVG paths from it, never port it.

---

### 6.6 Routing

The prototypes navigate by relative `.dc.html` links. Those become real routes —
never client-side-only state — so every screen is deep-linkable, shareable,
bookmarkable, and works with browser back/forward.

| Prototype file | Route |
|---|---|
| Neev Landing | `/` |
| Neev Login | `/login` |
| Neev 0 Owner Onboarding | `/owner/onboarding` |
| Neev 0b Analyzing | `/owner/loans/[loanId]/analyzing` |
| Neev 1 BoQ Review | `/owner/loans/[loanId]/boq` |
| Neev 1a Upload Revision | `/owner/loans/[loanId]/boq/revise` |
| Neev 1b Revised Contract | `/owner/loans/[loanId]/boq/rev/[rev]` |
| Neev 2 Sanction Check | `/owner/loans/[loanId]/sanction` |
| Neev 3 Build Progress | `/owner/loans/[loanId]/progress` |
| Neev 3b Update Progress | `/owner/loans/[loanId]/progress/report` |
| Neev 6 Change Orders | `/owner/loans/[loanId]/changes` |
| Neev 4 Portfolio Hotlist | `/bank/portfolio` |
| Neev 3 Tranche Decision | `/bank/loans/[loanId]/tranches/[n]` |
| Neev 5 Contractor Scorecard | `/bank/contractors` |
| Neev 7 Bank Onboarding | `/bank/setup` |

Rules that fall out of this:

- **Revisions are routes, not state.** The designs already treat them that way —
  Revised Contract's "Rev 1" toggle is an `<a href>` back to BoQ Review, so
  `/boq/rev/1` and `/boq/rev/2` are distinct URLs. `/boq` resolves to the latest.
- **Route groups carry the chrome, but not the URL.** `(marketing)`, `(owner)`,
  and `(bank)` each own a `layout.tsx` supplying the right top bar, nav, and
  profile chip, so no screen re-implements it — that is what makes the bank's
  dark `#111827` console chrome automatic. **Parenthesised segments are excluded
  from the URL**, so the `/owner/…` and `/bank/…` prefixes in the table above
  require a real directory inside the group:
  `app/(owner)/owner/loans/[loanId]/boq/page.tsx`. Getting this wrong silently
  serves `/loans/1001/boq` instead, and two agents would otherwise resolve it two
  different ways.
- **Filters and tabs belong in the URL.** BoQ Review's Flagged/All toggle,
  Portfolio's All/Needs-action/On-track filter, and Tranche Decision's
  owner/officer tabs become search params (`?view=flagged`) so a shared link
  reproduces what the sender saw — which matters when a credit officer sends a
  loan to a colleague.
- **Every dynamic route needs `loading.tsx`, `error.tsx`, and `not-found.tsx`.**
  An unknown `loanId` must render a real 404, not a crash or an empty shell.
- **Role enforcement lives in middleware**, redirecting to `/login` with a
  `?next=` param. Owner routes reject bank sessions and vice versa. The mock
  session still exercises this boundary so real auth is a drop-in.
- Fix the two link defects the prototypes carry: Onboarding's "see a sample
  report" points at `href="#"`, and only loan 1001 has a real drill-in href on
  the Portfolio table — every row must link to its own tranche page.

### 6.7 Web fundamentals — non-negotiable in the port

The prototypes are canvas mockups, not web pages: **there is not a single
`<button>`, `<input>`, or `<form>` in the entire bundle.** Every control is a
styled `<div>`, the phone field is a div containing placeholder text, and the
voice-note textarea is a div. Ported literally, nothing would be keyboard
reachable, screen readers would announce nothing, and no form would submit. The
port restores real semantics.

**Semantics.** Actions are `<button>`; navigation is `<a>`; the BoQ, portfolio,
scorecard and math grids are `<table>` (CSS grid for layout, table semantics for
meaning) so row and column relationships survive; one `<main>`, `<nav>`,
`<header>` per page; headings nest correctly with exactly one `<h1>`.

**Accessibility (WCAG 2.1 AA).** This product is aimed at first-time home
builders who "don't speak builder" — accessibility is core to the premise, not a
checkbox. Every interactive element is keyboard reachable in logical order with a
visible focus ring. Segmented toggles use `role="tablist"`/`aria-selected` and
respond to arrow keys. Status is never conveyed by color alone: every pill keeps
its text label, so "Rate +22%" reads correctly to someone who cannot distinguish
the red tint. Photo slots get real labels and upload status is announced via a
live region.

Three handoff tokens were measured against AA and **fail as specified**:

| Token | On | Ratio | Verdict |
|---|---|---|---|
| `faint #9b938a` | `bg #faf9f7` | 2.88:1 | Fails at any size |
| `brick #b4552e` | tint `#f9ece5` | 4.24:1 | Fails at the 11px pill size |
| `sand #8a6d4f` | tint `#f4efe6` | 4.19:1 | Fails at the 11px pill size |

The brick and sand pairs are the flag pills — the most repeated element in the
bundle (10+ files, six vocabularies) — and the designs set them at 11px, which is
normal text needing 4.5:1, not large text needing 3:1. Wave 0 darkens these three
tokens just enough to clear AA and re-measures, keeping the palette's character.
Everything else measured clean: `sub` 5.38:1, `action` 5.12:1, `green` 6.00:1,
`ink` 14.22:1, and the bank bar's inactive grey 6.99:1. The design's own `role="button"`
`aria-label` usage is inconsistent across files; normalize it rather than copying
it verbatim.

The accessibility cluster the designs place on every owner screen is **specified
as functional, not decorative** (handoff README: "mocked in prototype, must be
functional in build"). In this build: the theme toggle works app-wide, and the
language switcher and listen-aloud control render with correct semantics and
disabled state, since translation and TTS are out of scope. A disabled control
that announces why beats a dead control that lies.

**Viewport: laptop only.** Users work on laptops, so v1 targets laptop widths and
builds no phone layouts. The designs agree — every artboard is a fixed 1440px
canvas (`$preview.width: 1440`).

- **Supported range: 1280–1920px**, verified at 1280, 1440, and 1920. 1440 is the
  design width and the demo width.
- Content sits in a centered `max-width` (920–1280px per the handoff) so 1920
  screens do not stretch text to unreadable line lengths.
- The two-column `1fr 340px` shells stay two-column throughout the range; the
  sticky rail stays a rail. No collapse behavior is built.
- **Below 1280 the layout degrades gracefully but is not a target**: wide tables
  scroll inside their own `overflow-x` container so the page body never scrolls
  horizontally, and nothing is clipped or overlapped. This costs almost nothing
  and prevents an embarrassing break if a demo machine runs 1024 or a projector
  forces a smaller effective width.

No mobile breakpoints, no touch affordances, no hamburger nav in v1. Phone
support is a later phase (§7.5).

**Performance.** Fonts via `next/font` with `display: swap` and preconnect, so
Baloo 2 and JetBrains Mono do not block first paint. Server Components by default
— only genuinely interactive screens (Analyzing's stream, BoQ Review's filter,
Change Orders' mutations) opt into the client. Site photos go through
`next/image` with explicit dimensions to prevent layout shift, and are downscaled
client-side before upload. Route-level code splitting is automatic; keep it that
way by not barrel-importing the component kit.

**Metadata.** Per-route `title` and `description`; Open Graph on the landing page
only. Owner and bank routes are `noindex` — they render private loan data.

**States.** Every data-driven screen implements four states, not one: loading
(skeletons matching final layout, so nothing jumps), empty, error with a retry
affordance, and populated. The prototypes only ever show the populated state,
which is the single easiest thing to forget when porting from a mockup.

**Forms.** Real `<form>` elements with controlled inputs, inline validation tied
to fields via `aria-describedby`, disabled-and-labelled submit while pending, and
no double-submit. This covers Login's phone/OTP, Onboarding's three-step wizard,
Update Progress's milestone-plus-photos submission, and Bank Onboarding's
threshold settings.

**Theme.** Only the Landing prototype implements dark mode. Its
`body` / `body.dark` custom-property block is lifted into the app-wide theme so
every screen honors the toggle and `prefers-color-scheme`, with the choice
persisted.

---

## 7. Gaps the mockups leave open — decided in wave 0

These are fragment artifacts rather than genuine ambiguities. Each is decided
once, recorded here, and applied everywhere by the component kit.

1. **Logo appears in three treatments.** The explorations file marks turn 5a
   canonical (brick square + house + door + plinth bar); eleven screens use a
   simpler house-only glyph; the bank screens use a white square with a `न`
   character. *Decision: adopt the simple house glyph as `<Logo>` for both roles,
   recolored per skin — it is what eleven of the fifteen screens already show, and one mark
   across both consoles is what makes them read as one product. The 5a
   door-and-plinth variant is kept for brand/marketing use only.*
2. **Credit-officer rationale copy does not exist.** Tranche Decision designs the
   owner/officer tab pair but only the owner panel has content. *Decision: write
   it in the bank voice — compact and factual — sourced from the `explainer`
   agent's `officer_view`, citing exposure, verified value, and the evidence list.*
3. **Bank nav is inconsistent.** "Setup" appears only on Bank Onboarding; the
   other three bank screens carry blank lines where it was removed. *Decision:
   Setup stays in the nav on all bank routes — it owns the thresholds that drive
   every recommendation, so it must remain reachable.*
4. **Dead and partial links.** Onboarding's "see a sample report" points at
   `href="#"`, and only loan 1001 has a real drill-in on the Portfolio table.
   *Decision: point the sample link at the golden case's BoQ Review, and generate
   every portfolio row's href from its own loan id.*
5. **Mobile is undesigned** — every artboard is a fixed 1440px canvas.
   *Decision (owner's call): laptop is the primary and only v1 target. Users work
   on laptops, so no phone layouts are built. The supported range is 1280–1920px
   with graceful degradation below it (§6.7). Phone support is a deliberate later
   phase rather than debt — when it comes, the public Landing page is the natural
   first candidate, and the kit's token-and-props structure means adding
   breakpoints then does not require re-authoring screens.*

---

## 8. Execution plan

Contracts before fan-out. Parallel agents collide when they invent overlapping
interfaces, so the Pydantic schemas, generated TypeScript types, and the shared
component kit are all built **first and sequentially**. After that, every agent
owns disjoint files.

| Wave | Tasks | Agents | Parallel |
|---|---|---|---|
| **0** | Toolchain install · 4-package split with `pyproject.toml`s · package move + 7 import fixes · `boq_data`→`neev_core` · lazy genai client · **golden-number reconciliation (§4.4)** · AA token fixes · Pydantic schemas → TS types · Tailwind theme + shared component kit | — | No (sequential, foundational) |
| **1** | (a) DB models + seed · (b) pipeline runner + authored fixture + SSE · (c) frontend shell, routing, API client | 3 | Yes |
| **2** | (a) Landing+Login · (b) Onboarding+Analyzing · (c) BoQ Review · (d) Sanction Check · (e) Portfolio+Tranche · (f) 7 scaffold screens · (g) backend routes | 7 | Yes |
| **3** | Integration + golden-path E2E · offline test suite green · demo runbook + README rewrite | 2 | Yes |

Wave 2's BoQ Review is the densest screen in the bundle (4 stat cards, nested
grouped table with filter state, sticky rail with three cards, share composition)
and carries the most demo weight — it gets a dedicated agent and the largest budget.

### Verification gates

No wave is complete on "code written". Each ends with commands that ran:

- Wave 0: all 28 existing tests pass after the split (7 of them, `TestFixtureBoQs`,
  depend on the `boq_data` → `neev_core` move) · `npm run build` → clean ·
  `pip install -e` succeeds for all three Python packages
- Wave 1: backend boots, `/api/portfolio` returns 10 loans, SSE stream observed
- Wave 2: every route renders; typecheck and build clean
- Wave 3: golden path passes end-to-end in **fixture mode with no credentials
  and no network**

Every gate runs in fixture mode. Live mode is never invoked in any wave — it
ships code-complete and unexercised, to be validated by the user in Cloud Shell
when credits are available.

The existing `tests/test_offline.py` stub pattern is the model: it runs in 0.002s
with no ADK, no BigQuery, no network. Backend tests adopt the same discipline
against the extracted pure core.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| No Node/Python 3.10 locally → unverifiable code | Wave 0 installs both and proves boot before fan-out |
| **Accidental Google spend during the build** | Fixture default + `NEEV_ALLOW_BILLED_CALLS` fence + socket-blocked tests |
| **Live path ships unexercised** (accepted trade-off of the dry run) | Shares the pure core and response schemas with the tested fixture path, so only the billed I/O calls are unproven; user validates in Cloud Shell |
| Live Gemini/BigQuery fails during demo | `NEEV_MODE=fixture` serves the authored run with zero external calls |
| Restructure breaks the working `adk web` demo | Relocate rather than rewrite; 28 tests gate every wave |
| Parallel agents conflict | Contracts and shared components precede all fan-out; disjoint file ownership |
| New UI overshadows the ADK trace the judges want | `adk web` stays first-class; UI is the second surface |
| Model returns malformed JSON in state | Parse-and-validate layer with an explicit repair path |
| Benchmark rates still unverified (30 rows say `verified: NO`) | Out of scope here; remains an open demo-credibility item |

---

## 10. Out of scope

Real OTP/SMS · Postgres · deployment/CI · WhatsApp send integration · marked-up
PDF generation (button present, stubbed) · counter-rate composer modal (implied,
never designed) · Hindi/Telugu translation (switcher renders, EN only) ·
text-to-speech · CPWD DSR rate verification.
