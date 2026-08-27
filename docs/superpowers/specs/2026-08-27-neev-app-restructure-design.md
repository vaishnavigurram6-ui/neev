# Neev — Application Restructure & Build (Design Spec)

*Date: 2026-08-27 · Status: awaiting review · Supersedes the UI portions of `docs/Neev_Implementation_Plan.md` §4*

Turn the repo from a single ADK agent package into a three-package application:
a standalone AI pipeline, a FastAPI backend, and a Next.js frontend built from
the 16 designed screens in `design_handoff_neev/`.

---

## 1. Decisions taken

| Decision | Choice | Consequence |
|---|---|---|
| Existing `buildguard/` | **Relocate and rename**, keep working | `adk web`, `golden_run.py`, 28 offline tests survive |
| Landing | **Straight to `main`** | No PR gate; each wave commits independently |
| App database | **SQLite via SQLAlchemy** | Zero-setup, seeded from `fixtures/`; swap to Postgres later behind the ORM |
| Screen scope | **8 demo screens fully built, 8 scaffolded** | Matches the four demo beats |
| Auth | **Mocked session, real boundary** | Role cookie + `get_current_user` dependency; OTP drops in later |
| Pipeline execution | **Async job + SSE progress** | Feeds the Analyzing screen's 5-phase design |
| Timeline | **Hackathon demo soon** | Every demo path needs an offline fallback |
| **Google spend** | **Zero — dry run throughout** | No Gemini, no BigQuery calls during the entire build |
| Python environments | **Per-package venvs** | `agents/.venv` and `backend/.venv`, both Python 3.11 |

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
# agents
cd agents && /opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate && pip install -r requirements.txt

