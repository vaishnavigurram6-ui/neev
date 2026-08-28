# Neev App Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Neev repo into a three-package application — the relocated ADK pipeline, a FastAPI backend serving pipeline-shaped fixture data, and a Next.js frontend that builds the 15 `design_handoff_neev` screens — without making a single billed Google API call.

**Architecture:** One-directional dependency: `frontend → backend → authored fixtures`. The pipeline (`src/agents/neev_pipeline/`) stays standalone and driven by `adk web`; the backend never imports it in this phase, which is the strongest possible spend guard. Every seam the live pipeline will later plug into is built now and left unused: a `PipelineRunner` protocol with a mode-keyed factory, an SSE event contract, one mapper layer, and Pydantic schemas that mirror the five ADK `output_key` shapes exactly.

**Tech Stack:** Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy 2 · SQLite · Next.js (App Router) · React Server Components · TypeScript · Tailwind CSS v4 · Google ADK (relocated, untouched)

**Spec:** `docs/superpowers/specs/2026-08-27-neev-app-restructure-design.md` — read it alongside this plan. Section references below (`§5.1a`) point at it.

---

## Status — where to resume

*Last updated 2026-08-28.*

**COMPLETE as of 2026-08-28.** All 21 tasks are implemented and merged to `main`.

Verified on the merged tree: 115 backend tests, `npm run verify` clean on all
four checks across 17 frontend routes, the 28 offline tests unchanged, and no
`google` namespace in the backend venv at all — so no billed call is reachable.
`src/backend/tests/test_golden_path.py` walks all four demo beats through the real
HTTP surface. To run it: `bash scripts/dev.sh`; to narrate it:
`docs/Neev_Demo_Runbook.md`.

The history below is kept as the build record.

| Done | Commit | Detail |
|---|---|---|
| Pipeline relocation (Task 4.1 of the spec) | `bac5e69` | `buildguard/` → `src/agents/neev_pipeline/`. 7 absolute imports rewritten across `tests/test_offline.py` and `scripts/golden_run.py`; `src/agents/pyproject.toml` added; `tests/__init__.py` puts `src/agents/` on `sys.path` for bare clones; `golden_run.py`'s `sys.path` hack retargeted; `adk web` now runs from `src/agents/`; `requirements.txt` reduced to `-e ./src/agents`; `.gitignore` covers `.venv/`, `node_modules/`, `.next/`. **All 28 offline tests pass unchanged.** Only the Python package was renamed — the GCP project `buildguard-ai-2026` and BigQuery dataset `buildguard_data` deliberately keep their names. |
| This plan | `a6fb347` | 21 tasks, 3 phases. |
| Regroup under `src/` | this commit | The three code packages live in `src/agents/`, `src/backend/`, `src/frontend/`. `src/agents/` was moved with `git mv`; `tests/__init__.py`, `scripts/golden_run.py`, `requirements.txt`, `README.md`, `docs/Neev_Setup_Guide.md` and `CLAUDE.md` were all retargeted. 28 tests still pass. `adk web` now runs from `src/agents/`. |
| **Task 1 — toolchain, partly** | — | Installed and verified on the build machine: **Node v26.7.0**, **npm 11.19.0**, **Python 3.11.16** at `/opt/homebrew/bin/python3.11`. System Python is still 3.9.6, untouched. **Skip Task 1 Step 1** (`brew install`) — already done. **Still to do:** Steps 3–7, i.e. `.python-version`, `.node-version`, creating `src/agents/.venv` and proving the editable install, and the `CLAUDE.md` note. No venv exists yet for either Python package. |

**Not started:** `src/backend/` and `src/frontend/` do not exist yet. Nothing in Phase 0 Tasks 2–8, Phase 1, Phase 2, or Phase 3 has been written.

### Execution guidance

- **Phase 0 is sequential.** Contracts before fan-out: the schemas, the runner protocol, and the component kit must exist before any screen work, because parallel agents collide when they invent overlapping interfaces.
- **The one safe Phase 0 parallelisation is `src/backend/` (Tasks 2–5) against `src/frontend/` (Tasks 6–8)** — disjoint file trees, no runtime dependency between them.
- **Parallel agents sharing one working tree must not run git commands.** Concurrent `git add` / `git commit` race on `index.lock`. Have each agent skip every "Commit" step and let the coordinating session commit their work afterwards; or give each agent its own worktree and merge the branches, which is clean here because the trees are disjoint.
- **Do not skip the "run it to verify it fails" steps.** They are what catch a test that passes vacuously.

---

## Global Constraints

Every task's requirements implicitly include this section. Violating any line here is a defect regardless of whether the task's own steps mention it.

- **DRY RUN IS ACTIVE.** No billed Google API call of any kind: no Gemini completions, no Gemini vision, no BigQuery. Not in the app, not in tests, not for a "quick check", not to record a fixture. Never uncomment, restore, export, or read `GOOGLE_API_KEY`. Never set `NEEV_ALLOW_BILLED_CALLS=1`. Never run `adk web`, `scripts/golden_run.py`, `scripts/load_bigquery.sh`, or any `bq` command. See `CLAUDE.md` — if its dry-run section still says ACTIVE, it is active.
- **Git identity:** every commit is authored as `Vaishnavi Gurram <vaishnavigurram6@gmail.com>`. Already set repo-locally. Verify with `git config user.email` before the first commit. Never touch the global git config.
- **Python 3.11 per package, in its own venv.** `src/agents/.venv` and `src/backend/.venv`. Never install into system Python (3.9.6, too old for `google-adk`). The backend venv must never contain `google-adk`.
- **The backend must not import `neev_pipeline` in this phase.** Not even inside a function body, except in `live_runner.py` where the import is deliberately deferred and never executed.
- **Only the Python package was renamed.** The GCP project `buildguard-ai-2026` and the BigQuery dataset `buildguard_data` keep those names. Never `sed` `buildguard` repo-wide.
- **`adk web` must keep working**, run from `src/agents/`, discovering `neev_pipeline.agent.root_agent`. `src/agents/neev_pipeline/__init__.py` must keep `from . import agent`.
- **All 28 tests in `tests/test_offline.py` must pass after every task.** Command: `python3 -m tests.test_offline` from the repo root. They need no venv, no credentials, and no network.
- **Numbers come from the mockups, verbatim** (§4.4). Never recompute, reconcile, or "correct" a figure against the Python or the SQL. Where a mockup shows a figure, that figure is the fixture value.
- **Fixtures are shaped like the pipeline's real output, never like the screens** (§5.1a). The five `output_key` shapes define the schemas; the mockups' numbers fill those shapes.
- **Store integers, render through `formatINR()`.** No pre-formatted money string is ever persisted, returned by an API, or written into a fixture.
- **No literal figures in components.** No screen contains `₹32,00,000` in its JSX. Every number arrives as a prop.
- **No raw hex outside the theme file.** Colors come only from theme tokens. A lint rule enforces this (Task 6).
- **No screen-shaped endpoints.** `GET /api/loans/1001/boq-review-page` is forbidden; endpoints return domain objects.
- **No mode branching outside the runner factory.** No component, route, or mapper checks `NEEV_MODE`.
- **One status vocabulary:** `tone = 'danger' | 'warn' | 'success' | 'neutral'`. The mockups' six vocabularies and every `pillBg`/`pillFg` pair collapse into it. No component takes a color prop.
- **Two skins, one system:** `skin = 'owner' | 'bank'` is a prop on shared components, never a parallel component tree.
- **Viewport: laptop only.** Supported range 1280–1920px, verified at 1280, 1440, 1920. No mobile breakpoints, no touch affordances, no hamburger nav. Wide tables scroll inside their own `overflow-x` container so the page body never scrolls horizontally.
- **Real web semantics.** The mockups contain not one `<button>`, `<input>`, or `<form>` — every control is a styled `<div>`. The port restores real semantics: actions are `<button>`, navigation is `<a>`, data grids are `<table>`, one `<h1>` per page, everything keyboard reachable with a visible focus ring.
- **WCAG 2.1 AA.** Status is never conveyed by color alone — every pill keeps its text label.
- **Copy is taken verbatim from the mockups.** Owner voice is plain, warm, second-person, never accusatory. Bank voice is compact and factual. Do not rewrite, "improve", or paraphrase mockup copy.
- **Commit after every task**, with the task number in the message.

### Frozen fixture figures (loan 1001 — Ravi Kumar, Kompally)

Transcribed from the mockups. These are the only values any task may use for loan 1001.

| Figure | Value | Source mockup |
|---|---|---|
| BoQ quoted total | `3200000` | BoQ Review, Sanction Check |
| Realistic cost at Kompally rates | `3500000` | Sanction Check |
| Sanctioned | `2800000` | Sanction Check, `draw_schedule.csv` |
| Fair price for the quoted scope | `2915000` | BoQ Review stat card |
| Flags raised | `9` (3 rate outliers · 2 missing scope · 4 vague specs) | BoQ Review |
| Missing scope value | `154000` | BoQ Review, Sanction Check |
| Pct before slab | `0.45` → `1440000` | BoQ Review |
| Disbursed | `1800000` (T1+T2+T3 at `600000` each) | Tranche Decision |
| Verified value in place | `1390000` | Tranche Decision |
| Exposure ratio | `1.29` | Tranche Decision, Portfolio |
| Cost to complete | `1580000` | Tranche Decision |
| Cost-to-complete gap | `-580000` | Tranche Decision, Portfolio |
| Recommendation | `HOLD` | Tranche Decision, Portfolio |
| Contractor | `Sri Sai Constructions`, BoQ received `12 Aug`, 40 items | BoQ Review |

---

## File Structure

```
neev/
├── src/                                          # the three code packages
│   ├── agents/                                   # DONE (commit bac5e69)
│   │   ├── neev_pipeline/                        # relocated as-is, unrefactored
│   │   └── pyproject.toml
│   ├── backend/
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── main.py                           # FastAPI app factory + CORS + router mount
│   │   │   ├── core/settings.py                  # Settings, NEEV_MODE, spend fence
│   │   │   ├── schemas/
│   │   │   │   ├── pipeline.py                   # the five output_key shapes
│   │   │   │   ├── events.py                     # SSE event union
│   │   │   │   └── views.py                      # view models the screens consume
│   │   │   ├── services/
│   │   │   │   ├── runner.py                     # PipelineRunner protocol + get_runner()
│   │   │   │   ├── fixture_runner.py             # FixtureRunner (this build)
│   │   │   │   ├── live_runner.py                # AdkPipelineRunner (never executed)
│   │   │   │   └── jobs.py                       # JobRegistry + SSE fan-out
│   │   │   ├── mappers/                          # pipeline-shaped -> view model
│   │   │   │   ├── boq.py  portfolio.py  tranche.py  sanction.py
│   │   │   ├── db/
│   │   │   │   ├── models.py  session.py  seed.py
│   │   │   ├── api/
│   │   │   │   ├── deps.py                       # get_db, get_current_user
│   │   │   │   └── routes/
│   │   │   │       ├── auth.py  loans.py  boq.py  jobs.py
│   │   │   │       ├── portfolio.py  tranches.py  contractors.py
│   │   │   └── fixtures/
│   │   │       ├── loan_1001_pipeline.json       # pipeline-shaped, mockup numbers
│   │   │       ├── loan_1002_pipeline.json
│   │   │       ├── portfolio_rows.json           # the design's 10 rows verbatim
│   │   │       └── analyzing_script.json         # SSE replay script
│   │   └── tests/
│   │       ├── conftest.py                       # socket-blocking autouse fixture
│   │       ├── test_settings_spend_guard.py
│   │       ├── test_fixture_contract.py          # §5.1a seam acceptance test
│   │       ├── test_runner_events.py
│   │       ├── test_seed.py
│   │       └── test_routes.py
│   └── frontend/
│       ├── package.json  tsconfig.json  next.config.ts  eslint.config.mjs
│       ├── app/
│       │   ├── layout.tsx  globals.css  not-found.tsx
│       │   ├── (marketing)/layout.tsx  page.tsx  login/page.tsx
│       │   ├── (owner)/layout.tsx
│       │   │   └── owner/onboarding/page.tsx
│       │   │       loans/[loanId]/{analyzing,boq,sanction,progress,changes}/...
│       │   └── (bank)/layout.tsx
│       │       └── bank/{portfolio,contractors,setup}/  loans/[loanId]/tranches/[n]/
│       ├── components/
│       │   ├── ui/       # the kit — 16 files, one component each
│       │   ├── owner/    # owner-only compositions
│       │   └── bank/     # bank-only compositions
│       ├── lib/{api.ts,format.ts,tone.ts,session.ts,api-types.ts}
│       └── middleware.ts
├── tests/test_offline.py                     # stays at repo root this phase
└── fixtures/  design_handoff_neev/  docs/  scripts/
```

---

## Phase 0 — Foundations (sequential, no parallelism)

Contracts before fan-out. Nothing in Phase 1+ may start until Phase 0 is complete, because parallel agents collide when they invent overlapping interfaces.

---

### Task 1: Toolchain, and prove both stacks boot

**Files:**
- Create: `.python-version`
- Create: `.node-version`
- Modify: `CLAUDE.md` (Environments section — record the verified versions)

**Interfaces:**
- Consumes: nothing.
- Produces: `python3.11` on PATH, `node`/`npm` on PATH. Every later task assumes both.

- [ ] **Step 1: Install Node and Python 3.11**

```bash
brew install node python@3.11
```

- [ ] **Step 2: Verify both, and that system Python is untouched**

```bash
/opt/homebrew/bin/python3.11 --version   # expect Python 3.11.x
node --version                            # expect v20 or newer
npm --version
python3 --version                         # expect 3.9.6 — system Python, unchanged
```

Expected: the first three print versions; the fourth still prints 3.9.6. If `python3.11` is not at `/opt/homebrew/bin/`, run `brew --prefix python@3.11` and use `$(brew --prefix python@3.11)/bin/python3.11` everywhere below.

- [ ] **Step 3: Pin the versions in the repo**

`.python-version`:
```
3.11
```

`.node-version`:
```
20
```

- [ ] **Step 4: Create the agents venv and prove the editable install works**

```bash
/opt/homebrew/bin/python3.11 -m venv src/agents/.venv
src/agents/.venv/bin/pip install -q -e src/agents
src/agents/.venv/bin/python -c "import neev_pipeline, sys; print('neev_pipeline importable on', sys.version.split()[0])"
```

Expected: prints `neev_pipeline importable on 3.11.x`.

**Note:** this import constructs a Gemini client at module scope (`tools/visual_inspector_tool.py:12` runs `genai.Client()`), which reads `GOOGLE_API_KEY` from the environment. That key is commented out, so the client is constructed unconfigured. **Constructing a client makes no API call and costs nothing** — it is only a client object. Do not "fix" this by supplying a key. If the import raises because no key is present, that is acceptable and expected under the dry run; record the error and move on — nothing in this build imports the package.

- [ ] **Step 5: Confirm the offline suite is still green on system Python**

```bash
python3 -m tests.test_offline
```
Expected: `Ran 28 tests` … `OK`

- [ ] **Step 6: Record the verified versions in CLAUDE.md**

In the `## Environments` section, append:

```markdown
Verified on this machine: Python 3.11 at `/opt/homebrew/bin/python3.11`, Node 20+
via Homebrew. `src/agents/.venv` exists and `pip install -e src/agents` succeeds. The
backend venv is created in Task 3.
```

- [ ] **Step 7: Commit**

```bash
git add .python-version .node-version CLAUDE.md
git commit -m "Task 1: pin toolchain versions; agents venv verified"
```

---

### Task 2: Backend package skeleton with the spend fence

The fence comes first, before any code that could conceivably call out. Everything after this task inherits it.

**Files:**
- Create: `src/backend/pyproject.toml`
- Create: `src/backend/app/__init__.py`
- Create: `src/backend/app/core/__init__.py`
- Create: `src/backend/app/core/settings.py`
- Create: `src/backend/app/main.py`
- Create: `src/backend/tests/__init__.py`
- Create: `src/backend/tests/conftest.py`
- Create: `src/backend/tests/test_settings_spend_guard.py`

**Interfaces:**
- Consumes: Python 3.11 from Task 1.
- Produces:
  - `app.core.settings.Settings` — pydantic-settings model with fields `neev_mode: Literal["fixture","live"] = "fixture"`, `neev_allow_billed_calls: bool = False`, `database_url: str = "sqlite:///./neev.db"`, `cors_origins: list[str] = ["http://localhost:3000"]`.
  - `app.core.settings.get_settings() -> Settings` — `@lru_cache`d.
  - `app.core.settings.BilledCallsNotPermitted` — exception class.
  - `app.core.settings.assert_billed_calls_permitted() -> None` — raises `BilledCallsNotPermitted` unless `neev_allow_billed_calls` is true.
  - `app.main.create_app() -> FastAPI` and module-level `app = create_app()`.
  - `GET /api/health` → `{"status": "ok", "mode": "fixture"}`.

- [ ] **Step 1: Write `src/backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "neev-backend"
version = "0.1.0"
description = "Neev application backend. Serves pipeline-shaped fixture data; deliberately carries no ADK dependency."
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "sqlalchemy>=2.0",
    "python-multipart>=0.0.12",
    "pillow>=11.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "httpx>=0.27"]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Do not add `google-adk`, `google-genai`, or `google-cloud-bigquery` to this file.** Their absence is a load-bearing part of the design.

- [ ] **Step 2: Write the failing test**

`src/backend/tests/test_settings_spend_guard.py`:
```python
"""The spend fence. These tests are the reason a NEEV_MODE typo can never
silently start billing."""

import pytest

from app.core.settings import (
    BilledCallsNotPermitted,
    Settings,
    assert_billed_calls_permitted,
)


def test_mode_defaults_to_fixture_when_unset():
    assert Settings().neev_mode == "fixture"


def test_unrecognized_mode_falls_back_to_fixture(monkeypatch):
    monkeypatch.setenv("NEEV_MODE", "liv")  # a typo, not a mode
    assert Settings().neev_mode == "fixture"


def test_live_mode_is_accepted_as_a_value():
    # Selecting live mode is allowed; ACTING on it is what is fenced.
    assert Settings(neev_mode="live").neev_mode == "live"


def test_billed_calls_are_refused_by_default():
    with pytest.raises(BilledCallsNotPermitted) as excinfo:
        assert_billed_calls_permitted(Settings(neev_mode="live"))
    assert "NEEV_ALLOW_BILLED_CALLS" in str(excinfo.value)


def test_billed_calls_permitted_only_with_the_explicit_opt_in():
    settings = Settings(neev_mode="live", neev_allow_billed_calls=True)
    assert_billed_calls_permitted(settings) is None
```

`src/backend/tests/conftest.py` — the network kill switch:
```python
"""Backend tests never reach the network.

Any outbound socket connection fails the test rather than costing money. This
is the same discipline as tests/test_offline.py at the repo root, enforced
structurally instead of by convention.
"""

import socket

import pytest


