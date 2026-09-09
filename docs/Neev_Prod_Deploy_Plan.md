# Neev — production deploy plan

*Written 2026-09-10 for the single-shot Cloud Run deploy. Every claim below was
checked against this repository and against the live `buildguard-ai-2026`
project on 2026-09-10 with read-only commands. Where a doc and the code
disagree, the code wins and the disagreement is listed in §7.*

**The one thing that shapes this document:** `scripts/deploy_cloudrun.sh` makes
**two** `gcloud run deploy` calls, and only **two** free deploys exist. One run
of the script spends both. There is no second attempt and there is no previous
revision to roll back to. Everything that can be checked is checked in §1,
before anything is spent.

---

## 0 · State of play, verified 2026-09-10

| Fact | Value | How it was checked |
|---|---|---|
| Project | `buildguard-ai-2026`, number `516665930454`, ACTIVE | `gcloud projects describe` |
| Active account | `vaishnavigurram6@gmail.com`, `roles/owner` | `gcloud config list`, `get-iam-policy` |
| Region | `asia-south1` (script default) | `scripts/deploy_cloudrun.sh:42` |
| Cloud Run services | **none exist** — both free deploys are unspent | `gcloud run services list` returned empty |
| Artifact Registry | `cloud-run-source-deploy`, DOCKER, `asia-south1`, 110 MB, created 2026-09-09 17:07 UTC | `gcloud artifacts repositories describe` |
| BigQuery dataset | `buildguard_data` in `asia-south1` — same region as Cloud Run | `bq show` |
| `rate_benchmarks` | **62 rows**, last modified 2026-09-07 15:15 UTC | `bq show`; `fixtures/rate_benchmarks.csv` has 62 data rows + header |
| Offline suite | **60 tests**, 0.005 s | `python3 -m tests.test_offline` |
| Backend suite | **228 passed**, 22 s | `src/backend/.venv/bin/python -m pytest tests/ -q` |
| Frontend verify | clean; 17 routes built | `cd src/frontend && npm run verify` |

Two consequences worth saying out loud:

- The `rate_benchmarks` reload that `docs/Neev_Two_Week_Plan.md` still lists as
  an open item **is done**. 62 rows in BigQuery, 62 in the CSV. Nothing to do.
- The site photographs that the same doc lists as missing **ship in the image**.
  They moved from the git-ignored `demo_assets/` to `fixtures/site_photos/`
  (4 tracked JPEGs), and the root `Dockerfile` does `COPY fixtures /app/fixtures`.
  Beat 4's visual evidence will be there.

---

## 1 · Pre-flight — everything that must be true before the first deploy

`scripts/deploy_cloudrun.sh` already runs checks 1–4 itself and exits non-zero
before its first `gcloud run deploy`. They are listed anyway so you know what it
is doing and can see the results in advance.

### Already done — verified today, no action needed