# backend
cd backend && /opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate && pip install -r requirements.txt   # incl. -e ../agents
```

The backend depends on the agents package as an **editable install** (`-e ../agents`),
which is what removes every `sys.path` hack currently in `golden_run.py` and
`test_offline.py`. Both venvs are git-ignored; `.python-version` pins 3.11.

Frontend uses plain `npm` with a committed `package-lock.json`.

---

## 3. Target structure

```
neev/
├── agents/                          # AI pipeline — no knowledge of HTTP or DB
│   ├── neev_pipeline/
│   │   ├── __init__.py              # `from . import agent` — ADK discovery contract
│   │   ├── agent.py                 # root_agent: SequentialAgent of 5
│   │   ├── config.py                # thresholds, weights, LTV bands
│   │   ├── core/                    # NEW: pure functions, zero external deps
│   │   │   ├── risk.py              #   assess_tranche
│   │   │   └── boq_checks.py        #   the 4 pure BoQ checks
│   │   └── tools/                   # I/O-bearing ADK tools (BigQuery, Gemini)
│   ├── tests/test_offline.py        # the 28 tests
│   └── requirements.txt
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── api/routes/              # auth, loans, boq, tranches, portfolio, jobs
│   │   ├── db/                      # models.py, session.py, seed.py
│   │   ├── schemas/                 # Pydantic — the shared contract
│   │   └── services/
│   │       ├── pipeline_runner.py   # ADK Runner wrapper (live mode)
│   │       ├── fixture_runner.py    # recorded replay (fixture mode)
│   │       └── jobs.py              # in-process job registry + SSE broker
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app/(marketing)/             # landing, login
│   ├── app/(owner)/                 # onboarding, analyzing, boq, sanction, progress, changes
│   ├── app/(bank)/                  # portfolio, tranche, contractors, setup
│   ├── components/{ui,owner,bank}/
│   └── lib/{api.ts,format.ts,types.ts}
├── fixtures/  design_handoff_neev/  docs/  scripts/
```

**Dependency rule, strictly one-directional:** `frontend → backend → agents`.
The agents package never imports backend code.

**Naming caution:** the string `buildguard` also names the *GCP project*
(`buildguard-ai-2026`) and the *BigQuery dataset* (`buildguard_data`). These are
independent of the Python package name. A blind `sed` across the repo would
rename the data layer and break BigQuery. Only the Python package is renamed.

---

## 4. Migrating the pipeline

### 4.1 The move

`buildguard/` → `agents/neev_pipeline/`. The package is internally
relative-import clean, so only **6 absolute-import lines across 2 files** break:
five in `tests/test_offline.py` (lines 71, 72, 73, 202, 211) and one in
`scripts/golden_run.py` (line 31). Path-relative references to `../fixtures/`
and `../scripts/` also shift and must be repointed at the repo root.

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

**(b) Extract the pure core.** Six functions are pure arithmetic with zero I/O —
`assess_tranche`, `check_rate_deviation`, `check_steel_rcc_ratio`,
`check_missing_scope`, `check_payment_schedule`, plus `cumulative_weight` /
`ltv_default_prior`. Today they sit in files that import `bigquery` and `genai`
at module level, so they cannot be imported without those packages installed.
Moving them to `neev_pipeline/core/` lets the backend import and unit-test the
money math with no GCP, no credentials, and no stubs. The ADK tools become thin
wrappers that re-export them, so agent behavior is unchanged.

### 4.3 Known hazards to handle

- **`exposure_ratio` can be `float("inf")`** when `expected_total_cost` is 0 (a
  passing test exercises this). `Infinity` is not valid JSON. The Pydantic
  response model must serialize it as `null` with an explicit `exposure_undefined: true`.
- **Pipeline output is *strings*, not dicts.** Results live in
  `session.state["boq_findings"]` etc. as raw model text. `golden_run.py` verifies
  them by substring matching and counts flags with `boq.count('"type"')`. The
  backend must JSON-parse and validate each of the five `output_key` values, with
  a repair path for malformed model output.
- **Two different exposure numbers, both correct.** `assess_tranche` divides by
  `expected_total_cost` (loan 1001 → **1.03**); `portfolio_hotlist` uses
  `sanctioned` as a proxy (loan 1001 → **1.29**). The designs show 1.29 on both
  the Portfolio and Tranche Decision screens. The API must expose these as
  distinct, separately-labelled fields and never conflate them.
- **`loan_history` and `metro_city_prices` are not created by any script.**
  `load_bigquery.sh` only verifies they exist. `estimate_construction_cost`
  depends on them. Fixture mode must cover this gap.

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
| Line items, quantities, rates | `scripts/boq_data.py` — `RAVI_ITEMS` (40), `CLEAN_ITEMS` (41) |
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

### 6.2 Shared components (built in wave 0, before any screen)

`TopBar` (owner/bank/pre-auth skins), `NavTabs`, `ProfileChip`,
`AccessibilityCluster`, `StatusPill`, `StatCard`, `SegmentedToggle`, `CardTable`
(generic `columns` prop), `StickyRail` + `KeyValueCard`, `PageHeader`,
`Dropzone`, `StageStrip`, `PhotoSlot`, `Logo`, `formatINR`.

The top bar markup is byte-identical across ten files — it was copy-pasted, so
one component with a `role` prop replaces all of it. `StatusPill` is the most
repeated atom in the bundle (10+ files, six different vocabularies).

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

13 slot ids across 5 screens become `{loanId, tranche, slotKey}`.

### 6.5 Screen scope

**Fully built (8)** — the four demo beats: Landing, Login, Owner Onboarding,
Analyzing, BoQ Review, Sanction Check, Portfolio Hotlist, Tranche Decision.

**Scaffolded (7)** — routed, real layout, placeholder data, clearly marked
preview: Upload Revision, Revised Contract, Build Progress, Update Progress,
Change Orders, Contractor Scorecard, Bank Onboarding.

That is all 15 screens. The 16th file, Logo Explorations, is a reference
artboard rather than a screen — extract SVG paths from it, never port it.

---

## 7. Open design questions to resolve in wave 0

1. **Logo is inconsistent across three sources.** The Logo Explorations file
   marks turn 5a canonical (brick square + house + door + plinth bar); the 15
   screens use a simpler glyph (house path only); the bank screens use an
   entirely different white square with a `न` character. Pick one before
   building `<Logo>`.
2. **Credit-officer rationale copy does not exist.** Tranche Decision designs the
   owner/officer tab pair but only the owner panel has content. The officer text
   must be written — the `explainer` agent's `officer_view` supplies the numbers.
3. **Bank nav is inconsistent.** "Setup" appears only on Bank Onboarding; the
   other two bank screens have blank lines where it was deleted. Decide whether
   Setup is a nav item.
4. **Dead link** on Onboarding: "see a sample report" points at `href="#"`.

---

## 8. Execution plan

Contracts before fan-out. Parallel agents collide when they invent overlapping
interfaces, so the Pydantic schemas, generated TypeScript types, and the shared
component kit are all built **first and sequentially**. After that, every agent
owns disjoint files.

| Wave | Tasks | Agents | Parallel |
|---|---|---|---|
| **0** | Toolchain install · package move + 6 import fixes · lazy genai client · pure-core extraction · Pydantic schemas → TS types · Tailwind theme + 15 shared components | — | No (sequential, foundational) |
| **1** | (a) DB models + seed · (b) pipeline runner + authored fixture + SSE · (c) frontend shell, routing, API client | 3 | Yes |
| **2** | (a) Landing+Login · (b) Onboarding+Analyzing · (c) BoQ Review · (d) Sanction Check · (e) Portfolio+Tranche · (f) 7 scaffold screens · (g) backend routes | 7 | Yes |
| **3** | Integration + golden-path E2E · offline test suite green · demo runbook + README rewrite | 2 | Yes |

Wave 2's BoQ Review is the densest screen in the bundle (4 stat cards, nested
grouped table with filter state, sticky rail with three cards, share composition)
and carries the most demo weight — it gets a dedicated agent and the largest budget.

### Verification gates

No wave is complete on "code written". Each ends with commands that ran:

- Wave 0: `python -m tests.test_offline` → 28 pass · `npm run build` → clean
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