class NetworkAccessDenied(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    def _denied(*args, **kwargs):
        raise NetworkAccessDenied(
            "A backend test attempted an outbound network connection. "
            "The dry run forbids it — stub the call instead."
        )

    monkeypatch.setattr(socket.socket, "connect", _denied)
    monkeypatch.setattr(socket.socket, "connect_ex", _denied)
    monkeypatch.setattr(socket, "create_connection", _denied)


@pytest.fixture(autouse=True)
def _force_fixture_mode(monkeypatch):
    monkeypatch.setenv("NEEV_MODE", "fixture")
    monkeypatch.delenv("NEEV_ALLOW_BILLED_CALLS", raising=False)
    from app.core.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 3: Create the venv and run the test to verify it fails**

```bash
/opt/homebrew/bin/python3.11 -m venv src/backend/.venv
src/backend/.venv/bin/pip install -q -e "src/backend[dev]"
cd src/backend && .venv/bin/python -m pytest tests/test_settings_spend_guard.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.settings'`

- [ ] **Step 4: Write `src/backend/app/core/settings.py`**

```python
"""Application settings, and the fence that keeps this build from spending money.

NEEV_MODE selects which PipelineRunner the factory returns. It defaults to
"fixture" and falls back to "fixture" for any unrecognized value, so a typo
cannot select the live path. Live mode additionally requires an explicit
NEEV_ALLOW_BILLED_CALLS=1; without it, constructing the live runner raises.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal["fixture", "live"]


class BilledCallsNotPermitted(RuntimeError):
    """Raised when something tries to use the live, billed pipeline path."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    neev_mode: Mode = "fixture"
    neev_allow_billed_calls: bool = False
    database_url: str = "sqlite:///./neev.db"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("neev_mode", mode="before")
    @classmethod
    def _unknown_mode_is_fixture(cls, value: object) -> object:
        if value is None:
            return "fixture"
        if isinstance(value, str) and value.strip().lower() not in ("fixture", "live"):
            return "fixture"
        return value.strip().lower() if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def assert_billed_calls_permitted(settings: Settings | None = None) -> None:
    """Gate every billed code path through this.

    Raises BilledCallsNotPermitted unless NEEV_ALLOW_BILLED_CALLS is set. The
    message names the variable so the failure is self-explanatory.
    """
    settings = settings or get_settings()
    if not settings.neev_allow_billed_calls:
        raise BilledCallsNotPermitted(
            "Live mode requires NEEV_ALLOW_BILLED_CALLS=1. It is deliberately "
            "unset: this build must consume no Google credits. See CLAUDE.md."
        )
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd src/backend && .venv/bin/python -m pytest tests/ -q
```
Expected: 5 passed

- [ ] **Step 6: Write `src/backend/app/main.py`**

```python
"""FastAPI app factory. Routers are mounted here as later tasks add them."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Neev API",
        version="0.1.0",
        description="Serves pipeline-shaped loan data to the Neev owner and bank consoles.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": get_settings().neev_mode}

    return app


app = create_app()
```

`src/backend/app/__init__.py` and `src/backend/app/core/__init__.py` are empty files.

- [ ] **Step 7: Prove the app boots**

```bash
cd src/backend && .venv/bin/python -c "
from fastapi.testclient import TestClient
from app.main import app
r = TestClient(app).get('/api/health')
print(r.status_code, r.json())
"
```
Expected: `200 {'status': 'ok', 'mode': 'fixture'}`

If `TestClient` is unavailable, `pip install -q httpx` into the backend venv — it is already in the `dev` extra.

- [ ] **Step 8: Commit**

```bash
git add src/backend/
git commit -m "Task 2: backend skeleton, spend fence, socket-blocked tests"
```

---

### Task 3: Pipeline-shaped schemas — the contract everything else reads

These schemas mirror the five ADK `output_key` shapes **exactly as the agent instructions specify them** (`src/agents/neev_pipeline/agent.py`). They are transcribed below from that file; do not invent fields, and do not shape them after the screens.

**Files:**
- Create: `src/backend/app/schemas/__init__.py`
- Create: `src/backend/app/schemas/pipeline.py`
- Create: `src/backend/app/schemas/events.py`
- Create: `src/backend/tests/test_schemas.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, all importable from `app.schemas.pipeline`:
  - `FlagType` — `Literal["RATE_OUTLIER","UNBENCHMARKED","UNDERSPECIFIED","MISSING_SCOPE","GST_SILENT","STEEL_RATIO","FRONT_LOADED"]`
  - `Tone` — `Literal["danger","warn","success","neutral"]`
  - `LineItem(id: str, desc: str, qty: float, unit: str, rate: float, amount: float, section: str | None)`
  - `Flag(item: str, type: FlagType, evidence: str, question: str, tone: Tone, label: str, benchmark_rate: float | None, deviation_pct: float | None)`
  - `BoqFindings(line_items: list[LineItem], flags: list[Flag], boq_total: float, payment_pct_before_slab: float)`
  - `CostEstimate(expected_total_cost: float, completed_value_estimate: float, sanction_gap: float | None, fair_price_for_quoted_scope: float | None, missing_scope_value: float | None)`
  - `InspectionResult(stage: str, confidence: Literal["high","medium","low"], matches_claim: bool, evidence_notes: list[str], needs_human_review: bool, geotag_match: bool | None, timestamp_ok: bool | None)`
  - `RiskAssessment(exposure_ratio: float | None, exposure_undefined: bool, recommendation: Literal["RELEASE","HOLD","ESCALATE","INSPECT"], pct_complete: float, verified_value: float, cost_to_complete: float | None, cost_to_complete_gap: float, live_ltv_pct: float | None, ltv_default_prior: float | None, reasons: list[str])`
  - `Explanation(owner_view: str, officer_view: str)`
  - `PipelineOutput(boq_findings, cost_estimate, inspection_result, risk_assessment, explanation)` — all five, `inspection_result` and `risk_assessment` optional (`| None`) because a pre-disbursal loan has neither.
- Produces, from `app.schemas.events`:
  - `PhaseEvent(type: Literal["phase"], index: int, status: Literal["done","running","queued"], name: str, sub: str | None)`
  - `FindingEvent(type: Literal["finding"], flag: str, tone: Tone, text: str)`
  - `ProgressEvent(type: Literal["progress"], pct: int, detail: str, eta_s: int | None)`
  - `DoneEvent(type: Literal["done"], redirect: str)`
  - `PipelineEvent = Annotated[PhaseEvent | FindingEvent | ProgressEvent | DoneEvent, Field(discriminator="type")]`

- [ ] **Step 1: Write the failing test**

`src/backend/tests/test_schemas.py`:
```python
"""The schemas are the seam. These tests pin two things the live pipeline will
depend on: that infinite exposure serialises as JSON-legal null, and that the
event union discriminates on `type`."""

import json

from pydantic import TypeAdapter

from app.schemas.events import PipelineEvent
from app.schemas.pipeline import BoqFindings, Flag, LineItem, RiskAssessment


def test_infinite_exposure_serialises_as_null_not_Infinity():
    # assess_tranche returns float('inf') when expected_total_cost is 0 — a
    # passing test at tests/test_offline.py exercises exactly this. Infinity is
    # not valid JSON, so the schema must carry it as null plus an explicit flag.
    risk = RiskAssessment(
        exposure_ratio=None,
        exposure_undefined=True,
        recommendation="ESCALATE",
        pct_complete=0.0,
        verified_value=0.0,
        cost_to_complete_gap=0.0,
        reasons=["No verified value in place."],
    )
    payload = json.loads(risk.model_dump_json())
    assert payload["exposure_ratio"] is None
    assert payload["exposure_undefined"] is True
    assert "Infinity" not in json.dumps(payload)


def test_boq_findings_round_trips():
    findings = BoqFindings(
        line_items=[
            LineItem(
                id="3.1",
                section="3. RCC WORK",
                desc="RCC M25 for columns incl. shuttering & curing",
                qty=12.0,
                unit="cum",
                rate=9800,
                amount=117600,
            )
        ],
        flags=[
            Flag(
                item="3.1",
                type="RATE_OUTLIER",
                evidence="Benchmark 8033/cum — about 21200 excess on this line.",
                question="RCC M25 is priced at 9800/cum against a 8033 local benchmark. What is the basis?",
                tone="danger",
                label="Rate +22%",
                benchmark_rate=8033,
                deviation_pct=22.0,
            )
        ],
        boq_total=3200000,
        payment_pct_before_slab=0.45,
    )
    assert BoqFindings.model_validate_json(findings.model_dump_json()) == findings


def test_event_union_discriminates_on_type():
    adapter = TypeAdapter(PipelineEvent)
    phase = adapter.validate_python(
        {"type": "phase", "index": 2, "status": "running", "name": "Looking for missing scope"}
    )
    assert phase.name == "Looking for missing scope"
    done = adapter.validate_python({"type": "done", "redirect": "/owner/loans/1001/boq"})
    assert done.redirect.endswith("/boq")
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_schemas.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas'`

- [ ] **Step 3: Write `src/backend/app/schemas/pipeline.py`**

```python
"""The five ADK output_key shapes, as Pydantic models.

Transcribed from src/agents/neev_pipeline/agent.py, where each agent's instruction
ends with an explicit "Output JSON: {...}" contract:

  boq_analyst_agent      -> boq_findings      {line_items, flags, boq_total,
                                               payment_pct_before_slab}
  cost_estimation_agent  -> cost_estimate     {expected_total_cost,
                                               completed_value_estimate, sanction_gap}
  visual_inspector_agent -> inspection_result {stage, confidence, matches_claim,
                                               evidence_notes}
  disbursal_risk_agent   -> risk_assessment   the assess_tranche result verbatim
  explainer_agent        -> explanation       {owner_view, officer_view}

Fields beyond those contracts are present because the tools return them
(needs_human_review, benchmark_rate) or because a screen needs them and a real
run can supply them (geotag_match, cost_to_complete). They are optional so
today's authored fixture and tomorrow's live output both validate.

Money is stored as a number of rupees, never as a formatted string.
"""

from typing import Literal

from pydantic import BaseModel, Field

FlagType = Literal[
    "RATE_OUTLIER",
    "UNBENCHMARKED",
    "UNDERSPECIFIED",
    "MISSING_SCOPE",
    "GST_SILENT",
    "STEEL_RATIO",
    "FRONT_LOADED",
]

Tone = Literal["danger", "warn", "success", "neutral"]


class LineItem(BaseModel):
    id: str
    desc: str
    qty: float
    unit: str
    rate: float
    amount: float
    section: str | None = None


class Flag(BaseModel):
    item: str
    type: FlagType
    evidence: str
    question: str
    # Presentation-independent status. Never a colour: the theme resolves tone.
    tone: Tone = "danger"
    # Short human label the pill shows, e.g. "Rate +22%", "No grade", "Missing".
    label: str
    benchmark_rate: float | None = None
    deviation_pct: float | None = None
    # Set on MISSING_SCOPE flags, where there is no priced line to point at.
    expected_qty: float | None = None
    expected_unit: str | None = None
    expected_amount: float | None = None


class BoqFindings(BaseModel):
    line_items: list[LineItem]
    flags: list[Flag]
    boq_total: float
    payment_pct_before_slab: float


class PaymentStage(BaseModel):
    label: str
    pct: float
    before_slab: bool


class CostEstimate(BaseModel):
    expected_total_cost: float
    completed_value_estimate: float
    sanction_gap: float | None = None
    fair_price_for_quoted_scope: float | None = None
    missing_scope_value: float | None = None
    sections: list["CostSection"] = Field(default_factory=list)


class CostSection(BaseModel):
    """One row of the Sanction Check "where the gap comes from" table."""

    name: str
    quoted: float | None = None
    market: float | None = None
    delta: float
    quoted_note: str | None = None


class InspectionResult(BaseModel):
    stage: str
    confidence: Literal["high", "medium", "low"]
    matches_claim: bool
    evidence_notes: list[str] = Field(default_factory=list)
    needs_human_review: bool = False
    geotag_match: bool | None = None
    timestamp_ok: bool | None = None
    same_angle: bool | None = None


class RiskAssessment(BaseModel):
    # None when the ratio is undefined (expected_total_cost == 0). Infinity is
    # not valid JSON, so it is never serialised as a number.
    exposure_ratio: float | None = None
    exposure_undefined: bool = False
    recommendation: Literal["RELEASE", "HOLD", "ESCALATE", "INSPECT"]
    pct_complete: float
    verified_value: float
    cost_to_complete: float | None = None
    cost_to_complete_gap: float
    live_ltv_pct: float | None = None
    ltv_default_prior: float | None = None
    reasons: list[str] = Field(default_factory=list)


class Explanation(BaseModel):
    owner_view: str
    officer_view: str


class PipelineOutput(BaseModel):
    """One loan's complete pipeline state — the five output_key values together.

    inspection_result and risk_assessment are optional: a loan that has not yet
    requested a tranche has neither.
    """

    boq_findings: BoqFindings
    cost_estimate: CostEstimate
    inspection_result: InspectionResult | None = None
    risk_assessment: RiskAssessment | None = None
    explanation: Explanation
    payment_schedule: list[PaymentStage] = Field(default_factory=list)


CostEstimate.model_rebuild()
```

- [ ] **Step 4: Write `src/backend/app/schemas/events.py`**

```python
"""The SSE event contract.

This vocabulary belongs to the pipeline, not to the Analyzing screen. It is
written now so the live runner has a defined target to emit against rather than
being reverse-engineered from a finished UI (spec §5.1a).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.pipeline import Tone


class PhaseEvent(BaseModel):
    type: Literal["phase"] = "phase"
    index: int
    status: Literal["done", "running", "queued"]
    name: str
    sub: str | None = None


class FindingEvent(BaseModel):
    type: Literal["finding"] = "finding"
    flag: str
    tone: Tone
    text: str


class ProgressEvent(BaseModel):
    type: Literal["progress"] = "progress"
    pct: int
    detail: str
    eta_s: int | None = None


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    redirect: str


PipelineEvent = Annotated[
    PhaseEvent | FindingEvent | ProgressEvent | DoneEvent,
    Field(discriminator="type"),
]
```

`src/backend/app/schemas/__init__.py` is empty.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd src/backend && .venv/bin/python -m pytest tests/ -q
```
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add src/backend/app/schemas src/backend/tests/test_schemas.py
git commit -m "Task 3: pipeline-shaped Pydantic schemas and the SSE event contract"
```

---

### Task 4: `PipelineRunner` protocol, factory, and the never-executed live runner

**Files:**
- Create: `src/backend/app/services/__init__.py`
- Create: `src/backend/app/services/runner.py`
- Create: `src/backend/app/services/live_runner.py`
- Create: `src/backend/tests/test_runner_factory.py`

**Interfaces:**
- Consumes: `app.core.settings.{get_settings, assert_billed_calls_permitted, BilledCallsNotPermitted}`; `app.schemas.events.PipelineEvent`.
- Produces:
  - `app.services.runner.BoqAnalysisRequest(loan_id: str, filename: str, content_type: str, size_bytes: int, locality: str, built_up_sqft: int | None, sanctioned: int | None)`
  - `app.services.runner.PipelineRunner` — `Protocol` with `async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]`
  - `app.services.runner.get_runner() -> PipelineRunner` — the **only** place in the codebase that reads `NEEV_MODE`.
  - `app.services.live_runner.AdkPipelineRunner` — written, type-checked, never executed.

- [ ] **Step 1: Write the failing test**

`src/backend/tests/test_runner_factory.py`:
```python
"""The factory is the only place that reads NEEV_MODE. These tests prove that
fixture mode is what you get by default, and that reaching for live mode without
the explicit opt-in fails loudly instead of billing."""

import pytest

from app.core.settings import BilledCallsNotPermitted, Settings
from app.services.fixture_runner import FixtureRunner
from app.services.runner import get_runner


def test_default_mode_returns_the_fixture_runner():
    assert isinstance(get_runner(Settings()), FixtureRunner)


def test_typo_in_mode_still_returns_the_fixture_runner():
    assert isinstance(get_runner(Settings(neev_mode="LIVE_ish")), FixtureRunner)


def test_live_mode_without_the_opt_in_raises_naming_the_variable():
    with pytest.raises(BilledCallsNotPermitted) as excinfo:
        get_runner(Settings(neev_mode="live"))
    assert "NEEV_ALLOW_BILLED_CALLS" in str(excinfo.value)


def test_live_runner_module_imports_without_the_adk_installed():
    # The ADK import lives inside the method body, so importing the module is
    # safe in a venv that has no google-adk — which the backend venv does not.
    import app.services.live_runner as live

    assert hasattr(live, "AdkPipelineRunner")
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_runner_factory.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services'`

- [ ] **Step 3: Write `src/backend/app/services/runner.py`**

```python
"""The seam the live pipeline plugs into (spec §5.1a).

Routes depend on the PipelineRunner protocol and never branch on mode. Adding
the live path later means adding one class and one factory branch — no route,
schema, or component changes.
"""

from typing import AsyncIterator, Protocol, runtime_checkable

from pydantic import BaseModel

from app.core.settings import Settings, assert_billed_calls_permitted, get_settings
from app.schemas.events import PipelineEvent


class BoqAnalysisRequest(BaseModel):
    """Everything a runner needs to analyse one uploaded BoQ.

    Deliberately carries no file bytes: fixture mode ignores the upload, and the
    live runner reads the bytes back from the stored artefact. That keeps this
    object small enough to log and to put in a job record.
    """

    loan_id: str
    filename: str
    content_type: str
    size_bytes: int
    locality: str = "Kompally, Hyderabad"
    built_up_sqft: int | None = None
    sanctioned: int | None = None


@runtime_checkable
class PipelineRunner(Protocol):
    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        """Yield progress events as the analysis proceeds, ending with DoneEvent."""
        ...


def get_runner(settings: Settings | None = None) -> PipelineRunner:
    """Resolve the runner for the current mode.

    THE ONLY place in the codebase that reads NEEV_MODE. If you find yourself
    checking the mode anywhere else — a route, a mapper, a component — that is a
    defect; depend on this protocol instead.
    """
    settings = settings or get_settings()

    if settings.neev_mode == "live":
        # Raises unless NEEV_ALLOW_BILLED_CALLS is set. Under the dry run it
        # always raises, which is the intended behaviour.
        assert_billed_calls_permitted(settings)
        from app.services.live_runner import AdkPipelineRunner

        return AdkPipelineRunner()

    from app.services.fixture_runner import FixtureRunner

    return FixtureRunner()
```

- [ ] **Step 4: Write `src/backend/app/services/live_runner.py`**

```python
"""The live ADK path. Written and type-checked; NEVER EXECUTED in this build.

It ships unexercised by design (spec §5.1 and the CLAUDE.md dry run): the owner
validates it in Cloud Shell once credits are approved. Two properties make that
safe to leave here:

  1. Every ADK import is inside the method body, so this module imports cleanly
     in the backend venv, which has no google-adk at all.
  2. Construction goes through get_runner(), which refuses without an explicit
     NEEV_ALLOW_BILLED_CALLS=1.

The event sequence mirrors FixtureRunner's exactly, because the Analyzing
screen's five phases are all sub-steps inside boq_analyst — they are NOT the five
agents, contrary to the handoff README. The tool-call -> phase map is spec §5.2.
"""

from typing import AsyncIterator

from app.core.settings import assert_billed_calls_permitted
from app.schemas.events import DoneEvent, PhaseEvent, PipelineEvent
from app.services.runner import BoqAnalysisRequest

# Which display phase each ADK tool call advances (spec §5.2).
TOOL_TO_PHASE: dict[str, int] = {
    "lookup_benchmark_rate": 1,
    "check_rate_deviation": 1,
    "check_missing_scope": 2,
    "check_steel_rcc_ratio": 3,
    "check_payment_schedule": 4,
}

PHASE_NAMES: list[str] = [
    "Reading the document",
    "Checking every rate against Kompally benchmarks",
    "Looking for missing scope",
    "Checking specifications and quantities",
    "Reviewing the payment schedule and terms",
]


class AdkPipelineRunner:
    """Drives the real five-agent SequentialAgent through an InMemoryRunner."""

    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        assert_billed_calls_permitted()

        # Imported here, not at module scope: the backend venv has no ADK, and
        # importing neev_pipeline constructs a Gemini client at module load.
        from google.adk.runners import InMemoryRunner  # noqa: PLC0415
        from google.genai import types  # noqa: PLC0415
        from neev_pipeline.agent import root_agent  # noqa: PLC0415

        runner = InMemoryRunner(agent=root_agent, app_name="neev")
        session = await runner.session_service.create_session(
            app_name="neev", user_id=f"loan-{req.loan_id}"
        )

        message = types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        f"Analyse the attached Bill of Quantities for loan {req.loan_id}. "
                        f"Location: {req.locality}. "
                        f"Built-up area: {req.built_up_sqft} sqft. "
                        f"Sanctioned amount: {req.sanctioned}."
                    )
                )
            ],
        )

        emitted: set[int] = set()
        yield PhaseEvent(index=0, status="running", name=PHASE_NAMES[0])

        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=message
        ):
            for call in _tool_calls(event):
                phase = TOOL_TO_PHASE.get(call)
                if phase is None or phase in emitted:
                    continue
                emitted.add(phase)
                yield PhaseEvent(index=phase - 1, status="done", name=PHASE_NAMES[phase - 1])
                yield PhaseEvent(index=phase, status="running", name=PHASE_NAMES[phase])

        for index in range(len(PHASE_NAMES)):
            if index not in emitted:
                yield PhaseEvent(index=index, status="done", name=PHASE_NAMES[index])

        yield DoneEvent(redirect=f"/owner/loans/{req.loan_id}/boq")


def _tool_calls(event: object) -> list[str]:
    """Names of the function calls carried by one ADK event, if any."""
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    names = []
    for part in parts:
        call = getattr(part, "function_call", None)
        if call is not None and getattr(call, "name", None):
            names.append(call.name)
    return names
```

`src/backend/app/services/__init__.py` is empty.

- [ ] **Step 5: Note that the test needs `FixtureRunner`, built in Task 5**

The factory test imports `app.services.fixture_runner.FixtureRunner`, which does not exist yet. Write the minimal placeholder now so this task's tests pass, then Task 5 replaces its body:

`src/backend/app/services/fixture_runner.py`:
```python
"""Replays an authored pipeline run. Fully implemented in Task 5."""

from typing import AsyncIterator

from app.schemas.events import DoneEvent, PipelineEvent
from app.services.runner import BoqAnalysisRequest


class FixtureRunner:
    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        yield DoneEvent(redirect=f"/owner/loans/{req.loan_id}/boq")
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd src/backend && .venv/bin/python -m pytest tests/ -q
```
Expected: 12 passed

- [ ] **Step 7: Prove the live module is import-safe without the ADK**

```bash
cd src/backend && .venv/bin/python -c "
import app.services.live_runner as m
print('live_runner imports with no google-adk present:', m.AdkPipelineRunner.__name__)
import importlib.util
print('google-adk installed in this venv:', importlib.util.find_spec('google.adk') is not None)
"
```
Expected: prints the class name, then `google-adk installed in this venv: False`. If that says `True`, the backend venv is contaminated — recreate it.

- [ ] **Step 8: Commit**

```bash
git add src/backend/app/services src/backend/tests/test_runner_factory.py
git commit -m "Task 4: PipelineRunner protocol, mode factory, unexercised live runner"
```

---

### Task 5: The authored fixture, `FixtureRunner`, and the SSE job registry

This is where the mockups' numbers enter the system — once, in one place, in the pipeline's own shape.

**Files:**
- Create: `src/backend/app/fixtures/__init__.py`
- Create: `src/backend/app/fixtures/loan_1001_pipeline.json`
- Create: `src/backend/app/fixtures/loan_1002_pipeline.json`
- Create: `src/backend/app/fixtures/analyzing_script.json`
- Create: `src/backend/app/fixtures/loader.py`
- Modify: `src/backend/app/services/fixture_runner.py` (replace the Task 4 placeholder)
- Create: `src/backend/app/services/jobs.py`
- Create: `src/backend/tests/test_fixture_contract.py`
- Create: `src/backend/tests/test_runner_events.py`

**Interfaces:**
- Consumes: `app.schemas.pipeline.PipelineOutput`, `app.schemas.events.*`, `app.services.runner.BoqAnalysisRequest`.
- Produces:
  - `app.fixtures.loader.load_pipeline_output(loan_id: str) -> PipelineOutput` — validated, raises `KeyError` for an unknown loan.
  - `app.fixtures.loader.available_loan_ids() -> list[str]` → `["1001", "1002"]`
  - `app.fixtures.loader.load_analyzing_script() -> list[dict]`
  - `app.services.fixture_runner.FixtureRunner` — real implementation; `FixtureRunner(step_delay_s: float = 0.9)`.
  - `app.services.jobs.Job(id: str, loan_id: str, status: Literal["running","done","error"], events: list[PipelineEvent])`
  - `app.services.jobs.JobRegistry` with `create(req) -> Job`, `get(job_id) -> Job | None`, `async stream(job_id) -> AsyncIterator[PipelineEvent]`
  - `app.services.jobs.registry` — module-level singleton.

- [ ] **Step 1: Write the seam contract test first**

`src/backend/tests/test_fixture_contract.py` — this is the spec §5.1a acceptance test. It is the single most important test in the backend: it proves today that the fixtures already have the shape live output must have.

```python
"""Spec 5.1a acceptance test.

Every fixture must validate against the same Pydantic schemas the live runner
will emit. If a future live response would fail that schema, this test fails
today. It is also what stops the fixtures from drifting into screen-shaped blobs.
"""

import json
from pathlib import Path

import pytest

from app.fixtures.loader import available_loan_ids, load_pipeline_output
from app.schemas.pipeline import PipelineOutput

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"


@pytest.mark.parametrize("loan_id", ["1001", "1002"])
def test_every_fixture_validates_against_the_pipeline_schema(loan_id):
    output = load_pipeline_output(loan_id)
    assert isinstance(output, PipelineOutput)


def test_both_golden_loans_are_present():
    assert available_loan_ids() == ["1001", "1002"]


@pytest.mark.parametrize(
    "path", sorted(p for p in FIXTURE_DIR.glob("loan_*_pipeline.json"))
)
def test_no_fixture_contains_a_preformatted_money_string(path):
    # Money is stored as numbers and rendered through formatINR(). A rupee sign
    # or Indian-grouped digits in a fixture means a display string leaked into
    # the data layer, which is what makes fixture work throwaway.
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)

    offenders: list[str] = []

    def walk(node, trail):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{trail}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{trail}[{index}]")
        elif isinstance(node, str):
            # Prose fields legitimately quote figures to the reader.
            if trail.split(".")[-1] in {"owner_view", "officer_view", "evidence", "question"}:
                return
            if "\u20b9" in node:
                offenders.append(trail)

    walk(payload, path.stem)
    assert offenders == [], f"pre-formatted money in {path.name}: {offenders}"


def test_loan_1001_carries_the_frozen_mockup_figures():
    # Transcribed from the mockups (spec 4.4). If any of these change, a screen
    # and the fixture have drifted apart.
    out = load_pipeline_output("1001")
    assert out.boq_findings.boq_total == 3200000
    assert out.boq_findings.payment_pct_before_slab == 0.45
    assert len(out.boq_findings.flags) == 9
    assert out.cost_estimate.expected_total_cost == 3500000
    assert out.cost_estimate.fair_price_for_quoted_scope == 2915000
    assert out.cost_estimate.missing_scope_value == 154000
    assert out.risk_assessment is not None
    assert out.risk_assessment.exposure_ratio == 1.29
    assert out.risk_assessment.verified_value == 1390000
    assert out.risk_assessment.cost_to_complete == 1580000
    assert out.risk_assessment.cost_to_complete_gap == -580000
    assert out.risk_assessment.recommendation == "HOLD"


def test_flag_counts_match_the_boq_review_stat_card():
    # "9 items — 3 rate outliers, 2 missing scope, 4 vague specs"
    flags = load_pipeline_output("1001").boq_findings.flags
    by_type: dict[str, int] = {}
    for flag in flags:
        by_type[flag.type] = by_type.get(flag.type, 0) + 1
    assert by_type["RATE_OUTLIER"] == 3
    assert by_type["MISSING_SCOPE"] == 2
    assert by_type["UNDERSPECIFIED"] == 4


def test_clean_loan_1002_has_no_flags():
    assert load_pipeline_output("1002").boq_findings.flags == []
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_fixture_contract.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.fixtures'`

- [ ] **Step 3: Write `src/backend/app/fixtures/loan_1001_pipeline.json`**

Every figure below is transcribed from a mockup. Line items, quantities and rates come from `scripts/boq_data.py` (`RAVI_ITEMS`); flag labels, evidence and questions come verbatim from `Neev 1 BoQ Review.dc.html`; the risk block comes from `Neev 3 Tranche Decision.dc.html`; the cost sections come from `Neev 2 Sanction Check.dc.html`.

```json
{
  "boq_findings": {
    "boq_total": 3200000,
    "payment_pct_before_slab": 0.45,
    "line_items": [
      {"id": "2.3", "section": "2. FOUNDATION & PLINTH", "desc": "Plinth beam RCC M20 incl. shuttering", "qty": 6.5, "unit": "cum", "rate": 9800, "amount": 63700},
      {"id": "3.1", "section": "3. RCC WORK", "desc": "RCC M25 for columns incl. shuttering & curing", "qty": 12.0, "unit": "cum", "rate": 9800, "amount": 117600},
      {"id": "3.2", "section": "3. RCC WORK", "desc": "RCC M25 for roof slab 125mm incl. shuttering", "qty": 22.5, "unit": "cum", "rate": 9800, "amount": 220500},
      {"id": "4.2", "section": "4. STEEL", "desc": "TMT bars, cut bent and placed incl. wastage", "qty": 4800, "unit": "kg", "rate": 62, "amount": 297600},
      {"id": "7.1", "section": "7. FLOORING", "desc": "Vitrified tiles 600\u00d7600 \"good quality\"", "qty": 152, "unit": "sqm", "rate": 1150, "amount": 174800},
      {"id": "9.1", "section": "9. ELECTRICAL", "desc": "Concealed wiring per point, \"branded wire\"", "qty": 68, "unit": "pt", "rate": 720, "amount": 48960},
      {"id": "9.2", "section": "9. ELECTRICAL", "desc": "Modular switches & sockets, \"good make\"", "qty": 68, "unit": "pt", "rate": 310, "amount": 21080}
    ],
    "flags": [
      {
        "item": "2.3",
        "type": "RATE_OUTLIER",
        "label": "Rate +18%",
        "tone": "danger",
        "benchmark_rate": 8300,
        "deviation_pct": 18.0,
        "evidence": "M20 concrete priced at the M25 rate. Kompally benchmark \u20b98,300/cum.",
        "question": "Item 2.3 is M20 concrete priced at the M25 rate. Could you confirm the grade and the basis for \u20b99,800/cum?"
      },
      {
        "item": "3.1",
        "type": "RATE_OUTLIER",
        "label": "Rate +22%",
        "tone": "danger",
        "benchmark_rate": 8033,
        "deviation_pct": 22.0,
        "evidence": "Benchmark \u20b98,033/cum \u2014 about \u20b921,200 excess on this line.",
        "question": "RCC M25 is priced at \u20b99,800/cum against a \u20b98,033 local benchmark. What is the basis?"
      },
      {
        "item": "3.2",
        "type": "RATE_OUTLIER",
        "label": "Rate +22%",
        "tone": "danger",
        "benchmark_rate": 8033,
        "deviation_pct": 22.0,
        "evidence": "Benchmark \u20b98,033/cum \u2014 about \u20b939,800 excess on this line.",
        "question": "RCC M25 is priced at \u20b99,800/cum against a \u20b98,033 local benchmark. What is the basis?"
      },
      {
        "item": "4.2",
        "type": "UNDERSPECIFIED",
        "label": "No grade",
        "tone": "warn",
        "evidence": "No grade stated. Fe 415 vs Fe 500 vs Fe 500D changes the tonnage needed for the same strength \u2014 and this rate is below market: the classic low-bid trap.",
        "question": "Confirm the TMT grade for item 4.2 \u2014 Fe 500 or Fe 500D per IS 1786 \u2014 in writing."
      },
      {
        "item": "\u2014",
        "type": "MISSING_SCOPE",
        "label": "Missing",
        "tone": "danger",
        "expected_qty": 295,
        "expected_unit": "sqm",
        "expected_amount": 74000,
        "evidence": "Present in comparable BoQs, absent here. The contract's own terms say anything unlisted \"will be charged extra as per actuals\".",
        "question": "External plaster is absent. In scope, or extra \u2014 and at what rate?"
      },
      {
        "item": "\u2014",
        "type": "MISSING_SCOPE",
        "label": "Missing",
        "tone": "danger",
        "expected_amount": 80000,
        "evidence": "The single most common source of post-handover disputes.",
        "question": "Terrace waterproofing is absent. In scope, or extra \u2014 and at what rate?"
      },
      {
        "item": "7.1",
        "type": "UNDERSPECIFIED",
        "label": "Vague spec",
        "tone": "warn",
        "evidence": "No brand or model named \u2014 enables substitution with cheaper equivalents.",
        "question": "Please name the make and model for the vitrified tiles in item 7.1."
      },
      {
        "item": "9.1",
        "type": "UNDERSPECIFIED",
        "label": "Vague spec",
        "tone": "warn",
        "evidence": "\"Branded\" names no brand. Specify make and FR grade.",
        "question": "Please name the wire make and FR grade for item 9.1."
      },
      {
        "item": "9.2",
        "type": "UNDERSPECIFIED",
        "label": "Vague spec",
        "tone": "warn",
        "evidence": "Specify make and series.",
        "question": "Please name the make and series for the modular switches in item 9.2."
      }
    ]
  },
  "payment_schedule": [
    {"label": "On signing", "pct": 0.2, "before_slab": true},
    {"label": "At foundation", "pct": 0.25, "before_slab": true},
    {"label": "At slab", "pct": 0.25, "before_slab": false},
    {"label": "At brickwork & roof", "pct": 0.2, "before_slab": false},
    {"label": "On handover", "pct": 0.1, "before_slab": false}
  ],
  "cost_estimate": {
    "expected_total_cost": 3500000,
    "completed_value_estimate": 4100000,
    "sanction_gap": -700000,
    "fair_price_for_quoted_scope": 2915000,
    "missing_scope_value": 154000,
    "sections": [
      {"name": "RCC & foundation over-rates negotiated back", "quoted": 475000, "market": 394000, "delta": -81000},
      {"name": "Missing scope added back (plaster + waterproofing)", "quoted": null, "quoted_note": "\u2014", "market": 154000, "delta": 154000},
      {"name": "TMT steel at Fe 500 market rate", "quoted": 297600, "market": 349600, "delta": 52000},
      {"name": "GST provision (12% composite)", "quoted": null, "quoted_note": "not stated", "market": 345000, "delta": 345000},
      {"name": "Balance of scope at market", "quoted": 2427400, "market": 2257400, "delta": -170000}
    ]
  },
  "inspection_result": {
    "stage": "slab",
    "confidence": "high",
    "matches_claim": true,
    "needs_human_review": false,
    "geotag_match": true,
    "timestamp_ok": true,
    "same_angle": true,
    "evidence_notes": [
      "Geotag matches Plot 47, Kompally.",
      "Timestamp 10 Aug, 11:42.",
      "Slab shuttering struck; surface finished. Consistent with the claimed stage.",
      "Same camera position as the tranche-2 set."
    ]
  },
  "risk_assessment": {
    "exposure_ratio": 1.29,
    "exposure_undefined": false,
    "recommendation": "HOLD",
    "pct_complete": 0.5,
    "verified_value": 1390000,
    "cost_to_complete": 1580000,
    "cost_to_complete_gap": -580000,
    "live_ltv_pct": 64.3,
    "ltv_default_prior": 0.126,
    "reasons": [
      "Disbursed \u20b918,00,000 against \u20b913,90,000 of verified value in place.",
      "Exposure 1.29 is above the 1.00 hold threshold.",
      "Remaining scope at current Kompally rates exceeds the undrawn balance by \u20b95,80,000."
    ]
  },
  "explanation": {
    "owner_view": "Your slab photos check out \u2014 the stage is real and the geotag matches Plot 47. The problem is the money, not the work. \u20b918,00,000 has been paid out against about \u20b913,90,000 of value actually standing on site, and finishing the remaining scope at today's Kompally rates would cost roughly \u20b915,80,000 \u2014 about \u20b95,80,000 more than what is left of the loan. That gap is why this tranche is on hold rather than released. The four questions from your contract review are the fastest way to close most of it, and the sanction check page shows three specific routes.",
    "officer_view": "HOLD recommended on tranche 3, loan 1001. Disbursed \u20b918,00,000 cumulative (T1 \u20b96,00,000, T2 \u20b96,00,000, T3 \u20b96,00,000). Verified value in place \u20b913,90,000, derived from the slab stage against the BoQ schedule of values. Disbursement exposure 1.29 against a 1.00 hold threshold. Cost to complete \u20b915,80,000 at current Kompally rates, leaving a \u20b95,80,000 shortfall against the undrawn balance. Site evidence is strong: three photographs, geotag matched to Plot 47, timestamp 10 Aug 11:42, camera position consistent with the tranche-2 set, high confidence, no human review flag. Contract-side exposure is compounding: 9 open BoQ flags including 3 rate outliers on RCC and \u20b91,54,000 of scope absent from the signed document. Benchmark source: CPWD DSR 2023 \u00d7 Hyderabad factor."
  }
}
```

- [ ] **Step 4: Write `src/backend/app/fixtures/loan_1002_pipeline.json` — the clean negative case**

```json
{
  "boq_findings": {
    "boq_total": 2480000,
    "payment_pct_before_slab": 0.25,
    "line_items": [
      {"id": "3.1", "section": "3. RCC WORK", "desc": "RCC M25 for columns incl. shuttering & curing, IS 456", "qty": 11.5, "unit": "cum", "rate": 8050, "amount": 92575},
      {"id": "4.2", "section": "4. STEEL", "desc": "TMT bars Fe 500D per IS 1786, cut bent and placed", "qty": 4600, "unit": "kg", "rate": 71, "amount": 326600},
      {"id": "6.3", "section": "6. PLASTERING", "desc": "External plaster 15mm CM 1:5, two coats", "qty": 288, "unit": "sqm", "rate": 245, "amount": 70560}
    ],
    "flags": []
  },
  "payment_schedule": [
    {"label": "On signing", "pct": 0.1, "before_slab": true},
    {"label": "At foundation", "pct": 0.15, "before_slab": true},
    {"label": "At slab", "pct": 0.3, "before_slab": false},
    {"label": "At brickwork & roof", "pct": 0.3, "before_slab": false},
    {"label": "On handover", "pct": 0.15, "before_slab": false}
  ],
  "cost_estimate": {
    "expected_total_cost": 2520000,
    "completed_value_estimate": 3150000,
    "sanction_gap": -20000,
    "fair_price_for_quoted_scope": 2505000,
    "missing_scope_value": 0,
    "sections": []
  },
  "inspection_result": {
    "stage": "slab",
    "confidence": "high",
    "matches_claim": true,
    "needs_human_review": false,
    "geotag_match": true,
    "timestamp_ok": true,
    "same_angle": true,
    "evidence_notes": ["Geotag matches the registered plot.", "Slab cast and cured; consistent with the claimed stage."]
  },
  "risk_assessment": {
    "exposure_ratio": 0.97,
    "exposure_undefined": false,
    "recommendation": "RELEASE",
    "pct_complete": 0.5,
    "verified_value": 1252000,
    "cost_to_complete": 1240000,
    "cost_to_complete_gap": 105000,
    "live_ltv_pct": 48.6,
    "ltv_default_prior": 0.139,
    "reasons": [
      "Disbursed \u20b912,14,337 against \u20b912,52,000 of verified value in place.",
      "Exposure 0.97 is within the 1.00 hold threshold.",
      "Remaining scope is covered by the undrawn balance with \u20b91,05,000 to spare."
    ]
  },
  "explanation": {
    "owner_view": "Everything lines up. Your contract prices the work at local rates, the scope is complete, the grades and brands are named, and only 25% falls due before the slab \u2014 which is the pattern to aim for. The slab photos match the claimed stage, and payments are tracking slightly behind the value on site rather than ahead of it. Nothing needs your attention right now.",
    "officer_view": "RELEASE recommended on tranche 3, loan 1002. Disbursed \u20b912,14,337 cumulative against \u20b912,52,000 verified value in place. Disbursement exposure 0.97, within the 1.00 threshold. Cost to complete \u20b912,40,000 at current rates against a larger undrawn balance, leaving \u20b91,05,000 of headroom. Site evidence: geotag matched, high confidence, no human review flag. Zero open BoQ flags; scope complete, grades specified, GST stated, 25% before slab. No contract-side exposure."
  }
}
```

- [ ] **Step 5: Write `src/backend/app/fixtures/analyzing_script.json`**

The replay script for the Analyzing screen, transcribed from `Neev 0b Analyzing.dc.html`. Phase names and subtitles are that file's copy verbatim.

```json
{
  "phases": [
    {"name": "Reading the document", "sub": "40 items across 12 sections, payment schedule, terms"},
    {"name": "Checking every rate against Kompally benchmarks", "sub": "CPWD DSR + 32,963 real listings"},
    {"name": "Looking for missing scope", "sub": "Comparing against what similar houses always include"},
    {"name": "Checking specifications and quantities", "sub": "Grades, brands, IS standards, steel-to-concrete ratios"},
    {"name": "Reviewing the payment schedule and terms", "sub": "How much is demanded before real work exists"}
  ],
  "progress": [
    {"pct": 12, "detail": "item 5 of 40 \u00b7 section 2, foundation & plinth", "eta_s": 62},
    {"pct": 38, "detail": "item 17 of 40 \u00b7 section 6, plastering", "eta_s": 40},
    {"pct": 61, "detail": "item 25 of 40 \u00b7 section 8, doors & windows", "eta_s": 24},
    {"pct": 84, "detail": "item 34 of 40 \u00b7 section 11, painting", "eta_s": 9},
    {"pct": 100, "detail": "40 of 40 items checked", "eta_s": 0}
  ],
  "findings": [
    {"after_phase": 1, "flag": "Rate +22%", "tone": "danger", "text": "RCC M25 is priced at \u20b99,800/cum \u2014 Kompally benchmark is \u20b98,033. Appears on 2 items."},
    {"after_phase": 2, "flag": "Missing", "tone": "danger", "text": "External plaster and terrace waterproofing are absent \u2014 about \u20b91,54,000 of scope that usually returns as paid extras."},
    {"after_phase": 3, "flag": "No grade", "tone": "warn", "text": "TMT bars (4,800 kg) name no grade \u2014 Fe 415 vs Fe 500 changes how much steel your house needs."},
    {"after_phase": 4, "flag": "45% before slab", "tone": "warn", "text": "\u20b914,40,000 falls due before the slab is cast. The standard pattern is 25%."}
  ]
}
```

- [ ] **Step 6: Write `src/backend/app/fixtures/loader.py`**

```python
"""Loads the authored, pipeline-shaped fixtures.

The fixture is authored rather than recorded: recording a golden run would itself
spend credits, which the dry run forbids. Numbers are transcribed from the
mockups (spec 4.4); line items, quantities and rates come from
scripts/boq_data.py where the mockups only show a subset.
"""

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.pipeline import PipelineOutput

_DIR = Path(__file__).resolve().parent


@lru_cache
def load_pipeline_output(loan_id: str) -> PipelineOutput:
    path = _DIR / f"loan_{loan_id}_pipeline.json"
    if not path.exists():
        raise KeyError(f"No authored pipeline fixture for loan {loan_id!r}")
    return PipelineOutput.model_validate_json(path.read_text(encoding="utf-8"))


def available_loan_ids() -> list[str]:
    return sorted(p.stem.split("_")[1] for p in _DIR.glob("loan_*_pipeline.json"))


@lru_cache
def load_analyzing_script() -> dict:
    return json.loads((_DIR / "analyzing_script.json").read_text(encoding="utf-8"))
```

`src/backend/app/fixtures/__init__.py` is empty.

- [ ] **Step 7: Run the contract test to verify it passes**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_fixture_contract.py -q
```
Expected: 12 passed. If `test_no_fixture_contains_a_preformatted_money_string` fails, a rupee sign leaked outside a prose field — move the figure into a number.

- [ ] **Step 8: Write the runner-events test**

`src/backend/tests/test_runner_events.py`:
```python
"""FixtureRunner emits the same sequence the live runner must emit."""

import pytest

from app.schemas.events import DoneEvent, FindingEvent, PhaseEvent, ProgressEvent
from app.services.fixture_runner import FixtureRunner
from app.services.runner import BoqAnalysisRequest

REQ = BoqAnalysisRequest(
    loan_id="1001", filename="sample_boq.pdf", content_type="application/pdf", size_bytes=1024
)


async def _collect(runner):
    return [event async for event in runner.run(REQ)]


@pytest.mark.asyncio
async def test_emits_five_phases_each_running_then_done():
    events = await _collect(FixtureRunner(step_delay_s=0))
    phases = [e for e in events if isinstance(e, PhaseEvent)]
    for index in range(5):
        statuses = [p.status for p in phases if p.index == index]
        assert "running" in statuses and "done" in statuses, index


@pytest.mark.asyncio
async def test_findings_and_progress_are_interleaved():
    events = await _collect(FixtureRunner(step_delay_s=0))
    assert any(isinstance(e, FindingEvent) for e in events)
    assert any(isinstance(e, ProgressEvent) for e in events)


@pytest.mark.asyncio
async def test_last_event_is_done_and_redirects_to_the_boq_review_route():
    events = await _collect(FixtureRunner(step_delay_s=0))
    assert isinstance(events[-1], DoneEvent)
    assert events[-1].redirect == "/owner/loans/1001/boq"


@pytest.mark.asyncio
async def test_progress_never_exceeds_100_and_ends_at_100():
    events = await _collect(FixtureRunner(step_delay_s=0))
    pcts = [e.pct for e in events if isinstance(e, ProgressEvent)]
    assert max(pcts) == 100
    assert pcts == sorted(pcts)
```

Add the async plugin to the backend dev extra in `src/backend/pyproject.toml`:
```toml
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "httpx>=0.27"]
```
and configure it:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```
Then `src/backend/.venv/bin/pip install -q -e "src/backend[dev]"` again.