| # | Must be true | Verify with | Result 2026-09-10 |
|---|---|---|---|
| 1 | `run`, `cloudbuild`, `artifactregistry` enabled | `gcloud services list --enabled --project buildguard-ai-2026 \| grep -E '^(run\|cloudbuild\|artifactregistry)'` | all three enabled |
| 2 | `aiplatform.googleapis.com` enabled (Vertex is the live backend) | `gcloud services list --enabled --project buildguard-ai-2026 \| grep '^aiplatform'` | enabled |
| 3 | Runtime/build SA can build and push | `gcloud projects get-iam-policy buildguard-ai-2026 --flatten='bindings[].members' --filter="bindings.members:516665930454-compute@developer.gserviceaccount.com" --format='value(bindings.role)'` | `roles/cloudbuild.builds.builder` present |
| 4 | Same SA can call Vertex AI | same command as #3 | `roles/aiplatform.user` present |
| 5 | Same SA can read BigQuery (the analysts' benchmark lookups) | same command as #3 | `roles/bigquery.jobUser` **and** `roles/bigquery.dataViewer` present |
| 6 | Artifact Registry repo exists in the deploy region | `gcloud artifacts repositories describe cloud-run-source-deploy --project buildguard-ai-2026 --location=asia-south1` | exists, 110 MB |
| 7 | `rate_benchmarks` in BigQuery matches the CSV aliases | `bq show --format=prettyjson buildguard-ai-2026:buildguard_data.rate_benchmarks \| grep numRows` and `wc -l fixtures/rate_benchmarks.csv` | 62 vs 62+header — matched |
| 8 | Dataset and Cloud Run are in the same region | `bq show --format=prettyjson buildguard-ai-2026:buildguard_data \| grep location` | both `asia-south1` |
| 9 | No service exists yet, so no deploy has been spent | `gcloud run services list --project buildguard-ai-2026` | empty |

Note on #5: `roles/bigquery.*` is **only checked by the script on the API-key
path** (`deploy_cloudrun.sh:138-155`). On the Vertex path the script skips it —
but the pipeline still queries BigQuery on every live analysis. The bindings are
present, so this is moot today. It is a gap in the preflight, not in the project.

### Still to do — the morning of the deploy

| # | Must be true | Do / verify with |
|---|---|---|
| 10 | All three suites green **on the tree you are about to upload** | `python3 -m tests.test_offline` → 60 · `cd src/backend && .venv/bin/python -m pytest tests/ -q` → 228 · `cd src/frontend && npm run verify` → clean |
| 11 | **Decide what to do about the uncommitted work.** `--source` uploads the *working tree*, not `HEAD`, so anything dirty ships. The tree is **actively growing** — it changed twice while this plan was being written. As of 2026-09-10 it carried `M src/backend/app/fixtures/portfolio_rows.json` (adds `built_up_sqft: 2450` to 1003/1004) plus untracked `loan_1003/1004/1006_pipeline.json` and their `.golden_runs/` captures. Each new `loan_NNNN_pipeline.json` makes that loan fixture-covered (`loader.available_loan_ids()` globs the directory), but `app/api/accounts.py` still offers only `ravi`/`prasad`/`officer` — so a new fixture adds data no account can reach. | `git status --short` immediately before deploying, and read the list yourself. Then either commit so the deployed build is reproducible from git, or `git stash` so it is not. Do **not** leave it undecided, and do not trust the file list above — re-run the command. |
| 12 | Both containers actually build and serve. **Neither Dockerfile has ever been built in CI.** This is the stage that protects the two deploys, and it is free and unlimited. | `docker build -t neev-api .` · `docker build -t neev-web src/frontend` · `docker run -d --name api -p 8080:8080 neev-api` · `curl -fsS http://localhost:8080/api/health` → `{"status":"ok","mode":"fixture"}` · `docker run -d --name web -p 3000:8080 -e NEEV_API_BASE=http://host.docker.internal:8080 neev-web` · `curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:3000/` → 200 |
| 13 | Confirm what will be uploaded to Cloud Build. There is **no `.gcloudignore`** in the repo; gcloud generates one from `.gitignore` at deploy time. Verified today: 343 files for the backend context, 133 for the frontend, **zero** `node_modules` / `.venv` / `.next` entries. | `gcloud meta list-files-for-upload . \| wc -l` → 343 · `gcloud meta list-files-for-upload . \| grep -cE 'node_modules\|\.venv'` → 0 · `gcloud meta list-files-for-upload src/frontend \| wc -l` → 133. This command does **not** write `.gcloudignore`; `gcloud run deploy` **will**, in the repo root and in `src/frontend`. Expect two new untracked files afterwards. |
| 14 | Pick and record `NEEV_SESSION_SECRET` **yourself**. If you let the script generate it, you cannot reproduce it, and any later `--set-env-vars` that omits it signs every visitor out. | `openssl rand -hex 32` → paste into a note, then `export NEEV_SESSION_SECRET=<that value>` |
| 15 | Decide the demo password. **The runbook's documented override does not work** — see §7.1. The deployed password will be `neev-demo` unless you add `NEEV_DEMO_PASSWORD` to the gcloud command by hand. | Either accept `neev-demo` (it is already printed in `docs/Neev_Demo_Runbook.md`, which is the intent) or use the hand-written invocation in §2.3 |
| 16 | Decide the model. `NEEV_GEMINI_MODEL` is **not** passed by the deploy script, so the image runs `neev_pipeline/config.py`'s default `gemini-3.7-flash`. If that model id is not served on Vertex in the `global` location, every live analysis fails and you cannot change it without touching the service. | If you want an escape hatch, add `NEEV_GEMINI_MODEL=gemini-3.7-flash` to the env explicitly (§2.3) so a later `--update-env-vars` is an edit rather than an addition |
| 17 | Warm-up plan agreed: someone hits both URLs a minute before presenting | see §3 step 0 |

---

## 2 · The deploy

### 2.1 · What the script resolves to

Read from `scripts/deploy_cloudrun.sh` as it stands. Nothing below is inferred.

| Variable | Value | Why |
|---|---|---|
| `NEEV_DEPLOY_SANDBOX` | must be `1` or the script refuses at line 35 | Explicit acknowledgement that this build has demo login and ephemeral data |
| `PROJECT` | `buildguard-ai-2026` | |
| `REGION` | `asia-south1` | Same region as the BigQuery dataset; Hyderabad-adjacent |
| `BACKEND` / `FRONTEND` | `neev-api` / `neev-web` | |
| `MODE` | `live` (default) | `NEEV_MODE=live` drives the real five-agent ADK pipeline on whatever is uploaded |
| `GENAI_BACKEND` | `vertex` (default) | The Gemini API free tier is 20 `generateContent` requests/day/model ≈ two analyses; Vertex has no such cap, authenticates as the service account (no key to leak) and bills the Cloud Billing account where the hackathon credits sit |
| `VERTEX_LOCATION` | `global` | Vertex's multi-region endpoint. Harmless for BigQuery: `google-cloud-bigquery` does not read `GOOGLE_CLOUD_LOCATION` (verified by grep) and the dataset resolves its own `asia-south1` location |

### 2.2 · Backend environment, every variable and why

`NEEV_MODE=live`
: Selects `AdkPipelineRunner` in `app/services/runner.py::get_runner` — the only
  place in the codebase that reads the mode. Any unrecognised value falls back
  to `fixture`, on purpose, so a typo cannot spend money.

`NEEV_ALLOW_BILLED_CALLS=1`
: A second, independent gate. `assert_billed_calls_permitted` raises without it,
  so `NEEV_MODE=live` alone is inert. Set only because live is intended here.

`NEEV_DEMO_AUTH=true`
: Without it `POST /api/auth/session` returns 403 ("a verified identity provider
  is required") and `GET /api/auth/accounts` returns `[]` — the login screen
  would list nothing and accept nobody. The deployment is unusable without it.

`NEEV_SESSION_SECRET=<32 bytes hex>`
: Signs the session cookie. Empty means a random key per process, and any
  instance replacement then bounces every signed-in visitor to `/login` with a
  cookie signed by a key that no longer exists. Set it, and write it down.

`GOOGLE_CLOUD_PROJECT=buildguard-ai-2026`
: Read by `neev_pipeline/config.py:8` (`PROJECT_ID`) and by `bigquery.Client()`
  and `genai.Client()`, neither of which is passed a project explicitly.

`GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_LOCATION=global`
: Moves `google-genai` — and therefore every ADK agent built on it — to Vertex
  with no code change. Only set when `MODE=live` and `GENAI_BACKEND=vertex`.

`NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY=12` and `NEEV_MAX_ANALYSES_PER_DAY=60`
: The only thing between a public `--allow-unauthenticated` URL and the billing
  account. Enforced in `app/api/routes/boq.py::_refuse_if_over_the_daily_cap`,
  which counts analyses **started** (a run that 503s halfway already paid for
  the agents that answered) and returns 429 with reader-facing copy. Generous
  enough that a judge working the flow never meets them.

Not set, and therefore taking their defaults from `app/core/settings.py`:
`NEEV_DEMO_PASSWORD` = `neev-demo`; `DATABASE_URL` = `sqlite:///./neev.db`;
`ARTIFACT_DIR` = `./artifacts`; `CORS_ORIGINS` = localhost (irrelevant — every
call is a server-to-server hop inside Cloud Run, see §2.4).

### 2.3 · The invocation

**Recommended — the script, because it holds the preflight and the mid-flight
health gate:**

```bash
cd /Users/mohithkumar/Documents/Neev/neev
export NEEV_DEPLOY_SANDBOX=1
export NEEV_SESSION_SECRET=<the hex from step 14>     # do not let it self-generate
bash scripts/deploy_cloudrun.sh
```

**What that expands to.** Keep this to hand: if the script aborts after the
backend, this is the frontend half, and it is also the form to edit if you want
`NEEV_DEMO_PASSWORD` or `NEEV_GEMINI_MODEL` set (the script cannot pass either).

```bash
# --- backend -----------------------------------------------------------------
gcloud run deploy neev-api \
  --project buildguard-ai-2026 \
  --region asia-south1 \
  --source . \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --memory 2Gi \
  --cpu 1 \
  --timeout 600 \
  --set-env-vars "NEEV_MODE=live,NEEV_DEMO_AUTH=true,NEEV_SESSION_SECRET=$NEEV_SESSION_SECRET,GOOGLE_CLOUD_PROJECT=buildguard-ai-2026,NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY=12,NEEV_MAX_ANALYSES_PER_DAY=60,NEEV_ALLOW_BILLED_CALLS=1,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_LOCATION=global"
  # optional, and the script cannot add them for you:
  #   ,NEEV_DEMO_PASSWORD=<something not printed in this repo>
  #   ,NEEV_GEMINI_MODEL=gemini-3.7-flash

API_URL="$(gcloud run services describe neev-api \
  --project buildguard-ai-2026 --region asia-south1 --format='value(status.url)')"
curl -fsS "$API_URL/api/health"     # HARD GATE — see below

# --- frontend ----------------------------------------------------------------
gcloud run deploy neev-web \
  --project buildguard-ai-2026 \
  --region asia-south1 \
  --source src/frontend \
  --allow-unauthenticated \
  --min-instances 0 \
  --memory 1Gi \
  --timeout 600 \
  --set-env-vars "NEEV_API_BASE=$API_URL"
```

**The `curl` between them is the single most valuable line in the script.**
Under `set -e` a failing health check aborts *before* the frontend deploy, so a
broken backend costs one deploy and leaves one. Do not remove it and do not run
the two halves independently without it.

### 2.4 · Why each flag is what it is

`--source .` for the backend
: The build context must be the **repo root**, because
  `app/fixtures/loader.py` and `app/db/seed.py` resolve the repo root as
  `parents[4]` and read `<root>/fixtures/draw_schedule.csv`. That is also why
  the backend's `Dockerfile` sits at the root and the frontend keeps its own
  under `src/frontend/` — `--source` only honours a Dockerfile at the root of
  the context it is given.

`--max-instances 1` (backend)
: **A correctness requirement, not a cost one.** SQLite lives on the instance's
  own disk. Two instances would serve two different databases and a decision
  written on one would be invisible to the other.

`--min-instances 1` (backend)
: A cost decision, and the arithmetic is settled in
  `docs/Neev_Two_Week_Plan.md`: Cloud Run bills an idle min-instance at the
  *Min Instance CPU* SKU, ₹0.000238862/vCPU-s in `asia-south1` against
  ₹0.00229308 active — 9.6× less. Fourteen days of one warm 1 vCPU / 2 GiB
  instance, free tier applied, is about **₹740**, not the ₹2,530 an earlier
  version of that doc claimed. With ADK in the image a cold start pays the
  import plus a reseed: 15–30 s of blank screen in front of a judge is worth
  more than ₹740.

`--min-instances 0` (frontend)
: A Next standalone server boots in a second or two. Warming it would double the
  fortnight's bill for nothing.

`--memory 2Gi --cpu 1` (backend)
: The image carries ADK, `google-genai` and `google-cloud-bigquery`, and the
  container filesystem — SQLite plus the artifact store — is in memory and
  counts against this limit. See §4.3.

`--timeout 600`
: A measured live BoQ run is **107 s** and the SSE stream is held open for all of
  it. The frontend relays that stream through
  `app/api/jobs/[jobId]/events/route.ts`, so **both** services need the long
  timeout, and both have it.

`--allow-unauthenticated`
: A judge cannot present a Google identity token. The demo password and the
  daily caps are the only gates; that is the disclosed trade-off.

No `NEXT_PUBLIC_` variable anywhere
: `lib/api.ts` imports `server-only` and `NEEV_API_BASE` has no
  `NEXT_PUBLIC_` prefix, so the browser never learns the backend's address.
  Every call is a server-to-server hop inside Cloud Run — which is also why no
  CORS configuration is needed and why `CORS_ORIGINS` can stay at localhost.

---

## 3 · Immediately after the deploy — in this order

Capture both URLs first:

```bash
export API_URL="$(gcloud run services describe neev-api --project buildguard-ai-2026 --region asia-south1 --format='value(status.url)')"
export WEB_URL="$(gcloud run services describe neev-web --project buildguard-ai-2026 --region asia-south1 --format='value(status.url)')"
echo "$API_URL"; echo "$WEB_URL"
```

**Step 0 — warm.** Do this now and again a minute before presenting.

```bash
curl -fsS "$API_URL/api/health" && curl -fsS -o /dev/null -w '%{http_code}\n' "$WEB_URL"
```

**Step 1 — health, and confirm the mode.**

```bash
curl -fsS "$API_URL/api/health"
# expect exactly: {"status":"ok","mode":"live"}
```
If it says `"mode":"fixture"`, `NEEV_MODE` did not land (or was typo'd — the
validator silently coerces anything unrecognised to `fixture`). That is fixable
with `--update-env-vars`, not a redeploy; see §5.

**Step 2 — the container actually seeded.** The entrypoint runs
`python -m app.db.seed` before uvicorn. Confirm the book is there:

```bash
gcloud run services logs read neev-api --project buildguard-ai-2026 --region asia-south1 --limit 50
# expect "Initializing demo database ..." then "Serving on :8080 (NEEV_MODE=live)"
```

**Step 3 — sign-in works.** This is the check that catches a missing
`NEEV_DEMO_AUTH` or a mismatched password, and it costs nothing.

```bash
curl -fsS "$API_URL/api/auth/accounts"
# expect three accounts: ravi (owner/1001), prasad (owner/1002), officer (bank)
# an EMPTY array means NEEV_DEMO_AUTH did not land -> stop and fix before anything else

curl -fsS -c /tmp/neev.jar -X POST "$API_URL/api/auth/session" \
  -H 'content-type: application/json' \
  -d '{"username":"ravi","password":"neev-demo"}'
# expect {"role":"owner","loan_id":"1001","name":"Ravi Kumar"}
```

**Step 4 — the free, no-model check.** Every figure on the demo path is served
from the **seeded** recorded run, not from a live analysis. Reading these pages
calls no model and costs nothing:

```bash
curl -fsS -b /tmp/neev.jar "$API_URL/api/loans/1001/boq/latest"   | head -c 400
curl -fsS -b /tmp/neev.jar "$API_URL/api/loans/1001/sanction-check" | head -c 300
```

Then in a browser, signed in as `ravi` / `neev-demo`, and as `officer`:

- `$WEB_URL/owner/loans/1001/boq` — 40 items, ₹28,47,930 quoted vs ₹26,77,618 benchmark
- `$WEB_URL/owner/loans/1001/sanction` — ₹4,35,794 shortfall
- `$WEB_URL/bank/portfolio` — ten loans, worst first, ₹21,27,897 at risk
- `$WEB_URL/bank/loans/1001/tranches/4` — HOLD, exposure 1.11, and the site photographs

If all four render with figures, the demo is deliverable **whatever happens to
the live path**. Confirm that before you spend a rupee on step 5.

Note: these seeded revisions carry `pipeline_mode="fixture"` (`app/db/seed.py:226`),
so beat 1 still shows the "Demo replay" label on a live deployment. That is
correct and honest — it *is* a recording of a real run — but know it before a
judge points at the pill.

**Step 5 — the live path, exactly once.** ≈₹3.81 and ≈107 s. Signed in as
`ravi`, go to `$WEB_URL/owner/onboarding`, press **Use our sample BoQ**, and let
the Analyzing screen run to completion.

What good looks like, from the 2026-09-09 Vertex run: 40 line items, ~27–30
flags, ₹28,47,930 total, ₹32,35,794 cost estimate, zero parse errors. When it
finishes, the new revision on `/owner/loans/1001/boq` is labelled `live` rather
than `Demo replay` — that label flipping is the proof the deployed pipeline ran.

Narrate the wait: the last three agents all fire after the final tool call, so
the screen sits on "Reviewing the payment schedule" for the best part of ninety
seconds while a heartbeat every 15 s holds the connection open. The progress bar
genuinely does not move.

**Step 6 — reset before the judges arrive.** That live run left an extra
revision and consumed 1 of 12 for loan 1001. Nothing needs resetting if you are
content for the newest revision to be the live one; the recorded one is still
reachable at `/owner/loans/1001/boq/rev/1`.

---

## 4 · Known failure modes

### 4.1 · Gemini 503 or 429 on a live run

**Already mitigated in code.** `neev_pipeline/config.py::gemini_model()` wraps
every agent in `types.HttpRetryOptions(attempts=6, exp_base=2.0,
initial_delay=1.0)` retrying `[429, 500, 502, 503, 504]`. That exists because
one run is five-plus model calls in sequence, so a single 503 kills the whole
analysis — the failure rate compounds rather than averages. Measured 2026-09-09:
the same flash model answered a one-word prompt in 4.9 s while 503-ing the BoQ
request twice in a row. This is capacity pressure on heavy requests, not an
outage.

If it still surfaces, `app/services/jobs.py::_FAILURE_MESSAGES` maps it to copy
a borrower can act on, keyed on exception **class name** so ADK never gets
imported into fixture mode:

| Exception | What the screen says |
|---|---|
| `_ResourceExhaustedError` (429) | "Too many contracts were analysed in the last minute. Wait a minute and start the check again — nothing was lost." |
| `ServerError` (5xx) | "The service that reads contracts is busy right now. Try again in a few minutes." |
| `ClientError` (4xx) | "The service that reads contracts refused this document." |

**What you do:** wait sixty seconds and press Start again — but remember the cap
counted the failed attempt. If it fails twice, **stop demoing the live upload**
and narrate the recorded screens from step 4, which need no model at all. That
is a graceful degradation, not a broken demo. If you suspect the model id
itself, see §5.3 — `NEEV_GEMINI_MODEL` can be changed without a build.

### 4.2 · A cold start

`--min-instances 1` means there should not be one. There still can be: Cloud Run
replaces an instance on a revision change, an infrastructure move, or an OOM.
A cold start pays the ADK import plus `python -m app.db.seed` — 15–30 s of blank
screen. The frontend at `--min-instances 0` pays 1–2 s that nobody notices.

**What you do:** run step 0's warm-up a minute before presenting, every time.
If a screen is slow mid-demo, that is what it is; keep talking and it will
answer.

### 4.3 · The ephemeral SQLite and artifact store

`DATABASE_URL=sqlite:///./neev.db` and `ARTIFACT_DIR=./artifacts` both resolve
under `/app/src/backend`, on the container's **in-memory** filesystem. Three
consequences:

1. **Everything a judge does is lost when the instance recycles.** Decisions,
   uploads, reported milestones, new revisions. For a demo that is arguably
   right: every visitor gets clean state. It is also why the entrypoint seeds on
   boot rather than baking a database into the image — and it seeds *idempotently*
   (`python -m app.db.seed`, no `--reset`), so an existing book is never wiped.
2. **Uploads count against the 2 GiB memory limit.** `MAX_UPLOAD_BYTES` is
   10 MB per file (`app/services/artifacts.py:13`) and the frontend enforces the
   same 10 MB before sending, so it takes a deliberate effort to matter. Do not
   invite a room of judges to upload twenty scans each.
3. **The daily caps are per-process.** `JobRegistry` is in-memory with
   `MAX_RETAINED_JOBS = 50`, so an instance restart resets the counters. The cap
   is a good-faith brake, not a hard billing ceiling. If you need a hard one,
   the answer is a Cloud Billing budget alert, not this.

### 4.4 · Two judges colliding on one account

`--max-instances 1` exists so SQLite stays coherent, which means all traffic
hits one process and one database. `ravi` (loan 1001) and `prasad` (loan 1002)
are separate borrowers with separate contracts and **cannot** overwrite each
other. Two people signed in as `ravi` **can**: if both report a milestone, the
second overwrites the first.

**What you do:** hand out one account each — `ravi`, `prasad`, `officer` — or let
one person drive. There is no fourth owner account; `accounts.py` offers exactly
these three, because only 1001 and 1002 have a recorded run behind them and any
other loan lands a visitor on a contract screen with nothing to show.

To reset between visitors you must restart the instance, which on Cloud Run
means `gcloud run services update neev-api --region asia-south1
--update-env-vars NEEV_DEMO_RESET_NONCE=$(date +%s)` (any env change forces a
new revision — but see §5.2 on whether that counts as a deploy). The
runbook's `pkill` + `seed --reset` recipe is for the local `dev.sh` demo only.

### 4.5 · Smaller ones worth knowing

- **The Analyzing screen gives up after 3 reconnects.** `MAX_RECONNECTS = 3` in
  `AnalyzingLive.tsx`, and the counter is deliberately not reset by a successful
  message. The reader gets an error state with a retry button.
- **The SSE relay answers a transient backend failure with `200` and an empty
  stream**, never 503 — per the HTML spec an EventSource *fails permanently* on
  any status but 200. So a blip shows as a reconnect, not as "we lost the
  connection". Do not "fix" this if you see an odd empty stream in the logs.
- **`GET` reads through `lib/api.ts` time out at 8 s.** A wedged backend shows
  as an error state with a retry, not a hung page. The upload relay is separate
  at 180 s, and the accept returns a job id immediately, so the 107-second run
  is never the POST's problem.
- **Reaching `/owner/loans/1001/analyzing` by typing the URL shows a stalled
  screen.** It needs a `?job=` param. Always arrive there by uploading from
  `/owner/onboarding`.

---

## 5 · Rollback and recovery — what is honestly possible

### 5.1 · What cannot be undone

**One run of `scripts/deploy_cloudrun.sh` spends both free deploys.** After it
completes there is:

- no third deploy that is free;
- **no previous revision to roll back to** — `gcloud run services list` was empty
  before this, so each service will have exactly one revision and
  `gcloud run services update-traffic --to-revisions` has no target;
- no way to reclaim a deploy by deleting a service. `gcloud run services delete`
  plus a redeploy is a *third* deploy.

The one real piece of insurance is inside the script: the
`curl -fsS "$API_URL/api/health"` between the two deploys, under `set -e`. If
the backend is unhealthy, the script aborts and the **frontend deploy is not
spent**. Preserve that property — do not run the two halves separately without
the check between them.

### 5.2 · The open question you should have asked by now

`docs/Neev_Two_Week_Plan.md` lists it and it is **still open**: nobody has
confirmed with the organisers whether a "deploy" is a `gcloud run deploy`
invocation, a Cloud Run *revision*, or a *service* — or whether
`gcloud run services update` (an env change, no new image) counts at all. The
answer decides whether §5.3 is free or expensive. Ask before you need it.

### 5.3 · Repairs that need no new build

These change configuration only. They create a new *revision* from the *same
image*, with no Cloud Build run — which is why §5.2 matters.

**Use `--update-env-vars`, never `--set-env-vars`.** `--set-env-vars` **replaces
the entire set**: it would drop `NEEV_DEMO_AUTH`, `NEEV_SESSION_SECRET`,
`NEEV_ALLOW_BILLED_CALLS` and the Vertex flags in one stroke, disabling login
and signing out every visitor. This is the sharpest trap in the whole procedure.

```bash
# Live path failing and you need the demo to work: fall back to the recorded replay.
# This is the single most useful repair — it costs no model calls and every
# demo beat except the live upload keeps working.
gcloud run services update neev-api --project buildguard-ai-2026 --region asia-south1 \
  --update-env-vars NEEV_MODE=fixture

# The model id is wrong or unavailable on Vertex:
gcloud run services update neev-api --project buildguard-ai-2026 --region asia-south1 \
  --update-env-vars NEEV_GEMINI_MODEL=gemini-3.6-flash

# The public URL is being abused:
gcloud run services update neev-api --project buildguard-ai-2026 --region asia-south1 \
  --update-env-vars NEEV_MAX_ANALYSES_PER_DAY=0,NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY=0
# 0 disables the check entirely (`if per_loan > 0`), it does NOT block analyses.
# To block them, set NEEV_MODE=fixture instead — that makes every upload free.

# Change the password after the link has circulated:
gcloud run services update neev-api --project buildguard-ai-2026 --region asia-south1 \
  --update-env-vars NEEV_DEMO_PASSWORD=<new>
```

Each of these restarts the instance and therefore resets the SQLite book. That
is usually what you want.

### 5.4 · The real fallback

**`bash scripts/dev.sh` on the presenter's laptop.** It serves every one of the
four beats from a local SQLite database in fixture mode, with no network, no
Gemini and no BigQuery — there is no `google` package in the backend venv at
all, so nothing can bill even by accident. If Cloud Run is broken beyond a
config change, present from the laptop and say so. It is a hackathon; a working
demo on a laptop beats a broken URL.

`BE_PORT=8010 FE_PORT=3010 bash scripts/dev.sh` if a port is busy.

---

## 6 · What a judge will see

Sign-in is at `$WEB_URL/login`. Three accounts, one shared password `neev-demo`
(§1 step 15 if you changed it). The login screen lists the usernames itself, so
you do not have to read them out.

| Username | Signs in as |
|---|---|
| `ravi` | Ravi Kumar — the flagged contract, loan 1001 |
| `prasad` | D. Prasad — the clean contract, loan 1002 |
| `officer` | Anita Mehta, credit officer — the whole book |

**Beat 1 · Before signing.** As `ravi`, `$WEB_URL/owner/loans/1001/boq`.
A 40-item BoQ totalling ₹28,47,930 against ₹26,77,618 at Kompally benchmark
rates; 26 items flagged, grouped so the three that matter sit at the top. Point
at **RATES ABOVE BENCHMARK** — three RCC rows at ₹9,800/cum against a ₹8,036
benchmark, and read the tool's own sentence aloud. Then **EXPECTED BUT ABSENT** —
₹1,42,654 of scope not in the contract, with anti-termite showing a quantity and
no rupee figure because there is no benchmark and Neev will not invent one. The
line that lands: 45% of the money falls due before the slab is cast, ₹12,81,569.
Finish on the rail's four questions and **Send 4 questions**.

**Beat 2 · At sanction.** `$WEB_URL/owner/loans/1001/sanction`.
₹28,00,000 approved against a realistic ₹32,35,794, so a ₹4,35,794 shortfall
visible before a rupee is drawn. The gap table's five rows; two say "not stated"
rather than printing a zero. The first way forward quotes ≈₹2,50,000, derived
from this loan's own negative section deltas.

**Beat 3 · The bank's view.** As `officer`, `$WEB_URL/bank/portfolio`. Ten
active loans ranked by exposure, worst first; three need action, ₹21,27,897 at
risk. Point at "seen on site" against "paid up to" — loan 1003 is paid to slab
and photographed at plinth. Click row 1001 to drill in.

**Beat 4 · The decision, with evidence.**
`$WEB_URL/bank/loans/1001/tranches/4`. The brickwork-and-roof draw, ₹4,40,000,
recommended **HOLD**: ₹18,00,000 disbursed against ₹16,17,897 verified in place,
exposure 1.11, cost-to-complete gap −₹6,17,897. The reconciliation happens in
front of the room — ₹28,00,000 less ₹18,00,000 leaves ₹10,00,000 against
₹16,17,897 still to build. The site photograph checks out: Gemini read it
against a stage checklist and reported *slab*, high confidence. **The work is
real; the money is ahead of it.**

**Optional beat 5 · the live run**, if steps 3–5 of §3 went well and you have
two spare minutes. `/owner/onboarding` → **Use our sample BoQ** → watch five
agents run for ~107 s. Narrate the ninety quiet seconds.

**Three things to disclose before anyone asks** (judges respect a stated limit
more than they punish it):

- **Auth is a gate, not identity.** One shared password, printed in the runbook,
  no OTP, no phone verification. The role boundary and the 401 are real.
- **The demo-path figures are a recording**, captured from real runs on
  2026-09-07 against real BigQuery, and the BoQ screen labels itself so. The
  live pipeline is deployed and runnable — that is beat 5 — but it is not what
  beats 1–4 are reading.
- **`rate_benchmarks.verified` reads `NO - check vs CPWD DSR 2023`** on every
  row, while the tool tells the model its source is "CPWD DSR 2023 × Hyderabad
  factor". Soften that phrasing before a banker reads it closely, or say it
  first yourself.

And the measurement worth quoting, reproducible by a judge in thirty seconds at
zero cost:

```bash
src/agents/.venv/bin/python scripts/synthetic_boqs.py score
```

40 synthetic BoQs, 81 planted defects, `google.genai.Client` replaced with a
stub that raises so a model call is impossible: 100% precision and recall on
rate outliers, missing scope, front-loaded terms and GST silence, and 95%
benchmark coverage (826 of 866 priced items). `UNDERSPECIFIED` is excluded
deliberately — judging a specification too vague is a model judgement no tool
makes, and scoring it would be dishonest.

---

## 7 · Discrepancies found between the docs and the code

Found while writing this. Each one was verified in the source.

**7.1 · `NEEV_DEMO_PASSWORD` cannot be set by the deploy script.** *This is the
one that will bite you.* `docs/Neev_Demo_Runbook.md:229` documents:

    NEEV_DEMO_PASSWORD='say-it-out-loud' NEEV_DEPLOY_SANDBOX=1 bash scripts/deploy_cloudrun.sh

`scripts/deploy_cloudrun.sh` never reads that variable — grep finds it in the
two docs and nowhere in the script or the Dockerfile. `BACKEND_ENV` (lines
211–221) does not include it. The deployed password will be the
`app/core/settings.py:43` default, **`neev-demo`**, whatever you export. To
actually change it, add `NEEV_DEMO_PASSWORD=...` to the `--set-env-vars` string
by hand (§2.3) or fix it afterwards with `--update-env-vars` (§5.3).

**7.2 · The deploy script's closing banner describes the old sign-in.** Lines
277–278 print "Sign in with any 10-digit number. 'Home owner' lands on loan
1001". Since commit `aad7a11` ("Sign in with a username…") that is username +
password against three named accounts. Ignore the banner; §6's table is right.

**7.3 · The Two-Week Plan says the deployed app runs `FixtureRunner`.** Its demo
plan says "Do not demo a live upload. The deployed app runs `FixtureRunner`".
False for this deploy: `deploy_cloudrun.sh:57` defaults `MODE` to `live`, and
sets `NEEV_ALLOW_BILLED_CALLS=1` alongside it. Every "Start the check" on the
deployed URL is a real, billed run unless you deliberately deploy with
`NEEV_MODE=fixture`.

**7.4 · The same doc's change table still credits `--min-instances 0` with
saving ₹2,530.** Two sections earlier, the same doc corrects that arithmetic to
₹740 and puts `--min-instances 1` back — which is what the script actually does
(line 228). The table is stale, the corrected section and the script agree.

**7.5 · Two Two-Week-Plan open items are already closed.** "Reload
`rate_benchmarks` into BigQuery" — done, 62 rows in the table matching 62 in the
CSV. "Site photos in `demo_assets/`" — done differently and better: four tracked
JPEGs in `fixtures/site_photos/`, which `Dockerfile` copies into the image, so
they ship. `app/db/seed.py:386` still explains itself in terms of the git-ignored
`demo_assets/`.

**7.6 · The runbook's fixture-mode claim is now too pessimistic.** It says
"whatever PDF you upload, you see loan 1001's recorded analysis".
`fixture_runner.py::final_output` loads `loan_{req.loan_id}_pipeline.json` and
returns **None** for a loan it does not cover — deliberately, because serving
1001's numbers under another borrower's name is worse than an empty state. So
`prasad` sees 1002's recording, not Ravi's.

**7.7 · Test counts in both docs are stale.** `CLAUDE.md` says offline 28 /
backend 154; the Two-Week Plan says 35–38 / 158. Measured 2026-09-10: **offline
60, backend 228**, frontend verify clean. Use the real numbers in §1 step 10 —
a suite that reports more than the doc expects is not a failure.

**7.8 · `NEEV_GEMINI_MODEL` is not a deployable knob.** `config.py:19` reads it
from the environment and defaults to `gemini-3.7-flash`, but the deploy script
never passes it, so the deployed service has no override in place. Adding it
later is `--update-env-vars` (§5.3) — which may or may not cost a deploy (§5.2).
Consider setting it explicitly at deploy time so a later change is an edit.

**7.9 · `GOOGLE_GENAI_USE_VERTEXAI` is deprecated in the installed ADK.**
`google-adk` 2.8.0 / `google-genai` 2.22.0 both still honour it and both prefer
`GOOGLE_GENAI_USE_ENTERPRISE`; ADK emits a `DeprecationWarning`. It works today.
Do not swap it on deploy day — a warning in the logs is cheaper than an untested
change on the only deploy you get.

**7.10 · No conflict between `GOOGLE_CLOUD_LOCATION=global` and BigQuery.**
Worth stating because it looks like one: `neev_pipeline/config.py:10` sets
`LOCATION = "asia-south1"` for BigQuery while the deploy sets
`GOOGLE_CLOUD_LOCATION=global` for Vertex. Checked — `google-cloud-bigquery`
does not read `GOOGLE_CLOUD_LOCATION`, `bigquery.Client()` resolves the job to
the dataset's own location, and `buildguard_data` is `asia-south1`. No
cross-region query, no egress.

**7.11 · Minor: the "20 MB ceiling" comments.** Both
`app/api/loans/[loanId]/boq/route.ts:29` and `OnboardingWizard.tsx:93` reason
about a 20 MB wizard cap. The actual constants are 10 MB on both sides
(`upload-validation.ts:2`, `app/services/artifacts.py:13`). Comments only —
behaviour is consistent.

**7.12 · The preflight does not check BigQuery on the Vertex path.**
`deploy_cloudrun.sh` checks the runtime account's BigQuery roles only inside the
`elif` for the API-key path (lines 138–155). On the default Vertex path it is
skipped, yet the pipeline queries `buildguard_data` on every live analysis. The
bindings happen to be present today (§1 #5), so nothing is at risk — but the
check is on the wrong branch.

---

## 8 · The one-page version

```
BEFORE            git status --short              # read it; decide on every dirty file
                  python3 -m tests.test_offline   # 60
                  (cd src/backend && .venv/bin/python -m pytest tests/ -q)   # 228
                  (cd src/frontend && npm run verify)                        # clean
                  docker build -t neev-api . && docker build -t neev-web src/frontend
                  gcloud meta list-files-for-upload . | wc -l                # 343
                  openssl rand -hex 32            # write it down

DEPLOY (ONCE)     export NEEV_DEPLOY_SANDBOX=1
                  export NEEV_SESSION_SECRET=<the hex>
                  bash scripts/deploy_cloudrun.sh

AFTER             curl -fsS "$API_URL/api/health"          # mode:live
                  curl -fsS "$API_URL/api/auth/accounts"   # three accounts, not []
                  browser: /owner/loans/1001/boq, /owner/loans/1001/sanction,
                           /bank/portfolio, /bank/loans/1001/tranches/4
                  then ONE live run from /owner/onboarding
                  then warm both URLs a minute before presenting

IF BROKEN         gcloud run services update neev-api --region asia-south1 \
                    --update-env-vars NEEV_MODE=fixture
                  # --update-env-vars, NEVER --set-env-vars
                  # last resort: bash scripts/dev.sh on the laptop
```
