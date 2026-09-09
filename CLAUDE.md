# Neev — working agreements

## ✅ DRY RUN: LIFTED

**Status: LIFTED 2026-09-09 by the repo owner**, in their words: "we can spend
the credits now, its fine, so remove the guardrails and prepare it to go to
live and we have to use agents as well."

Gemini completions and vision, the ADK pipeline, and `gcloud run deploy` are all
permitted now. `GOOGLE_API_KEY` is restored in `.env` (the value came from
`.env.disabled-backup`, which stays git-ignored).

What that changes, and what it does not:

| Operation | Status |
|---|---|
| Gemini completions and vision, `adk web`, `scripts/golden_run.py`, `record_golden_run.py` | **Permitted.** Each full pipeline run costs about ₹3.81 — see `docs/Neev_Two_Week_Plan.md`. Say what a run will cost before making it, and do not run the pipeline in a loop without asking. |
| **A pipeline run while the key is on the free tier** | **Budget it like a scarce resource, because it is.** The free tier allows 20 `generateContent` requests per day *per model*, and one analysis is five agents plus tool round-trips — roughly **two analyses a day**. Spending them on a debugging loop leaves none for a demo. Check `https://ai.dev/rate-limit` before running, and prefer `--from-raw` replay (free) for anything that is not specifically testing the live path. |
| BigQuery reads and `bq load` on this project's own tables | **Permitted.** Kilobytes, inside the free tier. |
| `gcloud` read-only and metadata commands | **Permitted.** |
| **`gcloud run deploy`** | **STILL GATED. The owner approves every one.** Two free deploys existed for this hackathon and `scripts/deploy_cloudrun.sh` spends both in a single invocation (backend, then frontend). A third costs money. Never run it unasked. |
| Anything that deletes or rewrites cloud state — `bq rm`, dropping a dataset, deleting a service | **GATED.** Ask first. Reversibility is the test, not cost. |

### Rules

1. **`NEEV_MODE=live` needs `NEEV_ALLOW_BILLED_CALLS=1`** and a key in the
   environment. That belt-and-braces check stays: it is what stops a stray
   `NEEV_MODE=live` in a shell from billing, and `get_runner` is still the only
   place that reads the mode.
2. **Tests must never reach the network**, unchanged and non-negotiable. Follow
   `tests/test_offline.py`, which stubs the Google libraries in `sys.modules`
   and runs with no credentials. A test that bills is a test that bills on every
   CI run, forever. The socket-blocking fixture in
   `src/backend/tests/conftest.py` is autouse for the same reason.
3. **A deployment uses Vertex AI, not the Gemini API key**, and that is a cost
   decision. The Gemini API's free tier allows 20 `generateContent` requests per
   day per model — about two analyses — and lifting it means putting a card on
   an AI Studio account. Vertex runs the same models, authenticates as the Cloud
   Run service account, and bills the project's Cloud Billing account, which is
   where the hackathon credits are. Three env vars and no code change:
   `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`,
   `GOOGLE_CLOUD_LOCATION`. Proven on 2026-09-09: 40 line items, 30 flags, no
   parse errors, 161s.
4. **The API key never enters git.** It lives in `.env` (git-ignored) for local
   work, and in Secret Manager if anyone deploys with
   `NEEV_GENAI_BACKEND=apikey` — never in `--set-env-vars`, where it would sit
   in the service's config and in `gcloud` output.
5. **Live mode is exercised now, not shipped unexercised.** The path in
   `app/services/live_runner.py` was written and type-checked but never run
   under the dry run; it has been run since this section was lifted. If you
   change it, run it.
6. **A deployed live service is capped**, and the cap is not optional.
   `NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY` (12) and `NEEV_MAX_ANALYSES_PER_DAY`
   (60) exist because the demo is `--allow-unauthenticated` and its sign-in
   accepts any ten-digit number, so on the paid tier nothing else stands
   between a crawler and the billing account. Raise them deliberately, never
   to zero.
7. The backend venv and image now carry `google-adk`, `google-genai` and
   `neev-pipeline`, because the live runner imports them at call time. Fixture
   mode still touches none of them: the imports are inside the method body, and
   `test_no_google_import_at_module_scope` keeps them there.

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
- `docs/Neev_Demo_Runbook.md` — how to run and narrate the demo; start here
- `scripts/dev.sh` — starts both servers, seeded, in fixture mode

## State of the build (2026-08-28)

Phases 0-2 of the plan are complete and merged: all 21 tasks except the final
polish. The backend serves 17 API paths; the frontend serves 17 routes covering
all 15 handoff screens. Verify with:

```bash
python3 -m tests.test_offline                             # 28
cd src/backend && .venv/bin/python -m pytest tests/ -q    # 154
cd src/frontend && npm run verify                         # 4 checks
```

The mapper layer (`src/backend/app/mappers/`) is the only presentation-aware
code, and `app/services/runner.py::get_runner` is the only place that reads
`NEEV_MODE`. Both properties are load-bearing — keep them. The second is now
enforced by `test_no_service_but_the_runner_factory_reads_the_mode`; a runner
declares its own `mode` so callers can record provenance without a second check.

`app/services/pipeline_parse.py` turns raw ADK session state into a
`PipelineOutput` — the spec §4.3 layer, no longer deferred. Both the live runner
and `scripts/record_golden_run.py` go through it, which is what keeps a live run
and a recorded one from drifting apart. It imports no Google library, so it is
fully testable offline: `record_golden_run.py` saves raw state to `.golden_runs/`
*before* parsing, and `--from-raw` replays a saved capture for free. One billed
run, then as many parse iterations as it takes.