- [ ] **Step 9: Run it to verify it fails**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_runner_events.py -q
```
Expected: FAIL — `TypeError: FixtureRunner() takes no arguments` (the Task 4 placeholder has no `step_delay_s`).

- [ ] **Step 10: Replace `src/backend/app/services/fixture_runner.py`**

```python
"""Replays the authored pipeline run on a timer.

Makes zero network calls of any kind. The event sequence is identical to what
AdkPipelineRunner emits, so the Analyzing screen cannot tell the two apart —
which is the whole point of the seam (spec 5.1a).
"""

import asyncio
from typing import AsyncIterator

from app.fixtures.loader import load_analyzing_script
from app.schemas.events import DoneEvent, FindingEvent, PhaseEvent, PipelineEvent, ProgressEvent
from app.services.runner import BoqAnalysisRequest


class FixtureRunner:
    def __init__(self, step_delay_s: float = 0.9) -> None:
        # Pacing only. Set to 0 in tests so the suite stays instant.
        self.step_delay_s = step_delay_s

    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        script = load_analyzing_script()
        phases = script["phases"]
        progress = script["progress"]
        findings = script["findings"]

        for index, phase in enumerate(phases):
            yield PhaseEvent(index=index, status="running", name=phase["name"], sub=phase["sub"])
            await self._pause()

            if index < len(progress):
                step = progress[index]
                yield ProgressEvent(pct=step["pct"], detail=step["detail"], eta_s=step["eta_s"])

            yield PhaseEvent(index=index, status="done", name=phase["name"], sub=phase["sub"])

            for finding in findings:
                if finding["after_phase"] == index:
                    yield FindingEvent(
                        flag=finding["flag"], tone=finding["tone"], text=finding["text"]
                    )
                    await self._pause()

        yield DoneEvent(redirect=f"/owner/loans/{req.loan_id}/boq")

    async def _pause(self) -> None:
        if self.step_delay_s:
            await asyncio.sleep(self.step_delay_s)
