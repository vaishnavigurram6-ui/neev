# Neev — working agreements

## 🚫 DRY RUN: no billed Google API calls (ACTIVE)

**Status: ACTIVE as of 2026-08-27. Only the repo owner may lift it.**

While this section says ACTIVE, nothing in this repo may consume Google credits.
That means **no** Gemini completions, **no** Gemini vision calls, and **no**
BigQuery queries — not in the app, not in tests, not in a "quick check", and not
to record a fixture.

`GOOGLE_API_KEY` in `.env` is deliberately commented out (`#[DRY-RUN DISABLED …]`).
The original value is kept locally in `.env.disabled-backup`, which is git-ignored.

### Rules

1. **Do not uncomment, restore, export, or otherwise reinstate `GOOGLE_API_KEY`.**
   Not to debug, not to verify, not "just once". Only the owner re-enables it.
2. **Never run** `adk web`, `scripts/golden_run.py`, `scripts/load_bigquery.sh`,
   or any `bq` command. These all hit billed services.
3. **The backend runs in `NEEV_MODE=fixture`** — the default. Live mode also
   requires `NEEV_ALLOW_BILLED_CALLS=1`, which must never be set while this
   section is ACTIVE.
4. **Tests must not reach the network.** Follow the pattern in
   `tests/test_offline.py`, which stubs the Google libraries in `sys.modules` and
   runs with no credentials at all.
5. Live-mode code may still be **written and type-checked** — it just is never
   **executed**. It ships unexercised by design; the owner validates it in Cloud
   Shell once credits are approved.

### To lift the dry run (owner only)

Uncomment the key in `.env` (or restore `.env.disabled-backup`), then change this
section's status to LIFTED with the date. Until that edit exists in this file,
assume it is ACTIVE.

---

## Git identity

Commits here are authored as **Vaishnavi Gurram <vaishnavigurram6@gmail.com>**,
never the machine's global work identity. This is already set in the repo-local
`.git/config`, and the remote is pinned to `vaishnavigurram6-ui@github.com` so
credentials resolve to that account. Verify with `git config user.email` before
committing. Never modify the global git config.

## Environments

Python 3.11 per package, each in its own venv (`src/agents/.venv`,
`src/backend/.venv`) —
never install into system Python, which is 3.9.6 and too old for `google-adk`.
Frontend uses `npm`.

## Where things are

- `src/` — the three code packages: `src/agents/` (ADK pipeline, was
  `buildguard/`), `src/backend/` (FastAPI), `src/frontend/` (Next.js).
  `adk web` runs from `src/agents/` and discovers `neev_pipeline.agent.root_agent`. The GCP project
  `buildguard-ai-2026` and BigQuery dataset `buildguard_data` keep those names —
  only the Python package was renamed.
- `docs/superpowers/specs/` — design specs; the current one is
  `2026-08-27-neev-app-restructure-design.md`
- `docs/superpowers/plans/` — implementation plans; the current one is
  `2026-08-28-neev-app-restructure-plan.md` (21 tasks, 3 phases). Task 1's
  toolchain step and the whole pipeline relocation are already done; the plan's
  "Global Constraints" section is binding on every task.
- `design_handoff_neev/` — 16 hi-fi screen prototypes plus a build-notes README
- `fixtures/` — golden-case data: loan 1001 (Ravi, flagged) and 1002 (clean)
- `tests/test_offline.py` — 28 checks, no credentials, no network, ~0.002s