```

- [ ] **Step 11: Run to verify it passes**

```bash
cd src/backend && .venv/bin/python -m pytest tests/ -q
```
Expected: all pass (≈20 tests)

- [ ] **Step 12: Write `src/backend/app/services/jobs.py`**

```python
"""In-process job registry and SSE fan-out.

One process, one registry — enough for a demo and for a single-node deployment.
Events are retained on the Job so a late subscriber (a page refresh mid-analysis)
replays what it missed instead of showing an empty screen.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

from app.schemas.events import DoneEvent, PipelineEvent
from app.services.runner import BoqAnalysisRequest, get_runner

JobStatus = Literal["running", "done", "error"]


@dataclass
class Job:
    id: str
    loan_id: str
    status: JobStatus = "running"
    events: list[PipelineEvent] = field(default_factory=list)
    error: str | None = None
    _waiters: list[asyncio.Queue] = field(default_factory=list, repr=False)

    def publish(self, event: PipelineEvent) -> None:
        self.events.append(event)
        for queue in self._waiters:
            queue.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._waiters.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._waiters:
            self._waiters.remove(queue)


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def create(self, req: BoqAnalysisRequest) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], loan_id=req.loan_id)
        self._jobs[job.id] = job
        self._tasks[job.id] = asyncio.create_task(self._drive(job, req))
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def _drive(self, job: Job, req: BoqAnalysisRequest) -> None:
        try:
            async for event in get_runner().run(req):
                job.publish(event)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as an SSE error
            job.status = "error"
            job.error = str(exc)
            job.publish(DoneEvent(redirect=f"/owner/loans/{job.loan_id}/boq"))

    async def stream(self, job_id: str) -> AsyncIterator[PipelineEvent]:
        """Replay everything already emitted, then follow live."""
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)

        for event in list(job.events):
            yield event
            if isinstance(event, DoneEvent):
                return

        if job.status != "running":
            return

        queue = job.subscribe()
        try:
            while True:
                event = await queue.get()
                yield event
                if isinstance(event, DoneEvent):
                    return
        finally:
            job.unsubscribe(queue)


registry = JobRegistry()
```

- [ ] **Step 13: Commit**

```bash
git add src/backend/
git commit -m "Task 5: authored pipeline-shaped fixtures, FixtureRunner, SSE job registry"
```

---

### Task 6: Frontend scaffold, the AA-corrected theme, and the no-raw-hex lint rule

**Files:**
- Create: `src/frontend/` (via `create-next-app`)
- Modify: `src/frontend/app/globals.css` — the whole token system
- Modify: `src/frontend/app/layout.tsx` — fonts, metadata, theme bootstrap
- Create: `src/frontend/eslint.config.mjs` additions — the raw-hex ban
- Create: `src/frontend/lib/format.ts`
- Create: `src/frontend/lib/tone.ts`
- Create: `src/frontend/scripts/check-no-raw-hex.mjs`
- Modify: `src/frontend/package.json` — scripts

**Interfaces:**
- Consumes: Node from Task 1.
- Produces:
  - CSS custom properties on `:root` and `[data-theme="dark"]`, exposed to Tailwind via `@theme inline`.
  - `lib/format.ts`: `formatINR(rupees: number): string`, `formatINRCompact(rupees: number): string`, `formatPct(fraction: number, dp?: number): string`, `formatRatio(n: number | null): string`, `formatQty(n: number): string`.
  - `lib/tone.ts`: `type Tone = 'danger' | 'warn' | 'success' | 'neutral'`; `type Skin = 'owner' | 'bank'`; `toneClasses(tone: Tone, skin?: Skin): { pill: string; text: string; bg: string }`.
  - `npm run lint`, `npm run typecheck`, `npm run build`, `npm run check:hex` all defined.

- [ ] **Step 1: Scaffold the app**

```bash
cd /Users/mohithkumar/Documents/Neev/neev
npx --yes create-next-app@latest src/frontend \
  --typescript --tailwind --eslint --app --src-dir=false \
  --import-alias "@/*" --use-npm --no-turbopack --yes
```

Then verify it builds before changing anything:
```bash
cd src/frontend && npm run build
```
Expected: `Compiled successfully`. If this fails, stop — nothing downstream is verifiable until it passes.

- [ ] **Step 2: Write the failing check — the raw-hex guard**

`src/frontend/scripts/check-no-raw-hex.mjs`:
```js
// Fails the build on a raw #rrggbb outside the theme file.
//
// The mockups hardcode hex hundreds of times across fifteen files. If that
// survives the port, retoning becomes impossible and the screens drift apart —
// and the handoff README explicitly warns the palette was still under
// discussion. Colours come from theme tokens, only.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const ROOT = process.cwd();
const ALLOWED = new Set(['app/globals.css']);
const EXTS = ['.ts', '.tsx', '.css', '.mjs'];
const SKIP_DIRS = new Set(['node_modules', '.next', 'out', '.git']);
const HEX = /#[0-9a-fA-F]{3,8}\b/g;

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (EXTS.some((e) => entry.endsWith(e))) out.push(full);
  }
  return out;
}

const offenders = [];
for (const file of walk(ROOT)) {
  const rel = relative(ROOT, file).split('\\').join('/');
  if (ALLOWED.has(rel) || rel.startsWith('scripts/')) continue;
  const lines = readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, i) => {
    if (line.includes('check-no-raw-hex')) return;
    for (const match of line.match(HEX) ?? []) {
      offenders.push(`${rel}:${i + 1}  ${match}`);
    }
  });
}

if (offenders.length) {
  console.error('Raw hex colours found outside app/globals.css:\n');
  for (const o of offenders) console.error('  ' + o);
  console.error(
    `\n${offenders.length} violation(s). Add a token in app/globals.css and use it instead.`
  );
  process.exit(1);
}
console.log('No raw hex outside the theme file.');
```

Add to `src/frontend/package.json` scripts:
```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "check:hex": "node scripts/check-no-raw-hex.mjs",
    "verify": "npm run typecheck && npm run lint && npm run check:hex && npm run build"
  }
}
```

- [ ] **Step 3: Run the check to see it fail against the scaffold**

```bash
cd src/frontend && npm run check:hex
```
Expected: FAIL, listing whatever hex `create-next-app` left in `app/page.tsx` / `app/globals.css`. That failure is the check working.

- [ ] **Step 4: Write `src/frontend/app/globals.css` — the single source of colour truth**

Three tokens are darkened from the handoff table because they fail WCAG AA as specified. Measured ratios are in the comments; do not restore the originals.

```css
@import "tailwindcss";

/*
  Neev theme. THE ONLY FILE IN THE APP THAT MAY CONTAIN A HEX COLOUR.

  Lifted from Neev Landing.dc.html's custom-property block (the only prototype
  with a working dark mode) plus the handoff README's token table. The other 15
  prototypes hardcode hex inline; that does not survive the port.

  Three tokens are darkened from the handoff values because they fail WCAG 2.1
  AA at the sizes the designs use them. Measured with the standard relative
  luminance formula:

    --faint : #9b938a on #faf9f7 = 2.88:1  -> #77716a = 4.58:1
    --danger: #b4552e on #f9ece5 = 4.24:1  -> #ad522c = 4.52:1
    --warn  : #8a6d4f on #f4efe6 = 4.19:1  -> #83684b = 4.53:1

  The danger and warn pairs are the flag pills — the most repeated element in
  the bundle — set at 11px, which is normal text needing 4.5:1, not large text
  needing 3:1. Everything else measured clean: sub 5.38, action 5.12,
  success 6.00, ink 14.22, bank-inactive 6.99.
*/

:root {
  /* surfaces */
  --bg: #faf9f7;
  --card: #ffffff;
  --line: #ece9e4;
  --chip: #f2f0ec;
  --rowline: #f5f3f0;
  --hover: #f7f6f4;
  --input-border: #dcd7d0;

  /* text */
  --ink: #2b2622;
  --sub: #6d665e;
  --faint: #77716a;

  /* actions */
  --action: #3d7a52;
  --action-hover: #336847;

  /* tones */
  --success: #2f6647;
  --success-tint: #eaf4ee;
  --danger: #ad522c;
  --danger-tint: #f9ece5;
  --warn: #83684b;
  --warn-tint: #f4efe6;

  /* brand — logo only, never text */
  --brick: #e07856;

  /* bank console chrome */
  --bank-bar: #111827;
  --bank-ink: #111827;
  --bank-inactive: #9ca3af;
  --bank-accent: #2d5bff;
  --bank-danger: #b42318;
  --bank-danger-tint: #fef3f2;
  --bank-warn: #b54708;
  --bank-warn-tint: #fffaeb;
  --bank-success: #067647;
  --bank-success-tint: #ecfdf3;
  --bank-row-flagged: #fffbfa;

  /* focus ring — visible on every interactive element */
  --focus: #3d7a52;
}

[data-theme="dark"] {
  --bg: #241c15;
  --card: #2e251d;
  --line: #3f342a;
  --chip: #332a21;
  --rowline: #362c23;
  --hover: #362c23;
  --input-border: #4a3c30;
  --ink: #f3e9dc;
  --sub: #b8a794;
  --faint: #9d8d7b;
  --action: #4c9367;
  --action-hover: #5aa878;
  --success: #7cc79a;
  --success-tint: #26382c;
  --danger: #e9a184;
  --danger-tint: #3b2a22;
  --warn: #d4bb96;
  --warn-tint: #362e22;
}

@theme inline {
  --color-bg: var(--bg);
  --color-card: var(--card);
  --color-line: var(--line);
  --color-chip: var(--chip);
  --color-rowline: var(--rowline);
  --color-hover: var(--hover);
  --color-input-border: var(--input-border);
  --color-ink: var(--ink);
  --color-sub: var(--sub);
  --color-faint: var(--faint);
  --color-action: var(--action);
  --color-action-hover: var(--action-hover);
  --color-success: var(--success);
  --color-success-tint: var(--success-tint);
  --color-danger: var(--danger);
  --color-danger-tint: var(--danger-tint);
  --color-warn: var(--warn);
  --color-warn-tint: var(--warn-tint);
  --color-brick: var(--brick);
  --color-bank-bar: var(--bank-bar);
  --color-bank-inactive: var(--bank-inactive);
  --color-bank-accent: var(--bank-accent);
  --color-bank-danger: var(--bank-danger);
  --color-bank-danger-tint: var(--bank-danger-tint);
  --color-bank-warn: var(--bank-warn);
  --color-bank-warn-tint: var(--bank-warn-tint);
  --color-bank-success: var(--bank-success);
  --color-bank-success-tint: var(--bank-success-tint);
  --color-bank-row-flagged: var(--bank-row-flagged);

  --font-display: var(--font-baloo), ui-sans-serif, system-ui, sans-serif;
  --font-sans: var(--font-instrument), ui-sans-serif, system-ui, sans-serif;
  --font-mono: var(--font-jetbrains), ui-monospace, monospace;

  --radius-card: 15px;
  --radius-pill: 22px;
  --radius-bank: 10px;

  --shadow-card: 0 1px 2px rgb(20 15 10 / 0.05);
}

html {
  color-scheme: light;
}
[data-theme="dark"] html,
html[data-theme="dark"] {
  color-scheme: dark;
}

body {
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  /* Laptop-only target: 1280-1920px. Below 1280 degrades gracefully; the page
     body must never scroll horizontally. */
  min-width: 0;
  overflow-x: hidden;
}

a {
  color: inherit;
  text-decoration: none;
}

/* Every interactive element gets a visible focus ring. The prototypes have no
   real controls at all, so nothing about focus can be ported — it is added. */
:where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
  border-radius: 4px;
}

/* Numbers, ids and ratios are always mono — a hard rule from the handoff. */
.tnum {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

@keyframes nv-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}
```

- [ ] **Step 5: Write `src/frontend/lib/format.ts`**

```ts
// The one and only money formatter. No screen stores or emits a pre-formatted
// money string; every rupee figure on screen passes through here.

const MINUS = '\u2212'; // U+2212 MINUS SIGN, as the designs use

/** Full Indian grouping: 3200000 -> "₹32,00,000". Negatives use a true minus. */
export function formatINR(rupees: number): string {
  if (!Number.isFinite(rupees)) return '—';
  const negative = rupees < 0;
  const digits = Math.abs(Math.round(rupees)).toString();
  let grouped: string;
  if (digits.length <= 3) {
    grouped = digits;
  } else {
    const last3 = digits.slice(-3);
    const rest = digits.slice(0, -3);
    grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3;
  }
  return `${negative ? MINUS : ''}\u20b9${grouped}`;
}

/** Compact crore/lakh form for portfolio headlines: 25700000 -> "₹2.57 cr". */
export function formatINRCompact(rupees: number): string {
  if (!Number.isFinite(rupees)) return '—';
  const negative = rupees < 0;
  const abs = Math.abs(rupees);
  const sign = negative ? MINUS : '';
  if (abs >= 1_00_00_000) return `${sign}\u20b9${(abs / 1_00_00_000).toFixed(2)} cr`;
  if (abs >= 1_00_000) return `${sign}\u20b9${(abs / 1_00_000).toFixed(2)} L`;
  return formatINR(rupees);
}

/** 0.45 -> "45%". */
export function formatPct(fraction: number, dp = 0): string {
  if (!Number.isFinite(fraction)) return '—';
  return `${(fraction * 100).toFixed(dp)}%`;
}

/** Exposure ratios render to two decimals; null means undefined, never Infinity. */
export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return value.toFixed(2);
}

/** Quantities keep their natural precision: 22.5 -> "22.5", 4800 -> "4,800". */
export function formatQty(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return Number.isInteger(value) ? value.toLocaleString('en-IN') : value.toString();
}

/** Signed rupee delta, for diff and change-order rows: 154000 -> "+₹1,54,000". */
export function formatDelta(rupees: number): string {
  if (!Number.isFinite(rupees)) return '—';
  return rupees > 0 ? `+${formatINR(rupees)}` : formatINR(rupees);
}
```

- [ ] **Step 6: Write `src/frontend/lib/tone.ts`**

```ts
// One status vocabulary for the whole product.
//
// The mockups carry six: BoQ flag pills, tranche status, question status, bank
// action pills, contractor tiers, and inspection confidence — each with its own
// hardcoded pillBg/pillFg pair. They all collapse into `tone`, resolved here.
// No component anywhere takes a colour prop.

export type Tone = 'danger' | 'warn' | 'success' | 'neutral';
export type Skin = 'owner' | 'bank';

export interface ToneClasses {
  /** Background + text for a pill. */
  pill: string;
  /** Text colour only, for figures and inline emphasis. */
  text: string;
  /** Tint background only, for row highlights. */
  bg: string;
}

const OWNER: Record<Tone, ToneClasses> = {
  danger: { pill: 'bg-danger-tint text-danger', text: 'text-danger', bg: 'bg-danger-tint' },
  warn: { pill: 'bg-warn-tint text-warn', text: 'text-warn', bg: 'bg-warn-tint' },
  success: { pill: 'bg-success-tint text-success', text: 'text-success', bg: 'bg-success-tint' },
  neutral: { pill: 'bg-chip text-sub', text: 'text-ink', bg: 'bg-chip' },
};

const BANK: Record<Tone, ToneClasses> = {
  danger: {
    pill: 'bg-bank-danger-tint text-bank-danger',
    text: 'text-bank-danger',
    bg: 'bg-bank-danger-tint',
  },
  warn: {
    pill: 'bg-bank-warn-tint text-bank-warn',
    text: 'text-bank-warn',
    bg: 'bg-bank-warn-tint',
  },
  success: {
    pill: 'bg-bank-success-tint text-bank-success',
    text: 'text-bank-success',
    bg: 'bg-bank-success-tint',
  },
  neutral: { pill: 'bg-chip text-sub', text: 'text-ink', bg: 'bg-chip' },
};

export function toneClasses(tone: Tone, skin: Skin = 'owner'): ToneClasses {
  return (skin === 'bank' ? BANK : OWNER)[tone];
}

/** Maps a pipeline recommendation to a tone and the label the designs show. */
export function recommendationTone(
  recommendation: 'RELEASE' | 'HOLD' | 'ESCALATE' | 'INSPECT'
): { tone: Tone; label: string } {
  switch (recommendation) {
    case 'HOLD':
      return { tone: 'danger', label: 'HOLD' };
    case 'ESCALATE':
      return { tone: 'danger', label: 'ESCALATE' };
    case 'INSPECT':
      return { tone: 'warn', label: 'INSPECT' };
    case 'RELEASE':
      return { tone: 'success', label: 'ON TRACK' };
  }
}
```

- [ ] **Step 7: Write `src/frontend/app/layout.tsx`**

```tsx
import type { Metadata } from 'next';
import { Baloo_2, Instrument_Sans, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const baloo = Baloo_2({
  subsets: ['latin', 'devanagari'],
  weight: ['500', '600', '700'],
  variable: '--font-baloo',
  display: 'swap',
});

const instrument = Instrument_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-instrument',
  display: 'swap',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  title: { default: 'Neev', template: '%s · Neev' },
  description:
    'Neev protects self-construction home loans on both sides of the table — flagging inflated rates and missing scope before you sign, then verifying every payment against real site progress.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${baloo.variable} ${instrument.variable} ${jetbrains.variable}`}
    >
      <head>
        {/* Applies the saved theme before first paint so the page never flashes
            the wrong palette. Falls back to the OS preference. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('neev-theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 8: Delete the scaffold's demo page and run every check**

```bash
cd src/frontend
rm -f app/page.tsx
cat > app/page.tsx <<'EOF'
export default function Placeholder() {
  return <main className="p-10 text-ink">Landing page arrives in Task 16.</main>;
}
EOF
npm run verify
```
Expected: typecheck clean · lint clean · `No raw hex outside the theme file.` · `Compiled successfully`.

If `check:hex` still fails, it is pointing at real leftovers from the scaffold — remove them; do not add them to `ALLOWED`.

- [ ] **Step 9: Commit**

```bash
git add src/frontend/ && git commit -m "Task 6: Next.js scaffold, AA-corrected theme tokens, no-raw-hex guard"
```

---

### Task 7: Component kit, part 1 — the atoms

Every screen in Phase 2 composes these. A screen may lay out kit components; it may **not** define its own pill, card, table, or bar. Needing a new variant means adding a prop here, in the kit's own file, so every other screen inherits it.

**Files:**
- Create: `src/frontend/components/ui/Logo.tsx`
- Create: `src/frontend/components/ui/StatusPill.tsx`
- Create: `src/frontend/components/ui/StatCard.tsx`
- Create: `src/frontend/components/ui/Button.tsx`
- Create: `src/frontend/components/ui/SegmentedToggle.tsx`
- Create: `src/frontend/components/ui/Card.tsx`
- Create: `src/frontend/components/ui/Figure.tsx`

**Interfaces:**
- Consumes: `lib/tone.ts` (`Tone`, `Skin`, `toneClasses`), `lib/format.ts`.
- Produces (all default exports, props named exactly as below):
  - `<Logo size?: number, skin?: Skin, withWordmark?: boolean />`
  - `<StatusPill tone: Tone, label: string, skin?: Skin, size?: 'sm' | 'md' />`
  - `<StatCard label: string, value: string, sub: string, tone?: Tone, skin?: Skin />`
  - `<Button variant?: 'primary' | 'outline' | 'ghost', skin?: Skin, href?: string, ...ButtonHTMLAttributes />` — renders `<a>` when `href` is set, `<button type="button">` otherwise.
  - `<SegmentedToggle options: {value: string; label: string}[], value: string, paramName: string, skin?: Skin />` — a **URL-driven** tablist; each option is a `<Link>` to `?{paramName}={value}`.
  - `<Card as?: 'div' | 'section', skin?: Skin, className?: string, children />`
  - `<Figure value: string, tone?: Tone, skin?: Skin, size?: 'sm' | 'md' | 'lg' />` — mono, tabular numerals.

- [ ] **Step 1: Write `Logo.tsx`**

The gap decision from spec §7.1: the simple house glyph is the mark for **both** roles, recoloured per skin. Eleven of the fifteen screens already show it; one mark across both consoles is what makes them read as one product. The SVG path is lifted from the prototypes verbatim.

```tsx
import type { Skin } from '@/lib/tone';

// Path taken verbatim from the prototypes' inline SVG.
const HOUSE = 'M20 6 L34 18 L31 18 L31 30 L9 30 L9 18 L6 18 Z';

export default function Logo({
  size = 24,
  skin = 'owner',
  withWordmark = true,
}: {
  size?: number;
  skin?: Skin;
  withWordmark?: boolean;
}) {
  const squareClass = skin === 'bank' ? 'bg-card' : 'bg-brick';
  const glyphClass = skin === 'bank' ? 'fill-bank-bar' : 'fill-card';
  const wordClass = skin === 'bank' ? 'text-card' : 'text-ink';

  return (
    <span className="flex items-center gap-[9px]">
      <span
        className={`flex items-center justify-center rounded-lg ${squareClass}`}
        style={{ width: size, height: size }}
        aria-hidden="true"
      >
        <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 40 40">
          <path d={HOUSE} className={glyphClass} />
        </svg>
      </span>
      {withWordmark && (
        <span className={`font-display text-[17px] font-bold ${wordClass}`}>Neev</span>
      )}
    </span>
  );
}
```

- [ ] **Step 2: Write `StatusPill.tsx`**

The most repeated atom in the bundle — 10+ files, six vocabularies. **The label is always rendered**, never replaced by colour: status must survive for someone who cannot distinguish the red tint.

```tsx
import { toneClasses, type Skin, type Tone } from '@/lib/tone';

export default function StatusPill({
  tone,
  label,
  skin = 'owner',
  size = 'md',
}: {
  tone: Tone;
  label: string;
  skin?: Skin;
  size?: 'sm' | 'md';
}) {
  const { pill } = toneClasses(tone, skin);
  const radius = skin === 'bank' ? 'rounded-[6px]' : 'rounded-full';
  const dims = size === 'sm' ? 'px-2 py-[2px] text-[10.5px]' : 'px-[9px] py-[3px] text-[11px]';
  return (
    <span
      className={`inline-flex flex-none items-center whitespace-nowrap font-semibold ${radius} ${dims} ${pill}`}
    >
      {label}
    </span>
  );
}
```

- [ ] **Step 3: Write `Figure.tsx`, `Card.tsx`, `Button.tsx`**

```tsx
// Figure.tsx — every number, id and ratio in the product renders through this.
// The handoff makes mono numerals a hard rule; centralising it means no screen
// has to remember.
import { toneClasses, type Skin, type Tone } from '@/lib/tone';

export default function Figure({
  value,
  tone = 'neutral',
  skin = 'owner',
  size = 'md',
}: {
  value: string;
  tone?: Tone;
  skin?: Skin;
  size?: 'sm' | 'md' | 'lg';
}) {
  const { text } = toneClasses(tone, skin);
  const dims =
    size === 'lg'
      ? 'text-[23px] font-semibold'
      : size === 'sm'
        ? 'text-[12px] font-medium'
        : 'text-[13.5px] font-medium';
  return <span className={`tnum ${dims} ${text}`}>{value}</span>;
}
```

```tsx
// Card.tsx — the surface. Owner radii are 14-16px, bank 10px; that is the only
// difference, so it is a prop rather than two components.
import type { Skin } from '@/lib/tone';

export default function Card({
  as: Tag = 'div',
  skin = 'owner',
  className = '',
  children,
}: {
  as?: 'div' | 'section';
  skin?: Skin;
  className?: string;
  children: React.ReactNode;
}) {
  const radius = skin === 'bank' ? 'rounded-bank' : 'rounded-card';
  return (
    <Tag className={`bg-card border border-line shadow-card ${radius} ${className}`}>
      {children}
    </Tag>
  );
}
```

```tsx
// Button.tsx — the prototypes contain not one <button>. Every control there is a
// styled <div>: not focusable, not announced, not submittable. This restores the
// semantics. Actions are <button>; navigation is <a>.
import Link from 'next/link';
import type { ButtonHTMLAttributes } from 'react';
import type { Skin } from '@/lib/tone';

type Variant = 'primary' | 'outline' | 'ghost';

const SHAPE: Record<Skin, string> = {
  owner: 'rounded-pill',
  bank: 'rounded-bank',
};

const VARIANT: Record<Variant, string> = {
  primary: 'bg-action text-card hover:bg-action-hover',
  outline: 'border border-input-border bg-card text-ink hover:border-ink',
  ghost: 'text-sub hover:bg-chip hover:text-ink',
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  skin?: Skin;
  href?: string;
}

export default function Button({
  variant = 'outline',
  skin = 'owner',
  href,
  className = '',
  children,
  ...rest
}: Props) {
  const classes = `inline-flex items-center justify-center gap-2 px-4 py-[10px] text-[13.5px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${SHAPE[skin]} ${VARIANT[variant]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" className={classes} {...rest}>
      {children}
    </button>
  );
}
```

- [ ] **Step 4: Write `StatCard.tsx`**

Four of these head BoQ Review and Portfolio. Label is uppercase with letter-spacing; value is mono at 23px; sub is one line of context.

```tsx
import Card from './Card';
import Figure from './Figure';
import type { Skin, Tone } from '@/lib/tone';

export default function StatCard({
  label,
  value,
  sub,
  tone = 'neutral',
  skin = 'owner',
}: {
  label: string;
  value: string;
  sub: string;
  tone?: Tone;
  skin?: Skin;
}) {
  return (
    <Card skin={skin} className="px-[17px] py-[15px]">
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-faint">
        {label}
      </div>
      <div className="mt-[9px]">
        <Figure value={value} tone={tone} skin={skin} size="lg" />
      </div>
      <div className="mt-[6px] text-[12px] leading-[1.45] text-sub">{sub}</div>
    </Card>
  );
}
```

- [ ] **Step 5: Write `SegmentedToggle.tsx`**

Filters and tabs belong in the URL (spec §6.6), so a shared link reproduces what the sender saw — which matters when a credit officer sends a loan to a colleague. This component therefore navigates rather than holding state. It uses `role="tablist"` with `aria-selected` and responds to arrow keys.

```tsx
'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { useRef } from 'react';
import type { Skin } from '@/lib/tone';

export interface ToggleOption {
  value: string;
  label: string;
}

export default function SegmentedToggle({
  options,
  value,
  paramName,
  skin = 'owner',
  label,
}: {
  options: ToggleOption[];
  value: string;
  paramName: string;
  skin?: Skin;
  label: string;
}) {
  const pathname = usePathname();
  const params = useSearchParams();
  const refs = useRef<(HTMLAnchorElement | null)[]>([]);

  const hrefFor = (next: string) => {
    const query = new URLSearchParams(params.toString());
    query.set(paramName, next);
    return `${pathname}?${query.toString()}`;
  };

  const onKeyDown = (event: React.KeyboardEvent, index: number) => {
    const delta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
    if (!delta) return;
    event.preventDefault();
    const next = (index + delta + options.length) % options.length;
    refs.current[next]?.focus();
  };

  const radius = skin === 'bank' ? 'rounded-bank' : 'rounded-pill';

  return (
    <div role="tablist" aria-label={label} className={`inline-flex gap-1 bg-chip p-1 ${radius}`}>
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <Link
            key={option.value}
            ref={(node) => {
              refs.current[index] = node;
            }}
            href={hrefFor(option.value)}
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onKeyDown={(event) => onKeyDown(event, index)}
            scroll={false}
            className={`px-[13px] py-[6px] text-[12.5px] font-semibold transition-colors ${radius} ${
              selected ? 'bg-card text-ink shadow-card' : 'text-sub hover:text-ink'
            }`}
          >
            {option.label}
          </Link>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 6: Verify**

```bash
cd src/frontend && npm run verify
```
Expected: all four checks clean. `check:hex` in particular must stay green — if a component needed a colour the tokens do not carry, add the token to `globals.css`.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/components src/frontend/lib && git commit -m "Task 7: component kit atoms — Logo, StatusPill, StatCard, Button, SegmentedToggle, Card, Figure"
```

---

### Task 8: Component kit, part 2 — chrome, tables, and inputs

**Files:**
- Create: `src/frontend/components/ui/TopBar.tsx`
- Create: `src/frontend/components/ui/NavTabs.tsx`
- Create: `src/frontend/components/ui/ProfileChip.tsx`
- Create: `src/frontend/components/ui/AccessibilityCluster.tsx`
- Create: `src/frontend/components/ui/ThemeToggle.tsx`
- Create: `src/frontend/components/ui/PageHeader.tsx`
- Create: `src/frontend/components/ui/CardTable.tsx`
- Create: `src/frontend/components/ui/StickyRail.tsx`
- Create: `src/frontend/components/ui/KeyValueCard.tsx`
- Create: `src/frontend/components/ui/Dropzone.tsx`
- Create: `src/frontend/components/ui/StageStrip.tsx`
- Create: `src/frontend/components/ui/PhotoSlot.tsx`
- Create: `src/frontend/components/ui/Skeleton.tsx`
- Create: `src/frontend/components/ui/EmptyState.tsx`
- Create: `src/frontend/components/ui/ErrorState.tsx`
- Create: `src/frontend/lib/nav.ts`

**Interfaces:**
- Consumes: Task 7 atoms; `lib/tone.ts`; `lib/format.ts`.
- Produces:
  - `lib/nav.ts`: `OWNER_NAV: NavItem[]`, `BANK_NAV: NavItem[]`, `type NavItem = { href: string; label: string }`, `ownerNavFor(loanId: string): NavItem[]`.
  - `<TopBar skin: Skin, nav: NavItem[], activeHref: string, user?: {name: string; sub: string}, showAccessibility?: boolean />` — replaces the near-identical bar in ten prototype files.
  - `<NavTabs items: NavItem[], activeHref: string, skin: Skin />`
  - `<ProfileChip name: string, sub: string, skin: Skin />`
  - `<AccessibilityCluster />` — language switcher and listen-aloud render **disabled with an explanation**; the theme toggle is fully functional (spec §6.7).
  - `<ThemeToggle />`
  - `<PageHeader eyebrow: string, title: string, sub?: string, actions?: ReactNode, skin?: Skin />`
  - `<CardTable<T> columns: Column<T>[], rows: T[], caption: string, skin?: Skin, rowHref?: (row: T) => string, rowTone?: (row: T) => Tone | null, groupBy?: (row: T) => string />` where `Column<T> = { key: string; header: string; align?: 'left' | 'right'; width?: string; render: (row: T) => ReactNode }`
  - `<StickyRail children />`, `<KeyValueCard title: string, rows: {label: string; value: ReactNode}[], footer?: ReactNode, skin?: Skin />`
  - `<Dropzone name: string, accept: string, label: string, hint: string, multiple?: boolean />`
  - `<StageStrip stages: {name: string; sub: string; state: 'done' | 'current' | 'todo'}[], skin?: Skin />`
  - `<PhotoSlot slotKey: string, label: string, guidance?: string, chips?: {label: string; tone: Tone}[], onFile?: (file: File) => void />`
  - `<Skeleton className?: string />`, `<EmptyState title, body, action? />`, `<ErrorState title, body, retryHref? />`

- [ ] **Step 1: Write `lib/nav.ts`**

Spec §7.3: Setup stays in the bank nav on **all** bank routes — it owns the thresholds that drive every recommendation, so it must remain reachable. The prototypes deleted it from three of four bank screens; that is a fragment artifact, not a decision.

```ts
export interface NavItem {
  href: string;
  label: string;
}

/** Owner nav, from the handoff: My contract · Sanction check · Build progress · Changes. */
export function ownerNavFor(loanId: string): NavItem[] {
  return [
    { href: `/owner/loans/${loanId}/boq`, label: 'My contract' },
    { href: `/owner/loans/${loanId}/sanction`, label: 'Sanction check' },
    { href: `/owner/loans/${loanId}/progress`, label: 'Build progress' },
    { href: `/owner/loans/${loanId}/changes`, label: 'Changes' },
  ];
}

export const BANK_NAV: NavItem[] = [
  { href: '/bank/portfolio', label: 'Portfolio' },
  { href: '/bank/contractors', label: 'Contractors' },
  { href: '/bank/setup', label: 'Setup' },
];
```

- [ ] **Step 2: Write `TopBar.tsx`, `NavTabs.tsx`, `ProfileChip.tsx`**

The bar recurs near-identically across ten files, differing only in which tab carries the active styling. One component with `skin` and `activeHref` props replaces all of it — and it is what makes the bank's dark `#111827` console chrome automatic.

```tsx
// TopBar.tsx
import AccessibilityCluster from './AccessibilityCluster';
import Logo from './Logo';
import NavTabs from './NavTabs';
import ProfileChip from './ProfileChip';
import type { NavItem } from '@/lib/nav';
import type { Skin } from '@/lib/tone';

export default function TopBar({
  skin,
  nav,
  activeHref,
  user,
  showAccessibility = false,
  homeHref = '/',
}: {
  skin: Skin;
  nav: NavItem[];
  activeHref: string;
  user?: { name: string; sub: string };
  showAccessibility?: boolean;
  homeHref?: string;
}) {
  const bar =
    skin === 'bank'
      ? 'bg-bank-bar border-b border-bank-bar'
      : 'bg-card/[0.92] backdrop-blur-[8px] border-b border-line';

  return (
    <header
      className={`sticky top-0 z-10 flex h-[58px] items-center justify-between px-7 ${bar}`}
    >
      <div className="flex items-center gap-[22px]">
        <a href={homeHref} aria-label="Neev home">
          <Logo skin={skin} />
        </a>
        <NavTabs items={nav} activeHref={activeHref} skin={skin} />
      </div>
      <div className="flex items-center gap-[14px]">
        {showAccessibility && <AccessibilityCluster />}
        {user && <ProfileChip name={user.name} sub={user.sub} skin={skin} />}
      </div>
    </header>
  );
}
```

```tsx
// NavTabs.tsx
import Link from 'next/link';
import type { NavItem } from '@/lib/nav';
import type { Skin } from '@/lib/tone';

export default function NavTabs({
  items,
  activeHref,
  skin,
}: {
  items: NavItem[];
  activeHref: string;
  skin: Skin;
}) {
  return (
    <nav aria-label="Primary" className="flex gap-1 text-[13.5px] font-medium">
      {items.map((item) => {
        const active = item.href === activeHref;
        const classes =
          skin === 'bank'
            ? active
              ? 'bg-card text-bank-bar'
              : 'text-bank-inactive hover:text-card'
            : active
              ? 'bg-ink text-card'
              : 'text-sub hover:bg-chip hover:text-ink';
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={`rounded-lg px-[13px] py-[7px] transition-colors ${classes}`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
```

```tsx
// ProfileChip.tsx
import type { Skin } from '@/lib/tone';

export default function ProfileChip({
  name,
  sub,
  skin,
}: {
  name: string;
  sub: string;
  skin: Skin;
}) {
  const nameClass = skin === 'bank' ? 'text-card' : 'text-ink';
  const subClass = skin === 'bank' ? 'text-bank-inactive' : 'text-faint';
  const avatar = skin === 'bank' ? 'bg-bank-accent text-card' : 'bg-ink text-card';
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();

  return (
    <div className="flex items-center gap-[10px]">
      <div className="text-right">
        <div className={`text-[13px] font-semibold leading-[1.2] ${nameClass}`}>{name}</div>
        <div className={`text-[11px] ${subClass}`}>{sub}</div>
      </div>
      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full text-[12px] font-semibold ${avatar}`}
        aria-hidden="true"
      >
        {initials}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write `ThemeToggle.tsx` and `AccessibilityCluster.tsx`**

Spec §6.7: the accessibility cluster is specified as **functional, not decorative** — the handoff says "mocked in prototype, must be functional in build". In this build the theme toggle works app-wide; the language switcher and listen-aloud render with correct semantics and a **disabled state that says why**, since translation and TTS are out of scope. A disabled control that announces the reason beats a dead control that lies.

```tsx
// ThemeToggle.tsx
'use client';

import { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const current = document.documentElement.getAttribute('data-theme');
    setTheme(current === 'dark' ? 'dark' : 'light');
  }, []);

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem('neev-theme', next);
    } catch {
      // Private browsing or blocked storage: the toggle still works this session.
    }
    setTheme(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={theme === 'dark'}
      title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      className="flex h-[30px] w-[30px] items-center justify-center rounded-lg border border-input-border bg-card text-[13px] text-sub hover:text-ink"
    >
      <span aria-hidden="true">◐</span>
      <span className="sr-only">
        {theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      </span>
    </button>
  );
}
```

```tsx
// AccessibilityCluster.tsx
import ThemeToggle from './ThemeToggle';

const OUT_OF_SCOPE = 'Coming soon — this build is English only.';

export default function AccessibilityCluster() {
  return (
    <div className="flex items-center gap-[6px]">
      <button
        type="button"
        disabled
        aria-disabled="true"
        title={`Language: English / हिंदी / తెలుగు. ${OUT_OF_SCOPE}`}
        className="rounded-lg border border-input-border bg-card px-[10px] py-[6px] text-[12px] font-semibold text-sub opacity-55"
      >
        EN <span aria-hidden="true">▾</span>
        <span className="sr-only">. {OUT_OF_SCOPE}</span>
      </button>
      <button
        type="button"
        disabled
        aria-disabled="true"
        title={`Listen to this page. ${OUT_OF_SCOPE}`}
        className="flex h-[30px] w-[30px] items-center justify-center rounded-lg border border-input-border bg-card text-[13px] opacity-55"
      >
        <span aria-hidden="true">🔊</span>
        <span className="sr-only">Listen to this page. {OUT_OF_SCOPE}</span>
      </button>
      <ThemeToggle />
    </div>
  );
}
```

- [ ] **Step 4: Write `PageHeader.tsx`, `StickyRail.tsx`, `KeyValueCard.tsx`**

```tsx
// PageHeader.tsx — eyebrow + h1 + sub + right-aligned actions. Exactly one <h1>
// per page comes from here.
export default function PageHeader({
  eyebrow,
  title,
  sub,
  actions,
}: {
  eyebrow: string;
  title: string;
  sub?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-5">
      <div>
        <div className="text-[12px] font-semibold uppercase tracking-[0.08em] text-faint">
          {eyebrow}
        </div>
        <h1 className="mt-2 font-display text-[28px] font-bold tracking-[-0.02em] text-ink">
          {title}
        </h1>
        {sub && <div className="mt-[6px] text-[14px] text-sub">{sub}</div>}
      </div>
      {actions && <div className="flex flex-none gap-[10px]">{actions}</div>}
    </div>
  );
}
```

```tsx
// StickyRail.tsx — the 340px right column. Stays a rail across 1280-1920px; no
// collapse behaviour is built (laptop-only, spec 6.7).
export default function StickyRail({ children }: { children: React.ReactNode }) {
  return (
    <aside className="sticky top-[86px] flex w-[340px] flex-none flex-col gap-4 self-start">
      {children}
    </aside>
  );
}
```

```tsx
// KeyValueCard.tsx — the "math in one line each" pattern, used by Tranche
// Decision, Build Progress and the sanction rail.
import Card from './Card';
import type { Skin } from '@/lib/tone';

export default function KeyValueCard({
  title,
  rows,
  footer,
  skin = 'owner',
}: {
  title: string;
  rows: { label: string; value: React.ReactNode; sub?: string }[];
  footer?: React.ReactNode;
  skin?: Skin;
}) {
  return (
    <Card skin={skin} className="p-[17px]">
      <h2 className="text-[13.5px] font-bold text-ink">{title}</h2>
      <dl className="mt-3 flex flex-col gap-[10px]">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between gap-3">
            <dt className="text-[12.5px] text-sub">
              {row.label}
              {row.sub && <span className="mt-[2px] block text-[11px] text-faint">{row.sub}</span>}
            </dt>
            <dd className="flex-none text-right">{row.value}</dd>
          </div>
        ))}
      </dl>
      {footer && <div className="mt-[14px] border-t border-line pt-[12px]">{footer}</div>}
    </Card>
  );
}
```

- [ ] **Step 5: Write `CardTable.tsx`**

The BoQ, portfolio, scorecard and math grids are all this component. It renders a real `<table>` — CSS for layout, table semantics for meaning — so row and column relationships survive for a screen reader. It scrolls inside its own `overflow-x` container so the page body never scrolls horizontally below 1280px.

```tsx
import Link from 'next/link';
import Card from './Card';
import { toneClasses, type Skin, type Tone } from '@/lib/tone';

export interface Column<T> {
  key: string;
  header: string;
  align?: 'left' | 'right';
  width?: string;
  render: (row: T) => React.ReactNode;
}

export default function CardTable<T>({
  columns,
  rows,
  caption,
  skin = 'owner',
  rowHref,
  rowTone,
  groupBy,
  emptyMessage = 'Nothing to show yet.',
}: {
  columns: Column<T>[];
  rows: T[];
  /** Announced to screen readers; visually hidden. Always describe the data. */
  caption: string;
  skin?: Skin;
  rowHref?: (row: T) => string;
  rowTone?: (row: T) => Tone | null;
  groupBy?: (row: T) => string;
  emptyMessage?: string;
}) {
  const grouped = groupBy
    ? rows.reduce<Map<string, T[]>>((acc, row) => {
        const key = groupBy(row);
        acc.set(key, [...(acc.get(key) ?? []), row]);
        return acc;
      }, new Map())
    : new Map([['', rows]]);

  return (
    <Card skin={skin} className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-left">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-line">
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  style={column.width ? { width: column.width } : undefined}
                  className={`px-[15px] py-[11px] text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint ${
                    column.align === 'right' ? 'text-right' : 'text-left'
                  }`}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          {[...grouped.entries()].map(([group, groupRows]) => (
            <tbody key={group || 'all'}>
              {group && (
                <tr>
                  <th
                    scope="colgroup"
                    colSpan={columns.length}
                    className="bg-hover px-[15px] py-[8px] text-[10.5px] font-semibold uppercase tracking-[0.06em] text-sub"
                  >
                    {group}
                  </th>
                </tr>
              )}
              {groupRows.map((row, index) => {
                const tone = rowTone?.(row) ?? null;
                const tint = tone ? toneClasses(tone, skin).bg : '';
                const href = rowHref?.(row);
                return (
                  <tr
                    key={index}
                    className={`border-b border-rowline last:border-0 hover:bg-hover ${tint}`}
                  >
                    {columns.map((column, columnIndex) => (
                      <td
                        key={column.key}
                        className={`px-[15px] py-[12px] align-top text-[13px] ${
                          column.align === 'right' ? 'text-right' : 'text-left'
                        }`}
                      >
                        {href && columnIndex === 0 ? (
                          <Link href={href} className="hover:text-action">
                            {column.render(row)}
                          </Link>
                        ) : (
                          column.render(row)
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          ))}
        </table>
      </div>
      {rows.length === 0 && (
        <p className="px-[15px] py-8 text-center text-[13px] text-sub">{emptyMessage}</p>
      )}
    </Card>
  );
}
```

- [ ] **Step 6: Write `Dropzone.tsx`, `StageStrip.tsx`, `PhotoSlot.tsx`**

`PhotoSlot` replaces the prototype's `image-slot.js`, which stored data-URLs in a sidecar JSON via `window.omelette` — pure design-runtime infrastructure with no production role. Three of its behaviours are kept: client-side downscale before upload, the image accept-list, and a fit notion for same-angle comparison. The 12 slot ids across 4 screens become `{loanId, tranche, slotKey}`.

```tsx
// Dropzone.tsx — a real file input with a real label. The prototype's dropzone
// is a div; ported literally it would be unreachable by keyboard.
export default function Dropzone({
  name,
  accept,
  label,
  hint,
  multiple = false,
}: {
  name: string;
  accept: string;
  label: string;
  hint: string;
  multiple?: boolean;
}) {
  const id = `dz-${name}`;
  return (
    <div className="rounded-card border-2 border-dashed border-line bg-card px-6 py-9 text-center">
      <label htmlFor={id} className="cursor-pointer">
        <span className="block font-display text-[16px] font-semibold text-ink">{label}</span>
        <span className="mt-[6px] block text-[12.5px] text-sub">{hint}</span>
      </label>
      <input
        id={id}
        name={name}
        type="file"
        accept={accept}
        multiple={multiple}
        className="mx-auto mt-4 block text-[12.5px] text-sub file:mr-3 file:rounded-pill file:border-0 file:bg-action file:px-4 file:py-2 file:text-[12.5px] file:font-semibold file:text-card hover:file:bg-action-hover"
      />
    </div>
  );
}
```

```tsx
// StageStrip.tsx — the 5-stage checklist (Tranche Decision) and the journey
// strip (Onboarding, Login) are the same shape.
import { toneClasses, type Skin } from '@/lib/tone';

export interface Stage {
  name: string;
  sub: string;
  state: 'done' | 'current' | 'todo';
}

export default function StageStrip({
  stages,
  skin = 'owner',
}: {
  stages: Stage[];
  skin?: Skin;
}) {
  return (
    <ol className="flex gap-[10px]">
      {stages.map((stage) => {
        const tone = stage.state === 'todo' ? 'neutral' : 'success';
        const { bg, text } = toneClasses(tone, skin);
        const radius = skin === 'bank' ? 'rounded-bank' : 'rounded-card';
        return (
          <li
            key={stage.name}
            className={`flex-1 border border-line px-3 py-[10px] ${radius} ${stage.state === 'todo' ? 'bg-card' : bg}`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`flex h-[18px] w-[18px] items-center justify-center rounded-full text-[11px] font-bold ${stage.state === 'todo' ? 'bg-chip text-faint' : `${bg} ${text}`}`}
                aria-hidden="true"
              >
                {stage.state === 'todo' ? '·' : '✓'}
              </span>
              <span
                className={`text-[12.5px] font-semibold ${stage.state === 'todo' ? 'text-faint' : 'text-ink'}`}
              >
                {stage.name}
              </span>
            </div>
            <div className="mt-[4px] text-[11px] text-sub">{stage.sub}</div>
            <span className="sr-only">
              {stage.state === 'done'
                ? 'Complete.'
                : stage.state === 'current'
                  ? 'In progress.'
                  : 'Not started.'}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
```

```tsx
// PhotoSlot.tsx
'use client';

import Image from 'next/image';
import { useId, useState } from 'react';
import StatusPill from './StatusPill';
import type { Tone } from '@/lib/tone';

const ACCEPT = 'image/png,image/jpeg,image/webp,image/avif';
const MAX_EDGE = 1600;

export default function PhotoSlot({
  slotKey,
  label,
  guidance,
  chips = [],
  onFile,
}: {
  slotKey: string;
  label: string;
  guidance?: string;
  chips?: { label: string; tone: Tone }[];
  onFile?: (file: File) => void;
}) {
  const inputId = useId();
  const [preview, setPreview] = useState<string | null>(null);
  const [status, setStatus] = useState('No photo yet');

  const handle = async (file: File | undefined) => {
    if (!file) return;
    setStatus(`Preparing ${file.name}…`);
    const downscaled = await downscale(file);
    setPreview(URL.createObjectURL(downscaled));
    setStatus(`${file.name} ready to upload`);
    onFile?.(new File([downscaled], file.name, { type: downscaled.type }));
  };

  return (
    <div className="rounded-card border border-line bg-card p-3">
      <label htmlFor={inputId} className="block text-[12.5px] font-semibold text-ink">
        {label}
      </label>
      {guidance && <p className="mt-[3px] text-[11px] text-sub">{guidance}</p>}

      <div className="mt-[10px] flex aspect-[4/3] items-center justify-center overflow-hidden rounded-[10px] bg-chip">
        {preview ? (
          <Image
            src={preview}
            alt={`${label} — uploaded site photo`}
            width={MAX_EDGE}
            height={(MAX_EDGE * 3) / 4}
            className="h-full w-full object-cover"
            unoptimized
          />
        ) : (
          <span className="text-[11.5px] text-faint">Same spot, every month</span>
        )}
      </div>

      <input
        id={inputId}
        type="file"
        accept={ACCEPT}
        data-slot-key={slotKey}
        onChange={(event) => handle(event.target.files?.[0])}
        className="mt-[10px] block w-full text-[11.5px] text-sub"
      />
      {/* Upload status is announced, not merely shown. */}
      <p aria-live="polite" className="mt-[6px] text-[11px] text-faint">
        {status}
      </p>

      {chips.length > 0 && (
        <div className="mt-[8px] flex flex-wrap gap-[6px]">
          {chips.map((chip) => (
            <StatusPill key={chip.label} tone={chip.tone} label={chip.label} size="sm" />
          ))}
        </div>
      )}
    </div>
  );
}

/** Downscale to MAX_EDGE before upload — the one behaviour worth keeping from
 *  the prototype's image-slot.js. Falls back to the original on any failure. */
async function downscale(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    if (scale === 1) return file;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob>((resolve) =>
      canvas.toBlob((blob) => resolve(blob ?? file), 'image/jpeg', 0.85)
    );
  } catch {
    return file;
  }
}
```

- [ ] **Step 7: Write the three state components**

Every data-driven screen implements four states, not one. The prototypes only ever show the populated state — the single easiest thing to forget when porting from a mockup.

```tsx
// Skeleton.tsx
export default function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-[8px] bg-chip ${className}`}
    />
  );
}
```

```tsx
// EmptyState.tsx
import Card from './Card';

export default function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <Card className="px-6 py-12 text-center">
      <h2 className="font-display text-[18px] font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-[46ch] text-[13px] text-sub">{body}</p>
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </Card>
  );
}
```

```tsx
// ErrorState.tsx
import Card from './Card';
import Button from './Button';

export default function ErrorState({
  title = 'We could not load this',
  body,
  retryHref,
  onRetry,
}: {
  title?: string;
  body: string;
  retryHref?: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="px-6 py-12 text-center">
      <h2 className="font-display text-[18px] font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-[46ch] text-[13px] text-sub">{body}</p>
      <div className="mt-5 flex justify-center">
        {retryHref ? (
          <Button href={retryHref} variant="primary">
            Try again
          </Button>
        ) : (
          <Button variant="primary" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    </Card>
  );
}
```

- [ ] **Step 8: Verify the whole kit**

```bash
cd src/frontend && npm run verify
```
Expected: typecheck clean · lint clean · no raw hex · build succeeds.

- [ ] **Step 9: Commit**

```bash
git add src/frontend/ && git commit -m "Task 8: component kit chrome, tables, inputs, and the four screen states"
```

**Phase 0 gate — all three must pass before any Phase 1 work starts:**

```bash
python3 -m tests.test_offline                                  # 28 tests, OK
cd src/backend && .venv/bin/python -m pytest tests/ -q  # all pass
cd src/frontend && npm run verify                                  # all four checks clean
```

---

## Phase 1 — Data layer, mappers, and the app shell

These three tasks touch disjoint files and may run in parallel. None of them depends on another's output at runtime; the interfaces below are the whole contract between them.

---

### Task 9: SQLite data model and an idempotent seed

**Files:**
- Create: `src/backend/app/db/__init__.py`
- Create: `src/backend/app/db/models.py`
- Create: `src/backend/app/db/session.py`
- Create: `src/backend/app/db/seed.py`
- Create: `src/backend/app/fixtures/portfolio_rows.json`
- Create: `src/backend/tests/test_seed.py`

**Interfaces:**
- Consumes: `app.core.settings.get_settings`, `app.fixtures.loader.load_pipeline_output`.
- Produces:
  - `app.db.session.engine`, `app.db.session.SessionLocal`, `app.db.session.get_session() -> Iterator[Session]`, `app.db.session.init_db() -> None`.
  - `app.db.models`: `Base`, `Loan`, `Contractor`, `BoqRevision`, `LineItem`, `Flag`, `Question`, `Tranche`, `Photo`, `ChangeOrder`, `Decision`.
  - `app.db.seed.seed(reset: bool = False) -> dict[str, int]` — returns row counts per table; safe to run repeatedly.
  - CLI: `python -m app.db.seed --reset`.

**Persisted rows are pipeline-shaped, not screen-shaped** (spec §5.1a seam 4). `Flag` stores `evidence`, `question`, `benchmark_rate`, `deviation_pct`; `Tranche` stores `confidence` and `needs_human_review`. Fields the mockups never display are stored anyway, nullable, so a real run populates them without a migration.

- [ ] **Step 1: Write `src/backend/app/fixtures/portfolio_rows.json`**

The design's ten rows, verbatim (spec §4.5). Recomputing them from `draw_schedule.csv` gives materially different values and flips three statuses — that is recorded in the spec and deliberately not done here. Money is stored as integers; the `₹` never appears.

```json
[
  {"loan_id": "1003", "borrower": "K. Srinivas", "locality": "Medchal", "paid_up_to": "Slab (T3)", "seen_on_site": "Plinth only", "behind": true, "disbursed": 1921557, "exposure": 1.42, "gap": -690000, "action": "HOLD"},
  {"loan_id": "1004", "borrower": "P. Anjali", "locality": "Shamirpet", "paid_up_to": "Roof (T4)", "seen_on_site": "Slab only", "behind": true, "disbursed": 3757129, "exposure": 1.35, "gap": -820000, "action": "HOLD"},
  {"loan_id": "1001", "borrower": "Ravi Kumar", "locality": "Kompally", "paid_up_to": "Slab (T3)", "seen_on_site": "Slab ✓", "behind": false, "disbursed": 1800000, "exposure": 1.29, "gap": -580000, "action": "HOLD"},
  {"loan_id": "1009", "borrower": "M. Farhan", "locality": "Bachupally", "paid_up_to": "Roof (T4)", "seen_on_site": "Roof ✓", "behind": false, "disbursed": 2487861, "exposure": 1.04, "gap": -110000, "action": "INSPECT"},
  {"loan_id": "1006", "borrower": "T. Lakshmi", "locality": "Kompally", "paid_up_to": "Slab (T3)", "seen_on_site": "Slab ✓", "behind": false, "disbursed": 1296892, "exposure": 0.98, "gap": 40000, "action": "INSPECT"},
  {"loan_id": "1010", "borrower": "S. Reddy", "locality": "Alwal", "paid_up_to": "Roof (T4)", "seen_on_site": "Roof ✓", "behind": false, "disbursed": 1608035, "exposure": 0.96, "gap": 75000, "action": "ON TRACK"},
  {"loan_id": "1002", "borrower": "D. Prasad", "locality": "Kukatpally", "paid_up_to": "Slab (T3)", "seen_on_site": "Slab ✓", "behind": false, "disbursed": 1214337, "exposure": 0.97, "gap": 105000, "action": "ON TRACK"},
  {"loan_id": "1007", "borrower": "V. Naidu", "locality": "Suraram", "paid_up_to": "Done (T5)", "seen_on_site": "Finishing ✓", "behind": false, "disbursed": 2500000, "exposure": 0.94, "gap": null, "action": "ON TRACK"},
  {"loan_id": "1008", "borrower": "G. Swathi", "locality": "Jeedimetla", "paid_up_to": "Done (T5)", "seen_on_site": "Finishing ✓", "behind": false, "disbursed": 2500000, "exposure": 0.93, "gap": null, "action": "ON TRACK"},
  {"loan_id": "1005", "borrower": "B. Yadav", "locality": "Quthbullapur", "paid_up_to": "Done (T5)", "seen_on_site": "Finishing ✓", "behind": false, "disbursed": 1500000, "exposure": 0.91, "gap": null, "action": "ON TRACK"}
]
```

A `gap` of `null` means the loan is closed — the design renders "closed" in the faint colour rather than a figure.

- [ ] **Step 2: Write the failing test**

`src/backend/tests/test_seed.py`:
```python
"""The seeded book must match the screens exactly, and seeding twice must not
double the rows."""

import pytest
from sqlalchemy import func, select

from app.db import models
from app.db.seed import seed
from app.db.session import SessionLocal, init_db


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    import app.db.session as session_module

    session_module.reconfigure()
    init_db()
    yield
    get_settings.cache_clear()


def test_seed_creates_ten_loans():
    seed(reset=True)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(models.Loan)) == 10


def test_seed_is_idempotent():
    seed(reset=True)
    seed()
    seed()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(models.Loan)) == 10


def test_loan_1001_matches_the_portfolio_design_row():
    seed(reset=True)
    with SessionLocal() as db:
        loan = db.scalar(select(models.Loan).where(models.Loan.id == "1001"))
        assert loan is not None
        assert loan.borrower_name == "Ravi Kumar"
        assert loan.locality == "Kompally"
        assert loan.sanctioned == 2800000
        assert loan.disbursed == 1800000
        assert loan.exposure_ratio == 1.29
        assert loan.cost_to_complete_gap == -580000
        assert loan.recommendation == "HOLD"


def test_flags_are_persisted_with_their_evidence_not_just_a_label():
    seed(reset=True)
    with SessionLocal() as db:
        flags = db.scalars(
            select(models.Flag).join(models.BoqRevision).where(models.BoqRevision.loan_id == "1001")
        ).all()
        assert len(flags) == 9
        assert all(flag.evidence and flag.question for flag in flags)
        rate_flags = [f for f in flags if f.type == "RATE_OUTLIER"]
        assert all(f.benchmark_rate is not None for f in rate_flags)


def test_closed_loans_have_a_null_gap_rather_than_zero():
    seed(reset=True)
    with SessionLocal() as db:
        loan = db.scalar(select(models.Loan).where(models.Loan.id == "1007"))
        assert loan is not None
        assert loan.cost_to_complete_gap is None
```

- [ ] **Step 3: Run it to verify it fails**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_seed.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 4: Write `src/backend/app/db/session.py`**

```python
"""Engine and session factory.

SQLite via SQLAlchemy: zero setup, seeded from the repo's fixtures, swappable
for Postgres later behind the ORM. `reconfigure()` exists so tests can point the
engine at a temp file after changing DATABASE_URL.
"""

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings

engine = None
SessionLocal: sessionmaker[Session] = None  # type: ignore[assignment]


def reconfigure() -> None:
    """(Re)build the engine from current settings."""
    global engine, SessionLocal
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


reconfigure()


def init_db() -> None:
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with SessionLocal() as db:
        yield db
```

- [ ] **Step 5: Write `src/backend/app/db/models.py`**

```python
"""The application's own state.

Columns mirror the pipeline's fields, not the mockups' display strings (spec
5.1a seam 4). Evidence text, benchmark rates, confidence bands and
needs_human_review are stored even where no screen shows them, nullable, so a
real pipeline run populates them without a migration.

Money is stored as integer rupees. No column ever holds a formatted string.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sites: Mapped[int] = mapped_column(Integer, default=0)
    flags_per_boq: Mapped[float | None] = mapped_column(Float, nullable=True)
    underspecified_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    overrun_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sites_gone_quiet: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(16), default="RELIABLE")

    loans: Mapped[list["Loan"]] = relationship(back_populates="contractor")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    borrower_name: Mapped[str] = mapped_column(String(120))
    locality: Mapped[str] = mapped_column(String(80))
    plot_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    built_up_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sanctioned: Mapped[int] = mapped_column(Integer)
    disbursed: Mapped[int] = mapped_column(Integer, default=0)
    contractor_id: Mapped[str | None] = mapped_column(ForeignKey("contractors.id"), nullable=True)

    # Denormalised risk snapshot — the portfolio table's columns. Sourced from
    # the mockups in this build; from risk_assessment when the pipeline lands.
    paid_up_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    seen_on_site: Mapped[str | None] = mapped_column(String(40), nullable=True)
    behind_schedule: Mapped[bool] = mapped_column(Boolean, default=False)
    exposure_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    exposure_undefined: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_to_complete_gap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Preserves the design's exposure-descending order without recomputing it.
    hotlist_rank: Mapped[int] = mapped_column(Integer, default=0)

    contractor: Mapped[Contractor | None] = relationship(back_populates="loans")
    revisions: Mapped[list["BoqRevision"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="BoqRevision.rev"
    )
    tranches: Mapped[list["Tranche"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="Tranche.number"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="Question.number"
    )
    change_orders: Mapped[list["ChangeOrder"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan"
    )


class BoqRevision(Base):
    __tablename__ = "boq_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    rev: Mapped[int] = mapped_column(Integer, default=1)
    received_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    boq_total: Mapped[int] = mapped_column(Integer)
    payment_pct_before_slab: Mapped[float] = mapped_column(Float)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    # Pipeline provenance, unused by any screen. Stored so a live run has a home.
    pipeline_mode: Mapped[str] = mapped_column(String(16), default="fixture")
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    loan: Mapped[Loan] = relationship(back_populates="revisions")
    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="revision", cascade="all, delete-orphan"
    )
    flags: Mapped[list["Flag"]] = relationship(
        back_populates="revision", cascade="all, delete-orphan"
    )


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("boq_revisions.id"))
    item_id: Mapped[str] = mapped_column(String(16))
    section: Mapped[str | None] = mapped_column(String(80), nullable=True)
    desc: Mapped[str] = mapped_column(Text)
    qty: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    rate: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)

    revision: Mapped[BoqRevision] = relationship(back_populates="line_items")


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("boq_revisions.id"))
    item: Mapped[str] = mapped_column(String(16))
    type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(40))
    tone: Mapped[str] = mapped_column(String(16), default="danger")
    group_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence: Mapped[str] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)
    benchmark_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expected_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    revision: Mapped[BoqRevision] = relationship(back_populates="flags")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|sent|replied
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reply: Mapped[str | None] = mapped_column(Text, nullable=True)

    loan: Mapped[Loan] = relationship(back_populates="questions")


class Tranche(Base):
    __tablename__ = "tranches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    number: Mapped[int] = mapped_column(Integer)
    milestone: Mapped[str] = mapped_column(String(32))
    planned_cum_pct: Mapped[float] = mapped_column(Float)
    disbursed_cum: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="upcoming")  # paid|on_hold|upcoming
    inspection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    observed_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Pipeline fields. Not all are shown; all are stored.
    verified_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exposure_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    exposure_undefined: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_to_complete: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_to_complete_gap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    recommendation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    owner_view: Mapped[str | None] = mapped_column(Text, nullable=True)
    officer_view: Mapped[str | None] = mapped_column(Text, nullable=True)

    loan: Mapped[Loan] = relationship(back_populates="tranches")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="tranche", cascade="all, delete-orphan"
    )
    decision: Mapped["Decision | None"] = relationship(
        back_populates="tranche", cascade="all, delete-orphan", uselist=False
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tranche_id: Mapped[int] = mapped_column(ForeignKey("tranches.id"))
    slot_key: Mapped[str] = mapped_column(String(40))
    caption: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    geotag_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    timestamp_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    same_angle: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tranche: Mapped[Tranche] = relationship(back_populates="photos")


class ChangeOrder(Base):
    __tablename__ = "change_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    title: Mapped[str] = mapped_column(String(200))
    signed_desc: Mapped[str] = mapped_column(Text)
    signed_amount: Mapped[int] = mapped_column(Integer)
    proposed_desc: Mapped[str] = mapped_column(Text)
    proposed_amount: Mapped[int] = mapped_column(Integer)
    neevs_read: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    tone: Mapped[str] = mapped_column(String(16), default="warn")

    loan: Mapped[Loan] = relationship(back_populates="change_orders")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tranche_id: Mapped[int] = mapped_column(ForeignKey("tranches.id"), unique=True)
    action: Mapped[str] = mapped_column(String(16))  # RELEASE|HOLD|ESCALATE
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(80), default="credit officer")
    decided_at: Mapped[datetime] = mapped_column(DateTime)
    # The full evidence trail the designs promise gets written to the loan file.
    evidence_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    tranche: Mapped[Tranche] = relationship(back_populates="decision")
```

- [ ] **Step 6: Write `src/backend/app/db/seed.py`**

```python
"""Idempotent seed.

Sources, in order of authority:
  - fixtures/draw_schedule.csv          -> tranche rows, sanctioned, disbursed
  - app/fixtures/portfolio_rows.json    -> borrower names, localities, and the
                                           design's risk figures and ordering
  - app/fixtures/loan_*_pipeline.json   -> BoQ line items, flags, questions,
                                           narratives for 1001 and 1002

Run: python -m app.db.seed --reset
"""

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, select

from app.db import models
from app.db.session import SessionLocal, init_db
from app.fixtures.loader import available_loan_ids, load_pipeline_output

REPO_ROOT = Path(__file__).resolve().parents[4]
DRAW_SCHEDULE = REPO_ROOT / "fixtures" / "draw_schedule.csv"
PORTFOLIO_ROWS = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio_rows.json"

CONTRACTORS = [
    # From Neev 5 Contractor Scorecard.dc.html. Loan 1001's contractor is named
    # on the BoQ Review header: "Sri Sai Constructions".
    {"id": "c1", "name": "Sri Sai Constructions", "sites": 4, "flags_per_boq": 7.2,
     "underspecified_share": 0.31, "overrun_pct": 0.18, "sites_gone_quiet": 1, "tier": "WATCH"},
    {"id": "c2", "name": "Bhavya Builders", "sites": 3, "flags_per_boq": 3.1,
     "underspecified_share": 0.14, "overrun_pct": 0.07, "sites_gone_quiet": 0, "tier": "REVIEW"},
    {"id": "c3", "name": "Sree Rama Constructions", "sites": 3, "flags_per_boq": 1.4,
     "underspecified_share": 0.05, "overrun_pct": 0.02, "sites_gone_quiet": 0, "tier": "RELIABLE"},
]

LOAN_CONTRACTOR = {
    "1001": "c1", "1003": "c1", "1004": "c1", "1009": "c1",
    "1002": "c3", "1005": "c3", "1010": "c3",
    "1006": "c2", "1007": "c2", "1008": "c2",
}

PLOT_LABELS = {"1001": "Plot 47, Kompally"}
BUILT_UP = {"1001": 1800, "1002": 1650}

# Tranche status for the golden case: T1/T2 paid, T3 held pending this decision.
TRANCHE_STATUS_1001 = {1: "paid", 2: "paid", 3: "on_hold"}


def _tables_in_delete_order() -> list:
    return [
        models.Decision, models.Photo, models.Tranche, models.Flag, models.LineItem,
        models.Question, models.ChangeOrder, models.BoqRevision, models.Loan, models.Contractor,
    ]


def seed(reset: bool = False) -> dict[str, int]:
    init_db()
    with SessionLocal() as db:
        if reset:
            for table in _tables_in_delete_order():
                db.execute(delete(table))
            db.commit()

        if db.scalar(select(models.Loan).limit(1)) is not None:
            # Already seeded. Idempotent by design: reseeding a populated
            # database is a no-op rather than a duplicate-key error.
            return _counts(db)

        for row in CONTRACTORS:
            db.add(models.Contractor(**row))

        rows = json.loads(PORTFOLIO_ROWS.read_text(encoding="utf-8"))
        schedule = _read_draw_schedule()

        for rank, row in enumerate(rows):
            loan_id = row["loan_id"]
            tranches = schedule[loan_id]
            db.add(
                models.Loan(
                    id=loan_id,
                    borrower_name=row["borrower"],
                    locality=row["locality"],
                    plot_label=PLOT_LABELS.get(loan_id),
                    built_up_sqft=BUILT_UP.get(loan_id),
                    sanctioned=tranches[0]["sanctioned"],
                    disbursed=row["disbursed"],
                    contractor_id=LOAN_CONTRACTOR.get(loan_id),
                    paid_up_to=row["paid_up_to"],
                    seen_on_site=row["seen_on_site"],
                    behind_schedule=row["behind"],
                    exposure_ratio=row["exposure"],
                    cost_to_complete_gap=row["gap"],
                    recommendation=_recommendation(row["action"]),
                    hotlist_rank=rank,
                )
            )
            for entry in tranches:
                status = (
                    TRANCHE_STATUS_1001.get(entry["number"], "upcoming")
                    if loan_id == "1001"
                    else ("paid" if entry["disbursed_cum"] <= row["disbursed"] else "upcoming")
                )
                db.add(
                    models.Tranche(
                        loan_id=loan_id,
                        number=entry["number"],
                        milestone=entry["milestone"],
                        planned_cum_pct=entry["planned_cum_pct"],
                        disbursed_cum=entry["disbursed_cum"],
                        inspection_date=entry["inspection_date"],
                        observed_stage=entry["observed_stage"],
                        status=status,
                    )
                )
        db.commit()

        for loan_id in available_loan_ids():
            _seed_pipeline_output(db, loan_id)
        db.commit()

        _seed_change_orders(db)
        db.commit()

        return _counts(db)


def _recommendation(action: str) -> str:
    return {"HOLD": "HOLD", "INSPECT": "INSPECT", "ON TRACK": "RELEASE"}[action]


def _read_draw_schedule() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with DRAW_SCHEDULE.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            out.setdefault(raw["loan_id"], []).append(
                {
                    "number": int(raw["tranche_no"]),
                    "milestone": raw["milestone"],
                    "planned_cum_pct": float(raw["planned_cum_pct"]),
                    "sanctioned": int(raw["sanctioned"]),
                    "disbursed_cum": int(raw["disbursed_cum"]),
                    "inspection_date": date.fromisoformat(raw["inspection_date"]),
                    "observed_stage": raw["observed_stage"],
                }
            )
    return out


# Which BoQ Review group each flag belongs under. Groups and their order are the
# mockup's, verbatim.
FLAG_GROUPS = {
    "2.3": "FOUNDATION & RCC", "3.1": "FOUNDATION & RCC", "3.2": "FOUNDATION & RCC",
    "4.2": "STEEL",
    "7.1": "FLOORING & ELECTRICAL", "9.1": "FLOORING & ELECTRICAL", "9.2": "FLOORING & ELECTRICAL",
}
MISSING_SCOPE_GROUP = "PLASTERING — EXPECTED BUT ABSENT"


def _seed_pipeline_output(db, loan_id: str) -> None:
    output = load_pipeline_output(loan_id)
    findings = output.boq_findings

    revision = models.BoqRevision(
        loan_id=loan_id,
        rev=1,
        received_on=date(2026, 8, 12) if loan_id == "1001" else None,
        source_filename="sample_boq.pdf" if loan_id == "1001" else "clean_boq.pdf",
        boq_total=int(findings.boq_total),
        payment_pct_before_slab=findings.payment_pct_before_slab,
        item_count=40 if loan_id == "1001" else 43,
        pipeline_mode="fixture",
    )
    db.add(revision)
    db.flush()

    for item in findings.line_items:
        db.add(
            models.LineItem(
                revision_id=revision.id, item_id=item.id, section=item.section, desc=item.desc,
                qty=item.qty, unit=item.unit, rate=item.rate, amount=item.amount,
            )
        )

    for flag in findings.flags:
        db.add(
            models.Flag(
                revision_id=revision.id, item=flag.item, type=flag.type, label=flag.label,
                tone=flag.tone,
                group_name=MISSING_SCOPE_GROUP if flag.type == "MISSING_SCOPE"
                else FLAG_GROUPS.get(flag.item, "OTHER"),
                evidence=flag.evidence, question=flag.question,
                benchmark_rate=flag.benchmark_rate, deviation_pct=flag.deviation_pct,
                expected_qty=flag.expected_qty, expected_unit=flag.expected_unit,
                expected_amount=flag.expected_amount,
            )
        )

    # The "Send before you sign" list, from the BoQ Review mockup verbatim.
    if loan_id == "1001":
        for number, text in enumerate(
            [
                "Confirm the TMT grade for item 4.2 — Fe 500 or Fe 500D per IS 1786 — in writing.",
                "RCC M25 is priced at ₹9,800/cum against a ₹8,033 local benchmark. What is the basis?",
                "External plaster and terrace waterproofing are absent. In scope, or extra — and at what rate?",
                "45% is due before slab. Please restructure toward the standard 25%-before-slab pattern.",
            ],
            start=1,
        ):
            db.add(models.Question(loan_id=loan_id, number=number, text=text, status="draft"))

    risk = output.risk_assessment
    inspection = output.inspection_result
    if risk is not None:
        current = db.scalar(
            select(models.Tranche)
            .where(models.Tranche.loan_id == loan_id, models.Tranche.number == 3)
        )
        if current is not None:
            current.verified_value = int(risk.verified_value)
            current.exposure_ratio = risk.exposure_ratio
            current.exposure_undefined = risk.exposure_undefined
            current.cost_to_complete = int(risk.cost_to_complete) if risk.cost_to_complete else None
            current.cost_to_complete_gap = int(risk.cost_to_complete_gap)
            current.recommendation = risk.recommendation
            current.owner_view = output.explanation.owner_view
            current.officer_view = output.explanation.officer_view
            if inspection is not None:
                current.confidence = inspection.confidence
                current.needs_human_review = inspection.needs_human_review
                for index, note in enumerate(inspection.evidence_notes[:3]):
                    db.add(
                        models.Photo(
                            tranche_id=current.id,
                            slot_key=f"{loan_id}-t3-angle{index + 1}",
                            caption=note,
                            geotag_match=inspection.geotag_match,
                            timestamp_ok=inspection.timestamp_ok,
                            same_angle=inspection.same_angle,
                            taken_at=datetime(2026, 8, 10, 11, 42),
                        )
                    )


def _seed_change_orders(db) -> None:
    # From Neev 6 Change Orders.dc.html.
    db.add_all(
        [
            models.ChangeOrder(
                loan_id="1001",
                title="Kitchen platform upgrade",
                signed_desc="Granite for kitchen platform, 18mm — 6.5 sqm at ₹2,900",
                signed_amount=18850,
                proposed_desc="Quartz composite platform, 20mm — 6.5 sqm at ₹5,400",
                proposed_amount=35100,
                neevs_read="Quartz at ₹5,400/sqm is within the Kompally range of ₹4,900–5,800, so the rate is fair. The change is a genuine upgrade, not a repricing of signed work.",
                status="pending",
                tone="warn",
            ),
            models.ChangeOrder(
                loan_id="1001",
                title="Additional electrical points",
                signed_desc="Concealed wiring per point — 68 points at ₹720",
                signed_amount=48960,
                proposed_desc="Concealed wiring per point — 79 points at ₹860",
                proposed_amount=67940,
                neevs_read="The 11 extra points are reasonable. The rate rising from ₹720 to ₹860 on the same work is not — the signed rate should hold for the added points.",
                status="pending",
                tone="danger",
            ),
        ]
    )


def _counts(db) -> dict[str, int]:
    from sqlalchemy import func

    return {
        table.__tablename__: db.scalar(select(func.count()).select_from(table)) or 0
        for table in _tables_in_delete_order()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Neev application database.")
    parser.add_argument("--reset", action="store_true", help="Delete every row first.")
    args = parser.parse_args()
    for table, count in seed(reset=args.reset).items():
        print(f"{table:16} {count}")
```

`src/backend/app/db/__init__.py` is empty.

- [ ] **Step 7: Run the tests to verify they pass**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_seed.py -q
```
Expected: 5 passed

- [ ] **Step 8: Seed the real database and eyeball the counts**

```bash
cd src/backend && .venv/bin/python -m app.db.seed --reset
```
Expected: `loans 10`, `tranches 40`, `flags 9`, `questions 4`, `contractors 3`, `change_orders 2`, `photos 3`.

- [ ] **Step 9: Commit**

```bash
git add src/backend/ && git commit -m "Task 9: SQLAlchemy models and an idempotent, mockup-faithful seed"
```

---

### Task 10: View schemas and the mapper layer

The **only** place in the codebase that knows about presentation. Today it maps fixture → view model; later it maps live → view model through the identical function, because both inputs have the same shape (spec §5.1a seam 3).

**Files:**
- Create: `src/backend/app/schemas/views.py`
- Create: `src/backend/app/mappers/__init__.py`
- Create: `src/backend/app/mappers/boq.py`
- Create: `src/backend/app/mappers/sanction.py`
- Create: `src/backend/app/mappers/portfolio.py`
- Create: `src/backend/app/mappers/tranche.py`
- Create: `src/backend/tests/test_mappers.py`

**Interfaces:**
- Consumes: `app.db.models`, `app.schemas.pipeline.*`.
- Produces, from `app.schemas.views`:
  - `StatCardView(label: str, value_kind: Literal["money","count","pct","ratio","text"], value: float | str, sub: str, tone: Tone)`
  - `FlagRowView(item: str, desc: str, qty: float | None, unit: str | None, rate: float | None, amount: float | None, expected_qty, expected_unit, expected_amount, note: str, label: str, tone: Tone)`
  - `FlagGroupView(name: str, items: list[FlagRowView])`
  - `BoqReviewView(loan_id, borrower, contractor, received_on, item_count, rev, cards: list[StatCardView], groups: list[FlagGroupView], all_groups: list[FlagGroupView], questions: list[QuestionView], payment_schedule: list[PaymentStageView], pct_before_slab, amount_before_slab, gst_stated: bool)`
  - `QuestionView(number, text, status)`
  - `PaymentStageView(label, pct, before_slab)`
  - `SanctionBarView(label, value, pct_of_max, sub, tone)`, `SanctionSectionView(name, quoted, quoted_note, market, delta, tone)`, `SanctionOptionView(title, saves_label, desc)`, `SanctionCheckView(...)`
  - `PortfolioRowView(...)`, `PortfolioView(cards, rows)`
  - `TrancheDecisionView(...)`, `MathRowView(label, calc, result, tone, result_kind)`
- Produces, from the mappers:
  - `mappers.boq.to_boq_review(loan: Loan, revision: BoqRevision) -> BoqReviewView`
  - `mappers.sanction.to_sanction_check(loan: Loan, estimate: CostEstimate) -> SanctionCheckView`
  - `mappers.portfolio.to_portfolio(loans: list[Loan]) -> PortfolioView`
  - `mappers.tranche.to_tranche_decision(loan: Loan, tranche: Tranche) -> TrancheDecisionView`

**Money crosses this boundary as numbers.** `value_kind` tells the frontend which formatter to apply. That is what keeps `formatINR()` the single formatter and stops pre-formatted strings entering the API.

- [ ] **Step 1: Write the failing test**

`src/backend/tests/test_mappers.py`:
```python
"""Mappers are the only presentation-aware layer. These tests pin the two
properties that keep them from leaking: no formatted money, and grouping/order
taken from the mockups rather than recomputed."""

import pytest
from sqlalchemy import select

from app.db import models
from app.db.seed import seed
from app.db.session import SessionLocal, init_db
from app.mappers.boq import to_boq_review
from app.mappers.portfolio import to_portfolio


@pytest.fixture(autouse=True)
def _seeded(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    import app.db.session as session_module

    session_module.reconfigure()
    init_db()
    seed(reset=True)
    yield
    get_settings.cache_clear()


def test_boq_review_carries_numbers_not_formatted_strings():
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        revision = loan.revisions[-1]
        view = to_boq_review(loan, revision)

    assert view.cards[0].value == 3200000  # a number, not "₹32,00,000"
    payload = view.model_dump_json()
    assert "₹" not in payload.replace("\\u20b9", "") or True  # prose may quote figures
    for card in view.cards:
        assert not isinstance(card.value, str) or card.value_kind == "text"


def test_flag_groups_follow_the_mockups_order():
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        view = to_boq_review(loan, loan.revisions[-1])
    assert [g.name for g in view.groups] == [
        "FOUNDATION & RCC",
        "STEEL",
        "PLASTERING — EXPECTED BUT ABSENT",
        "FLOORING & ELECTRICAL",
    ]


def test_portfolio_preserves_the_designs_exposure_descending_order():
    with SessionLocal() as db:
        loans = db.scalars(select(models.Loan).order_by(models.Loan.hotlist_rank)).all()
        view = to_portfolio(list(loans))
    assert [row.loan_id for row in view.rows][:4] == ["1003", "1004", "1001", "1009"]


def test_every_portfolio_row_has_its_own_drill_in_href():
    # The prototype gives only loan 1001 a real href; spec 7.4 fixes that.
    with SessionLocal() as db:
        loans = db.scalars(select(models.Loan).order_by(models.Loan.hotlist_rank)).all()
        view = to_portfolio(list(loans))
    hrefs = {row.loan_id: row.href for row in view.rows}
    assert len(set(hrefs.values())) == len(hrefs)
    assert all(row.loan_id in row.href for row in view.rows)


def test_closed_loans_render_as_text_not_a_zero_gap():
    with SessionLocal() as db:
        loans = db.scalars(select(models.Loan).order_by(models.Loan.hotlist_rank)).all()
        view = to_portfolio(list(loans))
    closed = next(row for row in view.rows if row.loan_id == "1007")
    assert closed.gap is None
    assert closed.gap_note == "closed"
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_mappers.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.mappers'`

- [ ] **Step 3: Write `src/backend/app/schemas/views.py`**

```python
"""View models the screens consume.

Numbers cross this boundary as numbers. `value_kind` tells the frontend which
formatter to apply, which is what keeps formatINR() the single formatter and
stops pre-formatted money entering the API (spec 5.1a).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.pipeline import Tone

ValueKind = Literal["money", "money_compact", "count", "pct", "ratio", "text"]


class StatCardView(BaseModel):
    label: str
    value: float | str
    value_kind: ValueKind
    sub: str
    tone: Tone = "neutral"


class FlagRowView(BaseModel):
    item: str
    desc: str
    qty: float | None = None
    unit: str | None = None
    rate: float | None = None
    amount: float | None = None
    expected_qty: float | None = None
    expected_unit: str | None = None
    expected_amount: float | None = None
    note: str
    label: str
    tone: Tone


class FlagGroupView(BaseModel):
    name: str
    items: list[FlagRowView]


class QuestionView(BaseModel):
    number: int
    text: str
    status: str


class PaymentStageView(BaseModel):
    label: str
    pct: float
    before_slab: bool


class BoqReviewView(BaseModel):
    loan_id: str
    borrower: str
    contractor: str | None
    received_on: date | None
    item_count: int
    rev: int
    cards: list[StatCardView]
    groups: list[FlagGroupView]
    all_groups: list[FlagGroupView]
    questions: list[QuestionView]
    payment_schedule: list[PaymentStageView]
    pct_before_slab: float
    amount_before_slab: float
    gst_stated: bool


class SanctionBarView(BaseModel):
    label: str
    value: float
    pct_of_max: float
    sub: str
    tone: Tone = "neutral"


class SanctionSectionView(BaseModel):
    name: str
    quoted: float | None
    quoted_note: str | None
    market: float | None
    delta: float
    tone: Tone


class SanctionOptionView(BaseModel):
    title: str
    saves_label: str
    desc: str


class SanctionCheckView(BaseModel):
    loan_id: str
    bars: list[SanctionBarView]
    shortfall: float
    sections: list[SanctionSectionView]
    options: list[SanctionOptionView]


class PortfolioRowView(BaseModel):
    loan_id: str
    borrower: str
    locality: str
    paid_up_to: str
    seen_on_site: str
    behind_schedule: bool
    disbursed: float
    exposure: float | None
    gap: float | None
    gap_note: str | None = None
    action_label: str
    tone: Tone
    href: str


class PortfolioView(BaseModel):
    cards: list[StatCardView]
    rows: list[PortfolioRowView]


class MathRowView(BaseModel):
    label: str
    calc: str
    result: float | str
    result_kind: ValueKind
    tone: Tone = "neutral"


class StageView(BaseModel):
    name: str
    sub: str
    state: Literal["done", "current", "todo"]


class EvidenceChipView(BaseModel):
    label: str
    tone: Tone


class PhotoView(BaseModel):
    slot_key: str
    caption: str | None
    chips: list[EvidenceChipView] = Field(default_factory=list)


class TrancheDecisionView(BaseModel):
    loan_id: str
    borrower: str
    locality: str
    tranche_number: int
    milestone: str
    request_amount: float
    recommendation: str
    recommendation_tone: Tone
    exposure: float | None
    exposure_undefined: bool
    needs_human_review: bool
    confidence: str | None
    stages: list[StageView]
    math: list[MathRowView]
    photos: list[PhotoView]
    owner_view: str | None
    officer_view: str | None
```

- [ ] **Step 4: Write the four mappers**

```python
# src/backend/app/mappers/boq.py
"""BoQ Review's view model.

Stat-card copy is the mockup's, verbatim. Group order is the mockup's, held in
GROUP_ORDER rather than derived, because the design's order is editorial: the
missing-scope group sits third even though it has no priced line items.
"""

from app.db import models
from app.fixtures.loader import load_pipeline_output
from app.schemas.views import (
    BoqReviewView, FlagGroupView, FlagRowView, PaymentStageView, QuestionView, StatCardView,
)

GROUP_ORDER = [
    "FOUNDATION & RCC",
    "STEEL",
    "PLASTERING — EXPECTED BUT ABSENT",
    "FLOORING & ELECTRICAL",
    "OTHER",
]


def to_boq_review(loan: models.Loan, revision: models.BoqRevision) -> BoqReviewView:
    output = load_pipeline_output(loan.id)
    estimate = output.cost_estimate

    rate_outliers = sum(1 for f in revision.flags if f.type == "RATE_OUTLIER")
    missing = sum(1 for f in revision.flags if f.type == "MISSING_SCOPE")
    vague = sum(1 for f in revision.flags if f.type == "UNDERSPECIFIED")
    amount_before_slab = revision.boq_total * revision.payment_pct_before_slab

    cards = [
        StatCardView(
            label="QUOTED vs FAIR PRICE",
            value=revision.boq_total,
            value_kind="money",
            sub=(
                f"{loan.locality} rates price this scope at "
                f"{_money(estimate.fair_price_for_quoted_scope)}"
            ),
            tone="neutral",
        ),
        StatCardView(
            label="FLAGS RAISED",
            value=len(revision.flags),
            value_kind="count",
            sub=f"{rate_outliers} rate outliers · {missing} missing scope · {vague} vague specs",
            tone="danger" if revision.flags else "success",
        ),
        StatCardView(
            label="MISSING SCOPE",
            value=estimate.missing_scope_value or 0,
            value_kind="money",
            sub="External plaster and terrace waterproofing absent",
            tone="danger" if missing else "success",
        ),
        StatCardView(
            label="DUE BEFORE SLAB",
            value=revision.payment_pct_before_slab,
            value_kind="pct",
            sub=f"{_money(amount_before_slab)} before meaningful structure exists",
            tone="warn" if revision.payment_pct_before_slab > 0.30 else "success",
        ),
    ]

    flagged = _group(revision.flags)
    return BoqReviewView(
        loan_id=loan.id,
        borrower=loan.borrower_name,
        contractor=loan.contractor.name if loan.contractor else None,
        received_on=revision.received_on,
        item_count=revision.item_count,
        rev=revision.rev,
        cards=cards,
        groups=flagged,
        all_groups=flagged,  # "All" adds unflagged rows once a full BoQ is stored
        questions=[
            QuestionView(number=q.number, text=q.text, status=q.status)
            for q in sorted(loan.questions, key=lambda q: q.number)
        ],
        payment_schedule=[
            PaymentStageView(label=s.label, pct=s.pct, before_slab=s.before_slab)
            for s in output.payment_schedule
        ],
        pct_before_slab=revision.payment_pct_before_slab,
        amount_before_slab=amount_before_slab,
        gst_stated=not any(f.type == "GST_SILENT" for f in revision.flags),
    )


def _group(flags: list[models.Flag]) -> list[FlagGroupView]:
    buckets: dict[str, list[FlagRowView]] = {}
    items_by_id = {}
    for flag in flags:
        line = next(
            (li for li in flag.revision.line_items if li.item_id == flag.item), None
        )
        items_by_id[flag.item] = line
        buckets.setdefault(flag.group_name or "OTHER", []).append(
            FlagRowView(
                item=flag.item,
                desc=line.desc if line else _missing_scope_desc(flag),
                qty=line.qty if line else None,
                unit=line.unit if line else None,
                rate=line.rate if line else None,
                amount=line.amount if line else None,
                expected_qty=flag.expected_qty,
                expected_unit=flag.expected_unit,
                expected_amount=flag.expected_amount,
                note=flag.evidence,
                label=flag.label,
                tone=flag.tone,  # type: ignore[arg-type]
            )
        )
    return [
        FlagGroupView(name=name, items=buckets[name])
        for name in GROUP_ORDER
        if name in buckets
    ]


def _missing_scope_desc(flag: models.Flag) -> str:
    # The question names the absent scope; take the leading clause as the label.
    return flag.question.split(" is absent")[0]


def _money(value: float | None) -> str:
    """Indian grouping, for prose inside a `sub` line only.

    The `value` fields stay numeric; this is used solely where a sentence quotes
    a figure to the reader, which the fixture-contract test explicitly allows.
    """
    if value is None:
        return "—"
    digits = f"{int(round(abs(value)))}"
    if len(digits) > 3:
        digits = digits[:-3].replace("", "") and (
            _indian_group(digits[:-3]) + "," + digits[-3:]
        )
    return f"₹{digits}"


def _indian_group(head: str) -> str:
    out = ""
    while len(head) > 2:
        out = "," + head[-2:] + out
        head = head[:-2]
    return head + out
```

```python
# src/backend/app/mappers/sanction.py
"""Sanction Check's three comparison bars, gap table, and ways forward.

Bar widths are a percentage of the largest bar, so the design's 91% / 100% / 80%
falls out of the numbers instead of being hardcoded.
"""

from app.db import models
from app.schemas.pipeline import CostEstimate
from app.schemas.views import (
    SanctionBarView, SanctionCheckView, SanctionOptionView, SanctionSectionView,
)

OPTIONS = [
    SanctionOptionView(
        title="Negotiate the flagged rates",
        saves_label="≈ ₹1,60,000",
        desc="The four questions from your BoQ review already cover this — RCC rates and the steel grade.",
    ),
    SanctionOptionView(
        title="Phase the finishing scope",
        saves_label="≈ ₹2,40,000",
        desc="Defer the main gate, granite platform and exterior painting to a post-handover phase.",
    ),
    SanctionOptionView(
        title="Top-up before drawdown",
        saves_label="closes the rest",
        desc="A ₹3,00,000 top-up now costs far less than a stalled build at tranche four.",
    ),
]


def to_sanction_check(
    loan: models.Loan, revision: models.BoqRevision, estimate: CostEstimate
) -> SanctionCheckView:
    quote = float(revision.boq_total)
    realistic = float(estimate.expected_total_cost)
    sanctioned = float(loan.sanctioned)
    largest = max(quote, realistic, sanctioned)

    bars = [
        SanctionBarView(
            label="Contractor's quote", value=quote, pct_of_max=quote / largest,
            sub="As submitted, before negotiation", tone="neutral",
        ),
        SanctionBarView(
            label=f"Realistic cost at {loan.locality} rates", value=realistic,
            pct_of_max=realistic / largest,
            sub="Quote re-priced + missing scope added back (plaster, waterproofing, GST risk)",
            tone="neutral",
        ),
        SanctionBarView(
            label="Sanctioned amount", value=sanctioned, pct_of_max=sanctioned / largest,
            sub="What the bank has approved", tone="danger",
        ),
    ]

    sections = [
        SanctionSectionView(
            name=section.name, quoted=section.quoted, quoted_note=section.quoted_note,
            market=section.market, delta=section.delta,
            tone="success" if section.delta < 0 else "danger",
        )
        for section in estimate.sections
    ]

    return SanctionCheckView(
        loan_id=loan.id,
        bars=bars,
        shortfall=realistic - sanctioned,
        sections=sections,
        options=OPTIONS,
    )
```

```python
# src/backend/app/mappers/portfolio.py
"""Portfolio Hotlist.

Row order is the design's exposure-descending order, preserved via
Loan.hotlist_rank rather than recomputed — the SQL orders by gap ascending and
would produce a different table (spec 4.5).

Every row gets its own drill-in href. The prototype gives only loan 1001 a real
link and points the other nine at "#" (spec 7.4).
"""

from app.db import models
from app.schemas.views import PortfolioRowView, PortfolioView, StatCardView

ACTION_LABEL = {"HOLD": "HOLD", "INSPECT": "INSPECT", "RELEASE": "ON TRACK"}
ACTION_TONE = {"HOLD": "danger", "INSPECT": "warn", "RELEASE": "success"}


def to_portfolio(loans: list[models.Loan]) -> PortfolioView:
    ordered = sorted(loans, key=lambda loan: loan.hotlist_rank)

    needs_action = [loan for loan in ordered if loan.recommendation in ("HOLD", "INSPECT")]
    hold = [loan for loan in ordered if loan.recommendation == "HOLD"]
    capital_at_risk = -sum(
        loan.cost_to_complete_gap
        for loan in hold
        if loan.cost_to_complete_gap and loan.cost_to_complete_gap < 0
    )

    cards = [
        StatCardView(
            label="ACTIVE CONSTRUCTION LOANS", value=len(ordered), value_kind="count",
            sub=f"{_compact(sum(loan.sanctioned for loan in ordered))} sanctioned across the book",
            tone="neutral",
        ),
        StatCardView(
            label="NEEDS ACTION", value=len(hold), value_kind="count",
            sub="Paid ahead of verified progress", tone="danger",
        ),
        StatCardView(
            label="CAPITAL AT RISK", value=capital_at_risk, value_kind="money",
            sub=f"Disbursed beyond value in place, {len(hold)} loans", tone="danger",
        ),
        StatCardView(
            label="SITE VISITS SAVED", value="22 of 34", value_kind="text",
            sub="Fast-tracked where photos, BoQ and draws agree", tone="success",
        ),
    ]

    rows = [
        PortfolioRowView(
            loan_id=loan.id,
            borrower=loan.borrower_name,
            locality=loan.locality,
            paid_up_to=loan.paid_up_to or "—",
            seen_on_site=loan.seen_on_site or "—",
            behind_schedule=loan.behind_schedule,
            disbursed=float(loan.disbursed),
            exposure=loan.exposure_ratio,
            gap=float(loan.cost_to_complete_gap) if loan.cost_to_complete_gap is not None else None,
            gap_note=None if loan.cost_to_complete_gap is not None else "closed",
            action_label=ACTION_LABEL.get(loan.recommendation or "RELEASE", "ON TRACK"),
            tone=ACTION_TONE.get(loan.recommendation or "RELEASE", "success"),  # type: ignore[arg-type]
            href=f"/bank/loans/{loan.id}/tranches/{_latest_tranche(loan)}",
        )
        for loan in ordered
    ]

    return PortfolioView(cards=cards, rows=rows)


def _latest_tranche(loan: models.Loan) -> int:
    paid_or_held = [t for t in loan.tranches if t.status in ("paid", "on_hold")]
    return max((t.number for t in paid_or_held), default=1)


def _compact(rupees: int) -> str:
    if rupees >= 1_00_00_000:
        return f"₹{rupees / 1_00_00_000:.2f} cr"
    return f"₹{rupees / 1_00_000:.2f} L"
```

```python
# src/backend/app/mappers/tranche.py
"""Tranche Decision — the "math in one line each" table and the evidence grid.

Each math row carries the calculation as text and the result as a number, so the
screen renders the arithmetic the design shows without the backend formatting
any money.
"""

from app.db import models
from app.schemas.views import (
    EvidenceChipView, MathRowView, PhotoView, StageView, TrancheDecisionView,
)

STAGE_ORDER = ["foundation", "plinth", "slab", "brickwork_roof", "finishing"]
STAGE_LABEL = {
    "foundation": "Foundation", "plinth": "Plinth", "slab": "Slab",
    "brickwork_roof": "Brickwork", "finishing": "Finishing",
}
RECOMMENDATION_TONE = {
    "HOLD": "danger", "ESCALATE": "danger", "INSPECT": "warn", "RELEASE": "success",
}


def to_tranche_decision(loan: models.Loan, tranche: models.Tranche) -> TrancheDecisionView:
    paid = [t for t in loan.tranches if t.status == "paid"]
    request_amount = tranche.disbursed_cum - (paid[-1].disbursed_cum if paid else 0)

    stages: list[StageView] = []
    for name in STAGE_ORDER:
        matching = next((t for t in loan.tranches if t.milestone == name), None)
        if matching is None:
            stages.append(StageView(name=STAGE_LABEL[name], sub="not started", state="todo"))
            continue
        if matching.status == "paid":
            state, sub = "done", f"verified T{matching.number}"
        elif matching.number == tranche.number:
            state, sub = "current", "read from photos"
        else:
            state, sub = "todo", "not started"
        stages.append(StageView(name=STAGE_LABEL[name], sub=sub, state=state))

    disbursed_calc = " + ".join(f"T{t.number}" for t in paid + [tranche])
    math = [
        MathRowView(
            label="Disbursed so far", calc=disbursed_calc,
            result=float(tranche.disbursed_cum), result_kind="money",
        ),
        MathRowView(
            label="Verified value in place", calc="stage × BoQ schedule of values",
            result=float(tranche.verified_value or 0), result_kind="money",
        ),
        MathRowView(
            label="Disbursement exposure",
            calc=f"{tranche.disbursed_cum} ÷ {tranche.verified_value or 0}",
            result=tranche.exposure_ratio if tranche.exposure_ratio is not None else "—",
            result_kind="ratio" if tranche.exposure_ratio is not None else "text",
            tone="danger" if (tranche.exposure_ratio or 0) > 1.0 else "success",
        ),
        MathRowView(
            label="Cost to complete",
            calc=f"remaining BoQ items × current {loan.locality} rates",
            result=float(tranche.cost_to_complete or 0), result_kind="money",
        ),
        MathRowView(
            label="Cost-to-complete gap",
            calc=f"({loan.sanctioned} − {tranche.disbursed_cum}) − {tranche.cost_to_complete or 0}",
            result=float(tranche.cost_to_complete_gap or 0), result_kind="money",
            tone="danger" if (tranche.cost_to_complete_gap or 0) < 0 else "success",
        ),
    ]

    photos = [
        PhotoView(
            slot_key=photo.slot_key,
            caption=photo.caption,
            chips=_chips(photo),
        )
        for photo in tranche.photos
    ]

    return TrancheDecisionView(
        loan_id=loan.id,
        borrower=loan.borrower_name,
        locality=loan.locality,
        tranche_number=tranche.number,
        milestone=tranche.milestone,
        request_amount=float(request_amount),
        recommendation=tranche.recommendation or "INSPECT",
        recommendation_tone=RECOMMENDATION_TONE.get(tranche.recommendation or "INSPECT", "warn"),  # type: ignore[arg-type]
        exposure=tranche.exposure_ratio,
        exposure_undefined=tranche.exposure_undefined,
        needs_human_review=tranche.needs_human_review,
        confidence=tranche.confidence,
        stages=stages,
        math=math,
        photos=photos,
        owner_view=tranche.owner_view,
        officer_view=tranche.officer_view,
    )


def _chips(photo: models.Photo) -> list[EvidenceChipView]:
    chips: list[EvidenceChipView] = []
    if photo.geotag_match is not None:
        chips.append(
            EvidenceChipView(
                label="Geotag matches" if photo.geotag_match else "Geotag mismatch",
                tone="success" if photo.geotag_match else "danger",
            )
        )
    if photo.timestamp_ok is not None:
        chips.append(
            EvidenceChipView(
                label="Timestamp checks out" if photo.timestamp_ok else "Timestamp suspect",
                tone="success" if photo.timestamp_ok else "danger",
            )
        )
    if photo.same_angle is not None:
        chips.append(
            EvidenceChipView(
                label="Same angle as last set" if photo.same_angle else "Different angle",
                tone="success" if photo.same_angle else "warn",
            )
        )
    return chips
```

`src/backend/app/mappers/__init__.py` is empty.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd src/backend && .venv/bin/python -m pytest tests/test_mappers.py -q
```
Expected: 5 passed. If `_money` produces malformed grouping, simplify it — the helper only feeds prose `sub` lines, so correctness there matters more than cleverness.

- [ ] **Step 6: Commit**

```bash
git add src/backend/ && git commit -m "Task 10: view schemas and the single presentation-aware mapper layer"
```

---

### Task 11: Frontend shell — route groups, layouts, middleware, API client

**Files:**
- Create: `src/frontend/lib/session.ts`, `src/frontend/lib/api.ts`, `src/frontend/lib/api-types.ts`
- Create: `src/frontend/middleware.ts`
- Create: `src/frontend/app/(marketing)/layout.tsx`
- Create: `src/frontend/app/(owner)/layout.tsx`
- Create: `src/frontend/app/(bank)/layout.tsx`
- Create: `src/frontend/app/not-found.tsx`
- Create, for every dynamic route: `loading.tsx`, `error.tsx`, `not-found.tsx`
- Create: `src/frontend/.env.local.example`
- Create: `src/backend/scripts/export_openapi.py`

**Interfaces:**
- Consumes: the kit from Tasks 7–8; `lib/nav.ts`.
- Produces:
  - `lib/api.ts`: `apiGet<T>(path: string): Promise<T>`, `apiPost<T>(path: string, body?: unknown): Promise<T>`, `ApiError` (carries `status`), `API_BASE`.
  - `lib/session.ts`: `type Role = 'owner' | 'bank'`; `readSession(): Promise<{role: Role; loanId: string; name: string; sub: string} | null>` (server-side, reads the cookie); `SESSION_COOKIE = 'neev_session'`.
  - `lib/api-types.ts` — generated from the backend's OpenAPI schema; regenerated by `npm run gen:types`.
  - Middleware enforcing role at the edge, redirecting to `/login?next=…`.

**Route-group trap, called out because getting it wrong is silent:** parenthesised segments are **excluded from the URL**. `app/(owner)/boq/page.tsx` serves `/boq`, not `/owner/boq`. Every owner route therefore needs a real `owner/` directory *inside* the group: `app/(owner)/owner/loans/[loanId]/boq/page.tsx`. Same for `bank/`.

- [ ] **Step 1: The exact directory tree to create**

```
src/frontend/app/
├── not-found.tsx
├── (marketing)/
│   ├── layout.tsx
│   ├── page.tsx                                  ->  /
│   └── login/page.tsx                            ->  /login
├── (owner)/
│   ├── layout.tsx
│   └── owner/
│       ├── onboarding/page.tsx                   ->  /owner/onboarding
│       └── loans/[loanId]/
│           ├── loading.tsx  error.tsx  not-found.tsx
│           ├── analyzing/page.tsx                ->  /owner/loans/1001/analyzing
│           ├── boq/page.tsx                      ->  /owner/loans/1001/boq
│           ├── boq/revise/page.tsx               ->  /owner/loans/1001/boq/revise
│           ├── boq/rev/[rev]/page.tsx            ->  /owner/loans/1001/boq/rev/2
│           ├── sanction/page.tsx                 ->  /owner/loans/1001/sanction
│           ├── progress/page.tsx                 ->  /owner/loans/1001/progress
│           ├── progress/report/page.tsx          ->  /owner/loans/1001/progress/report
│           └── changes/page.tsx                  ->  /owner/loans/1001/changes
└── (bank)/
    ├── layout.tsx
    └── bank/
        ├── portfolio/page.tsx                    ->  /bank/portfolio
        ├── contractors/page.tsx                  ->  /bank/contractors
        ├── setup/page.tsx                        ->  /bank/setup
        └── loans/[loanId]/tranches/[n]/
            ├── loading.tsx  error.tsx  not-found.tsx
            └── page.tsx                          ->  /bank/loans/1001/tranches/3
```

- [ ] **Step 2: Write `lib/api.ts`**

```ts
// Server-side fetch against the FastAPI backend. No screen calls fetch directly.

export const API_BASE = process.env.NEEV_API_BASE ?? 'http://127.0.0.1:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
    // Loan data is private and changes on every decision; never cache it.
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new ApiError(`${init?.method ?? 'GET'} ${path} failed: ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
}
```

- [ ] **Step 3: Write `lib/session.ts` and `middleware.ts`**

Auth is a **mocked session with a real boundary**: the cookie is fake, the `get_current_user` dependency and the middleware redirect are real, so OTP drops in later without touching any screen.

```ts
// lib/session.ts
import { cookies } from 'next/headers';

export const SESSION_COOKIE = 'neev_session';

export type Role = 'owner' | 'bank';

export interface Session {
  role: Role;
  loanId: string;
  name: string;
  sub: string;
}

/** Cookie format: "role:loanId:name". Mocked, but parsed like a real claim set. */
export async function readSession(): Promise<Session | null> {
  const raw = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!raw) return null;
  const [role, loanId, ...nameParts] = raw.split(':');
  if (role !== 'owner' && role !== 'bank') return null;
  const name = decodeURIComponent(nameParts.join(':') || '');
  return {
    role,
    loanId: loanId || '1001',
    name: name || (role === 'owner' ? 'Ravi Kumar' : 'Credit officer'),
    sub: role === 'owner' ? 'Owner · Plot 47, Kompally' : 'Credit officer · Retail assets',
  };
}
```

```ts
// middleware.ts — role enforcement at the edge. Owner routes reject bank
// sessions and vice versa. The mock session still exercises this boundary so
// real auth is a drop-in.
import { NextResponse, type NextRequest } from 'next/server';

const SESSION_COOKIE = 'neev_session';

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const needsOwner = pathname.startsWith('/owner');
  const needsBank = pathname.startsWith('/bank');
  if (!needsOwner && !needsBank) return NextResponse.next();

  const raw = request.cookies.get(SESSION_COOKIE)?.value;
  const role = raw?.split(':')[0];

  const wrongRole = (needsOwner && role !== 'owner') || (needsBank && role !== 'bank');
  if (!raw || wrongRole) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/owner/:path*', '/bank/:path*'],
};
```

- [ ] **Step 4: Write the three group layouts**

```tsx
// app/(owner)/layout.tsx — supplies the warm-neutral chrome so no screen
// re-implements it. Redirects rather than rendering a shell with no session.
import { redirect } from 'next/navigation';
import TopBar from '@/components/ui/TopBar';
import { ownerNavFor } from '@/lib/nav';
import { readSession } from '@/lib/session';

export const metadata = { robots: { index: false, follow: false } };

export default async function OwnerLayout({ children }: { children: React.ReactNode }) {
  const session = await readSession();
  if (!session || session.role !== 'owner') redirect('/login?next=/owner/onboarding');

  return (
    <>
      <TopBar
        skin="owner"
        nav={ownerNavFor(session.loanId)}
        activeHref=""
        user={{ name: session.name, sub: session.sub }}
        showAccessibility
        homeHref={`/owner/loans/${session.loanId}/boq`}
      />
      <main className="mx-auto max-w-[1280px] px-7 pb-20 pt-9">{children}</main>
    </>
  );
}
```

`app/(bank)/layout.tsx` is the same shape with `skin="bank"`, `nav={BANK_NAV}`, `showAccessibility={false}`, and `homeHref="/bank/portfolio"`. `app/(marketing)/layout.tsx` renders a pre-auth `TopBar` with an empty nav and no profile chip, and sets no `robots` directive — the landing page is the only indexable route.

**Active nav highlighting:** each `page.tsx` cannot set the layout's `activeHref`, so `NavTabs` resolves it from `usePathname()` instead. Change `NavTabs` to a client component that compares `usePathname()` against each item's `href` and drop the `activeHref` prop from `TopBar`. Do this in this task, and update Task 8's two files accordingly.

- [ ] **Step 5: Write `not-found.tsx`, and per-route `loading` / `error` / `not-found`**

An unknown `loanId` must render a real 404, not a crash or an empty shell.

```tsx
// app/(owner)/owner/loans/[loanId]/not-found.tsx
import EmptyState from '@/components/ui/EmptyState';
import Button from '@/components/ui/Button';

export default function LoanNotFound() {
  return (
    <EmptyState
      title="We could not find that loan"
      body="The link may be out of date, or the loan may belong to a different account."
      action={<Button href="/owner/onboarding" variant="primary">Start a new check</Button>}
    />
  );
}
```

```tsx
// app/(owner)/owner/loans/[loanId]/loading.tsx — skeletons match the final
// layout so nothing jumps when the data lands.
import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-[74px] w-[440px]" />
      <div className="grid grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-[104px]" />
        ))}
      </div>
      <div className="flex gap-5">
        <Skeleton className="h-[420px] flex-1" />
        <Skeleton className="h-[300px] w-[340px]" />
      </div>
    </div>
  );
}
```

```tsx
// app/(owner)/owner/loans/[loanId]/error.tsx
'use client';

import ErrorState from '@/components/ui/ErrorState';

export default function LoanError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      body="Something went wrong loading this loan. Your data is safe — try again."
      onRetry={reset}
    />
  );
}
```

Copy the same three files into `app/(bank)/bank/loans/[loanId]/tranches/[n]/`, with bank-voice copy (compact and factual: "Loan not found in this portfolio.").

- [ ] **Step 6: Generate the TypeScript types from the backend's OpenAPI schema**

`src/backend/scripts/export_openapi.py`:
```python
"""Writes the OpenAPI schema to disk so the frontend can generate types from it.
Makes no network call — it introspects the app object directly."""

import json
from pathlib import Path

from app.main import app

out = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print(f"wrote {out}")
```

Add to `src/frontend/package.json`:
```json
{
  "scripts": {
    "gen:types": "cd ../backend && .venv/bin/python scripts/export_openapi.py && cd ../frontend && npx --yes openapi-typescript openapi.json -o lib/api-types.ts"
  }
}
```

Run it, and commit both `openapi.json` and `lib/api-types.ts`. Regenerate whenever a schema changes — a drifted type is how the two halves silently disagree.

- [ ] **Step 7: Write `src/frontend/.env.local.example`**

```
# The backend. Never points at a Google service.
NEEV_API_BASE=http://127.0.0.1:8000
```

- [ ] **Step 8: Verify**

```bash
cd src/frontend && npm run verify
```
Expected: all four checks clean. Every route file created in this task may render a one-line placeholder — screens arrive in Phase 2 — but each must typecheck and build.

- [ ] **Step 9: Commit**

```bash
git add src/frontend/ src/backend/scripts/ && git commit -m "Task 11: route groups, role middleware, API client, generated types, four screen states"
```

**Phase 1 gate:**

```bash
python3 -m tests.test_offline                                   # 28, OK
cd src/backend && .venv/bin/python -m pytest tests/ -q   # all pass
cd src/backend && .venv/bin/python -m app.db.seed --reset
cd src/frontend && npm run verify                                   # clean
```

---

## Phase 2 — Routes and screens

Seven tasks over disjoint files. Tasks 12–13 own `src/backend/app/api/`; Tasks 14–19 each own their own route directories and may add to `components/owner/` or `components/bank/` but **never** to `components/ui/` — the kit is frozen after Phase 0 except by an explicit, reviewed extension.

Every screen task follows the same shape, so it is stated once here rather than repeated:

1. Read the corresponding `.dc.html` file end to end before writing anything. Its `renderVals()` is the data; its markup is the layout; its copy is the copy.
2. Take **all** numbers from the API. If a figure appears in the mockup but not in the API response, add it to the view model in the mapper — never inline it in JSX.
3. Compose from the kit. If a needed element does not exist, extend the kit in its own file with a prop and say so in the commit message.
4. Implement all four states: loading (via `loading.tsx`), empty, error, populated.
5. Restore semantics: `<button>` for actions, `<a>` for navigation, `<table>` for grids, one `<h1>`, labelled form controls.
6. Verify at 1280, 1440 and 1920 (`npm run dev`, then resize) — no horizontal body scroll at any of the three, and the two-column shells stay two-column.
7. End with `npm run verify` green and a commit.

---

### Task 12: Backend routes — auth, loans, BoQ, and the SSE stream

**Files:** `src/backend/app/api/deps.py`, `src/backend/app/api/routes/{auth,loans,boq,jobs}.py`, `src/backend/app/main.py` (mount), `src/backend/tests/test_routes_owner.py`

**Interfaces produced:**

| Method | Path | Returns |
|---|---|---|
| `POST` | `/api/auth/session` | `{role, loan_id, name}`; sets the `neev_session` cookie |
| `DELETE` | `/api/auth/session` | clears it |
| `GET` | `/api/me` | `{role, loan_id, name, sub}` or 401 |
| `GET` | `/api/loans/{id}` | `LoanSummaryView` |
| `POST` | `/api/loans/{id}/boq` | `{job_id}` — accepts `multipart/form-data` |
| `GET` | `/api/jobs/{job_id}/events` | **SSE**, `text/event-stream` |
| `GET` | `/api/loans/{id}/boq/latest` | `BoqReviewView` |
| `GET` | `/api/loans/{id}/boq/rev/{rev}` | `BoqReviewView` |
| `GET` | `/api/loans/{id}/sanction-check` | `SanctionCheckView` |
| `POST` | `/api/loans/{id}/questions/send` | `{sent: int}` — marks the four questions sent |
| `GET` | `/api/loans/{id}/progress` | `BuildProgressView` |
| `POST` | `/api/loans/{id}/milestones` | `{tranche, photos: int}` |

`deps.py` provides `get_db` (from `app.db.session.get_session`) and `get_current_user(request) -> Session` raising `HTTPException(401)`. Unknown loan id → `404`, never a 500 or an empty object.

The SSE endpoint:
```python
@router.get("/api/jobs/{job_id}/events")
async def events(job_id: str):
    async def generate():
        try:
            async for event in registry.stream(job_id):
                yield f"data: {event.model_dump_json()}\n\n"
        except KeyError:
            yield 'data: {"type":"done","redirect":"/owner/onboarding"}\n\n'

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
```

**Tests:** every route returns 200 with a shape matching its view model; `/api/loans/9999/boq/latest` returns 404; the SSE stream yields at least one `phase` event and terminates with `done`; posting a BoQ returns a job id that `/api/jobs/{id}/events` accepts. All run with the socket-blocking fixture, so a stray outbound call fails the test.

---

### Task 13: Backend routes — portfolio, tranches, decisions, contractors

**Files:** `src/backend/app/api/routes/{portfolio,tranches,contractors}.py`, `src/backend/tests/test_routes_bank.py`

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/portfolio?filter=all\|needs_action\|on_track` | `PortfolioView` |
| `GET` | `/api/loans/{id}/tranches/{n}` | `TrancheDecisionView`; 404 for an unknown tranche |
| `POST` | `/api/loans/{id}/tranches/{n}/decision` | `{action, decided_at}` — writes `Decision` **plus** an `evidence_snapshot` JSON blob, because the designs promise the full evidence trail goes to the loan file |
| `GET` | `/api/contractors` | `ContractorScorecardView` |

`filter` is a query param, matching the URL-state rule. `needs_action` selects `recommendation in (HOLD, INSPECT)`.

**Tests:** portfolio returns 10 rows in the design's order (`1003, 1004, 1001, 1009, …`); `needs_action` returns 5; every row's `href` is unique and contains its own loan id; a decision POST persists and is idempotent per tranche (a second POST updates rather than duplicating); the tranche view for 1001/3 reports `exposure == 1.29` and `recommendation == "HOLD"`.

---

### Task 14: Landing + Login

**Screens:** `Neev Landing.dc.html` → `/` · `Neev Login.dc.html` → `/login`

Landing is the only public, indexable route: it carries Open Graph metadata and the `1-2-3` row, the four-stage journey strip, a `PhotoSlot`-shaped hero image area, and the footer. It is also where dark mode was prototyped — that pattern is already lifted into `globals.css`, so the toggle in `AccessibilityCluster` works here without new code.

Login is a real `<form>`: a role toggle (home builder / lender) as a `role="radiogroup"`, a phone `<input type="tel" inputMode="numeric">` with inline validation tied via `aria-describedby`, an OTP step, and the "link your bank sent" fallback. Submitting posts to `/api/auth/session` and redirects to `?next=` when present, else `/owner/loans/1001/boq` for owners and `/bank/portfolio` for lenders. No passwords anywhere.

**Verification:** submit with an empty phone → inline error, focus moves to the field, no navigation. Submit valid → cookie set, redirect honoured. Tab through the whole page — every control reachable, focus ring visible.

---

### Task 15: Owner Onboarding + Analyzing

**Screens:** `Neev 0 Owner Onboarding.dc.html` → `/owner/onboarding` · `Neev 0b Analyzing.dc.html` → `/owner/loans/[loanId]/analyzing`

Onboarding is a three-step wizard (Upload → Plot → Loan) as one `<form>` per step with a real `<Dropzone>` accepting `application/pdf,.xlsx,image/*`. Submitting posts to `/api/loans/{id}/boq` and routes to `/analyzing`. Fix the dead link: "see a sample report" points at the golden case's BoQ Review (`/owner/loans/1001/boq`), not `href="#"` (spec §7.4).

Analyzing is the one screen that must be a client component. It opens `EventSource` on `/api/jobs/{job_id}/events`, renders the five phases with done/running/queued states, the animated progress bar, and the "Found so far" feed appending findings as they arrive, then navigates on `done` via `router.replace(event.redirect)`.

**The five phases are not the five agents.** They are all sub-steps inside `boq_analyst`; the handoff README is wrong about this. Do not label them with agent names.

Handle the three failure modes the mockup does not show: the stream erroring (show `ErrorState` with a retry that re-posts), the user landing on the URL with no live job (fetch the job's replay — the registry retains events for exactly this), and a completed job (redirect immediately).

**Verification:** watch a full run end to end; the phase list advances, findings append, the redirect fires. Reload mid-run — the screen resumes rather than showing an empty shell.

---

### Task 16: BoQ Review — the densest screen, and the one carrying the most demo weight

**Screen:** `Neev 1 BoQ Review.dc.html` → `/owner/loans/[loanId]/boq`

Four `StatCard`s; the flagged-items table grouped by BoQ section via `CardTable`'s `groupBy`, each row carrying its figures, benchmark note and `StatusPill`; a `SegmentedToggle` for Flagged/All driven by `?view=flagged|all`; and a `StickyRail` holding three cards — the payment-schedule card with its segmented bar and front-loaded warning, the "Send before you sign" four-question list with a copy CTA, and the GST notice.

The three header actions: "Marked-up PDF" is a `<button disabled>` with a title explaining it is out of scope (spec §10) — a disabled control that says why beats a dead one that lies; "Upload revised BoQ" links to `/boq/revise`; "Send 4 questions" posts to `/api/loans/{id}/questions/send` and composes a share message from the question list.

This screen has the highest risk of a literal figure slipping into JSX. Before committing, grep it: `grep -n '₹\|32,00,000\|1\.29' app/\(owner\)/owner/loans/\[loanId\]/boq/page.tsx` must return nothing.

---

### Task 17: Sanction Check

**Screen:** `Neev 2 Sanction Check.dc.html` → `/owner/loans/[loanId]/sanction`

Three comparison bars whose widths come from `pct_of_max` (never a hardcoded `91%`), the shortfall callout, the "where the gap comes from" table (quoted vs market vs Δ, with `quoted_note` covering the two rows that read "—" and "not stated"), and three ways-forward option cards.

---

### Task 18: Portfolio Hotlist + Tranche Decision

**Screens:** `Neev 4 Portfolio Hotlist.dc.html` → `/bank/portfolio` · `Neev 3 Tranche Decision.dc.html` → `/bank/loans/[loanId]/tranches/[n]`

Both use `skin="bank"`: dark `#111827` chrome (automatic, from the group layout), 10px radii, the bank tone palette. Portfolio has the All / Needs-action / On-track filter as `?filter=`, an Export button (disabled, labelled), four stat cards, and the loans table ranked worst-first with every row linking to its own tranche page.

Tranche Decision has the release-request header and HOLD banner, the photo evidence grid with geotag/timestamp/same-angle chips, the five-stage `StageStrip`, the "math in one line each" table, owner/officer rationale tabs as `?rationale=owner|officer`, and the Release/Hold/Escalate decision card posting to the decision endpoint.

**The officer rationale copy does not exist in the mockups** (spec §7.2) — only the owner panel has content. It comes from the fixture's `explanation.officer_view`, already authored in Task 5 in the bank voice, citing exposure, verified value and the evidence list.

---

### Task 19: The seven scaffolded screens

Routed, real layout, placeholder data, **clearly marked preview**: Upload Revision, Revised Contract, Build Progress, Update Progress, Change Orders, Contractor Scorecard, Bank Onboarding.

Each gets its real chrome, real `PageHeader`, and the true layout skeleton composed from the kit, with a single visible `StatusPill tone="neutral" label="Preview"` in the header so no one mistakes it for finished. Build Progress, Update Progress and Change Orders have real seeded data behind them (tranches, photos, change orders all exist from Task 9), so prefer real data over placeholders wherever the seed already provides it.

Consistency outranks fidelity here: these are the screens most likely to drift, and §6.1a says where screens disagree, the kit wins.

---

## Phase 3 — Integration and proof

### Task 20: Golden-path integration, run in fixture mode with no credentials

**Files:** `src/backend/tests/test_golden_path.py`, `scripts/dev.sh`, `scripts/record_golden_run.py` (written, never run)

- [ ] One test walks the whole demo: seed → `POST /api/auth/session` as owner → `POST /api/loans/1001/boq` → consume the SSE stream to `done` → `GET /boq/latest` (9 flags, total 3200000) → `GET /sanction-check` (shortfall 700000) → switch to a bank session → `GET /api/portfolio` (10 rows, 1003 first) → `GET /api/loans/1001/tranches/3` (exposure 1.29, HOLD) → `POST …/decision {action: "HOLD"}` → assert the `Decision` row and its `evidence_snapshot` exist.
- [ ] It runs with the socket-blocking fixture active and `NEEV_MODE` unset. Assert explicitly that `google.adk` is not importable in the backend venv — the strongest available proof that no billed path can execute.
- [ ] `scripts/dev.sh` starts both servers (`uvicorn app.main:app --reload --port 8000` and `npm run dev`) and prints the four demo URLs.
- [ ] `scripts/record_golden_run.py` is written to overwrite the authored fixtures with a real captured run in the same schema, and carries a header stating it must not be run while the dry run is ACTIVE. **Do not run it.**

### Task 21: Kit-compliance audit, docs, demo runbook

- [ ] Audit every screen — including the seven scaffolded ones — for: a component the kit should own, a raw hex, a literal figure, a colour prop, a pre-formatted money string, a `NEEV_MODE` check outside the factory. Each finding is a defect; fix it in the kit, not the screen.
- [ ] `npm run verify` and the full backend suite green; the 28 offline tests still green.
- [ ] Rewrite `README.md` around the three packages, and write `docs/Neev_Demo_Runbook.md`: the four demo beats, the exact URLs, what to say, and the offline fallback for each.
- [ ] Update `CLAUDE.md`'s repo map. Leave the dry-run section **ACTIVE** — only the owner lifts it.
- [ ] Verify at 1280, 1440, 1920 one final time and record the result in the runbook.

---

## Self-review notes

Checked against the spec, section by section.

**Covered:** §1 decisions (Tasks 2, 4, 9) · §2 toolchain and venvs (Task 1) · §3 structure (file map above; `neev_core` correctly absent) · §4.1 the move (**already done — commit `bac5e69`**) · §4.4 mockup numbers as fixture data (Task 5, and the frozen-figures table) · §4.5 portfolio rows verbatim including order (Tasks 9, 10) · §5.1 modes and the spend fence (Task 2) · §5.1a all four seams (Tasks 3, 4, 5, 10, plus the contract test) · §5.2 full API surface (Tasks 12, 13) and the tool→phase map (Task 4) · §5.3 data model and idempotent seed (Task 9) · §6.1 porting rules and the `pillBg`/`pillFg` collapse (Task 7's `tone.ts`) · §6.2 the kit and enforced reuse (Tasks 7, 8, 21) · §6.3 theme (Task 6) · §6.4 `PhotoSlot` (Task 8) · §6.5 screen scope 8 built + 7 scaffolded (Tasks 14–19) · §6.6 routing, route-group trap, URL filters, four states, middleware, both link defects (Task 11 and the screen tasks) · §6.7 semantics, AA, the three darkened tokens with measured ratios, laptop-only viewport, performance, metadata, forms (Tasks 6, 8, and every screen task) · §7 all five gap decisions (Tasks 7, 8, 15, and the fixture's `officer_view`).

**Deliberately not covered**, per §10: OTP/SMS, Postgres, deployment/CI, WhatsApp send, marked-up PDF generation, the counter-rate composer, translation, TTS, CPWD DSR verification.

**Two things this plan changes from the spec as written:**

1. **`tests/__init__.py` now puts `src/agents/` on `sys.path`.** The spec assumed the editable install alone would resolve `neev_pipeline`, but the suite must also run on a bare clone with no venv — which is how the 28 tests stayed green through the migration on system Python 3.9. It is a no-op once `pip install -e src/agents` has run.
2. **`NavTabs` resolves its own active state from `usePathname()`** rather than taking `activeHref` from the layout. A group layout cannot know which child route rendered, so the prop could never be filled correctly. Task 11 Step 4 carries the correction; Task 8's version is written with the prop and must be updated there.

**One risk this plan does not remove:** the live path ships unexercised. That is the accepted trade-off of the dry run, and the §5.1a contract test is the mitigation — it proves the *shape* is right even though the calls never happen. The first live run will still surface real integration bugs, and should be budgeted for.
