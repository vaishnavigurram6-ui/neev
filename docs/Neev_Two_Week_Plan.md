# Neev — two-week live plan

*Cost, deployment, data and demo, for a hackathon window of roughly fourteen days.
Written 2026-09-07. Every figure is measured from this repository or verified
against Google's published pricing on that date.*

---

## The constraint that shapes everything

**You get two free deploys. Subsequent deploys cost money.**

`scripts/deploy_cloudrun.sh` makes **two** `gcloud run deploy` calls — one for
the backend, one for the frontend. So a single run of that script consumes both
free deploys, with nothing left for a repair.

That inverts the obvious order. You cannot "deploy early on fixtures, then
redeploy with real data" — that is two deploys with zero margin for a mistake in
either. Instead:

> **Everything is final before anything is deployed.** Capture the real runs,
> generate the data, verify locally, and deploy once — keeping the second deploy
> as your only emergency repair.

### What does *not* consume a deploy

This is the part that makes a single-shot deploy safe. In Cloud Shell:

- `docker build` — unlimited, free, and it is the same Dockerfile Cloud Build
  will use
- `docker run` — unlimited; you can exercise both containers end to end locally
- `gcloud artifacts docker push` — pushing an image is not deploying it
- Everything offline in this repo: tests, the BigQuery verifier, the synthetic
  eval, `--from-raw` re-parsing

So **all container debugging happens in Cloud Shell with Docker, at no deploy
cost.** Only the final `gcloud run deploy` is scarce.

### Worth asking the organisers

The accounting is ambiguous and the answer changes your margin from zero to one:

- Is a "deploy" a `gcloud run deploy` invocation, a Cloud Run **revision**, or a
  **service**? Two services deployed once each may count as one deploy or two.
- Does `gcloud run services update` (an env-var change, no new image) count?

Ask before you spend either one.

---

## Cost summary

Verified 2026-09-07. Conversion at 1 USD = ₹94.5.

| Service | Rate | Free tier |
|---|---|---|
| Gemini 3.6 Flash | $0.75 in / $3.75 out per 1M tokens | n/a — this project bills |
| Gemini, from 1 Jan 2027 | **$1.50 / $7.50** — doubles, already published | — |
| Gemini batch mode | 50% of standard | — |
| BigQuery on-demand | $6.25 / TB, 10 MB minimum per table per query | 1 TB / month |
| Cloud Run | $0.000024 / vCPU-s, $0.0000025 / GiB-s | 180k vCPU-s, 360k GiB-s, 2M requests |

Your project reports `billingEnabled: true` and `generativelanguage.googleapis.com`
enabled, so you are on the **Gemini paid tier**: calls bill against credit, and
there is no 15 RPM free-tier cap to design around.

### Cost of one pipeline run

The dominant term is not token price — it is how many times the model is called.
Every tool call is a separate turn that re-sends the whole conversation, so cost
grows with the square of the turn count.

| | Before (2026-09-07) | After batching | |
|---|---|---|---|
| Analyst tool calls | 81 | **5** | one per check, never per item |
| Input tokens | ~342,000 | ~43,000 | |
| Wall clock | ~2 min | ~10 s | this is the demo-critical one |
| Gemini | ₹25.60 | **₹3.81** | |
| BigQuery | 810 MB | 30 MB | the 10 MB minimum dominated, not the data |
| **Per run** | **₹26.08** | **₹3.81** | 85% less |

That change is already made — see *Code changes* below.

### Two-week budget

| Item | Runs | Cost |
|---|---|---|
| Captures for loans 1001 and 1002, with retries | 6 | ₹23 |
| `adk web` exploration | 10 | ₹38 |
| Live demo runs across the window | 60 | ₹229 |
| Buffer | 24 | ₹91 |
| **Gemini** | 100 | **₹381** |
| BigQuery — 3 GB against a 1 TB free tier | | **₹0** |
| Cloud Run at `--min-instances 0` | | **₹0** |
| Cloud Build, ~2 builds | | **₹0** |
| Docker in Cloud Shell, unlimited | | **₹0** |
| **Total** | | **≈ ₹400 of 30,000 — about 1.3%** |

**Credits are not your constraint.** The scarce resources are your two deploys
and the demo's wall clock.

### The ₹2,530 line, corrected to ₹740 — and put back

**This section had the arithmetic wrong.** It priced a warm instance at Cloud
Run's *active* CPU rate. Cloud Run bills an idle min-instance at a different
SKU, and the Cloud Billing catalog for `asia-south1` (read 2026-09-09) gives:

| SKU | ₹ per unit |
|---|---|
| Services CPU (request-based, active) | 0.00229308 / vCPU-s |
| **Services Min Instance CPU** | **0.000238862 / vCPU-s** |
| **Services Min Instance Memory** | **0.000238862 / GiB-s** |

Idle CPU is **9.6× cheaper** than active. Fourteen days of one warm instance is
1,209,600 seconds, so with the 180k vCPU-s / 360k GiB-s monthly free tier
applied:

- 1 vCPU + 1 GiB → ₹246 + ₹203 = **₹449**
- 1 vCPU + 2 GiB → ₹246 + ₹492 = **₹738**

Not ₹2,530. `--min-instances 1` is back on the backend at 2 GiB, because the
image now carries the ADK pipeline: a cold start pays that import plus a reseed,
which is 15–30 seconds of blank screen rather than the old 3–6. ₹740 is a
better trade than a judge watching a spinner.

The frontend stays at `--min-instances 0`. A Next standalone server boots in a
second or two, nobody notices, and warming it would double the bill for nothing.

`--max-instances 1` stays on the backend, and that one *is* a correctness
requirement rather than a cost one: SQLite lives on the instance's own disk, so
two instances would serve two different databases. A decision or an upload is
still lost when the instance recycles — for a demo that is arguably right, since
every visitor gets clean state.

---

## Does synthetic data cost credits?

**No.** Both halves are free, and the second is free by construction rather than
by intention.

| Step | Cost | Why |
|---|---|---|
| `synthetic_boqs.py generate` | ₹0 | Local arithmetic and reportlab. No API of any kind. |
| `synthetic_boqs.py score` | ₹0 | Reads BigQuery (kilobyte tables, free tier); `google.genai` is replaced with a stub that **raises** before any pipeline module imports, so a model call is impossible. |
| Running the full pipeline on a synthetic BoQ | ₹3.81 each | This is a real run and does bill. Only do it if you want a live demo on a second document. |

The same Gemini fence protects `scripts/verify_against_bigquery.py`.

---

## What the synthetic set is for

**It is an evaluation set, not training data.** Nothing in Neev is trained, and
that is a design decision worth defending rather than apologising for:

- The only model work is reading a PDF into line items and classifying a photo.
  Gemini does both zero-shot.
- Every number that constitutes a *decision* — benchmark rate, 15% threshold,
  steel/RCC range, exposure ratio, LTV band, RELEASE/HOLD — comes from a
  BigQuery lookup or a documented constant. Fine-tuning cannot improve a SQL
  query.
- Fine-tuning on synthetic BoQs would teach the model to reproduce *this
  generator's* patterns, and cost you the one property a bank needs: you can
  point at the row in `rate_benchmarks` that caused each flag.
- `docs/Neev_Data_Inventory.md` already forbids training on the one labelled
  dataset, for leakage.

What the set buys instead is a **measurement**. The generator knows what it
planted, so the grounding layer can be scored against ground truth:

```
Grounding-layer accuracy over 40 synthetic BoQs
BigQuery: real.  Gemini: unreachable by construction.

  defect type        planted  found  missed  false+   recall   prec.
  RATE_OUTLIER            17     17       0       0    100%    100%
  MISSING_SCOPE           14     14       0       0    100%    100%
  UNDERSPECIFIED           0      —       —       —      n/a     n/a
  FRONT_LOADED            18     18       0       0    100%    100%
  GST_SILENT              16     16       0       0    100%    100%

  benchmark coverage   826/866 priced items (95%)
```

Reproducible by a judge in thirty seconds, at zero cost. That is a far stronger
claim than any assertion about training.

`UNDERSPECIFIED` is excluded deliberately: it is a judgement about wording, which
only the model makes. Counting it as a tool miss would be dishonest.

### What the eval found on its first three runs

**1. A real false-positive bug, now fixed.** `EXPECTED_SCOPE["external plaster"]`
matched only the exact phrases `"external plaster"` and `"exterior plaster"`. An
ordinary Indian BoQ line — *"External cement plaster 18mm in CM 1:4"* — matched
neither, so a priced item was reported as **absent scope**. `MISSING_SCOPE`
precision was 35%. Ravi's fixture never caught it because external plaster is a
seeded *omission* there, so the present-but-differently-worded case had never
been exercised. Phrase lists widened in `config.py`; precision is now 100%.

**2. Benchmark coverage was 67% — now 95%.** A third of priced items had no
benchmark at all, and the misses were not exotic: `dpc` existed but not "damp
proof course", `pcc` but not "plain cement concrete", `size stone` but not
"stone masonry". Thirty-two alias rows later, coverage is **826 of 866 priced
items**, and the only wordings still unmatched are the three anti-termite ones —
deliberately, see below.

The cost of aliasing is duplicated rates: 62 rows over 30 distinct items. Two
tests in `tests/test_offline.py` make that safe — rows sharing a description
must agree on unit and `effective_rate`, and no wording may resolve to a
benchmark in a *different unit*. That second one matters more than it sounds:
`check_rate_deviation` divides a quote by a benchmark without ever checking the
units agree, so a per-cum quote against a per-sqm benchmark yields a confident,
meaningless deviation. It caught nine such routings on first run.

**3. An invented benchmark is worse than no benchmark.** Adding an anti-termite
rate looked like an easy coverage win. There is no CPWD DSR figure for it and no
sourced market one, so the rate was a guess — and at ₹120/sqm it made
`clean_boq.pdf`'s honest ₹95/sqm read as 21% *under* benchmark, flagging a
document authored to have no rate defects. A pre-existing test caught it.

The rows were removed. Anti-termite is caught by `EXPECTED_SCOPE` — is it
present or absent? — which needs no rate at all. The analyst prompt already
tells the model "never estimate a benchmark yourself"; the table should hold
itself to the same rule. Those three wordings stay UNBENCHMARKED, which the
pipeline supports explicitly.

**Ravi's own BoQ is still 28 of 39**, and that is fine. Its remaining misses are
all fittings and finishing — teak door frame, modular switches, DB with MCBs,
EWC, wash basins, MS gate, site cleaning — whose rate depends on brand and
model. The table benchmarks structural work. Say that if asked, rather than
treating it as a gap.

---

## Code changes already made

All verified offline. No credits spent.

| Change | File | Effect |
|---|---|---|
| Batched benchmark lookup | `tools/boq_analyst_tool.py` | `lookup_benchmark_rates(list)` — one query for the whole BoQ. 39 calls → 1 |
| Batched deviation check | `tools/boq_analyst_tool.py` | `check_rate_deviations(list)` — 28 calls → 1. Singular stays as the pure, tested implementation |
| Prompt caps tool calls | `agent.py` | "Use exactly five tool calls for the whole document… never per line item" |
| Scope phrases widened | `config.py` | Fixes the false-positive bug above |
| 32 benchmark aliases | `fixtures/rate_benchmarks.csv` | Coverage 67% → 95%; 30 → 62 rows |
| Alias integrity + unit guards | `tests/test_offline.py` | Duplicated rates cannot silently diverge |
| `--min-instances 0` | `scripts/deploy_cloudrun.sh` | Saves ₹2,530 |
| Verifier uses the batched path | `scripts/verify_against_bigquery.py` | Exercises what the paid run will actually do |

Behaviour is preserved: the verifier reports the same 28 matched items, 3 rate
flags and 7 total flags as before, in 2 queries instead of 78.

**Suites:** offline 38 · backend 158 · frontend verify clean.

---

## The schedule

Five stages, each with a gate. The gates exist so a bad step is not paid for
twice — the same logic the app applies to a construction loan.

### Stage 1 — Verify offline · Day 1 · ₹0

```bash
python3 -m tests.test_offline                              # 35
cd src/backend && .venv/bin/python -m pytest tests/ -q     # 158
cd src/frontend && npm run verify                          # clean
```

**Gate:** all three green.

### Stage 2 — Build and run both containers in Cloud Shell · Day 1 · ₹0

This is the stage that protects your two deploys. Do not skip it.

```bash
docker build -t neev-api .
docker build -t neev-web src/frontend

docker run -d --name api -p 8080:8080 neev-api
curl -fsS http://localhost:8080/api/health

docker run -d --name web -p 3000:8080 \
  -e NEEV_API_BASE=http://host.docker.internal:8080 neev-web
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:3000/
```

Iterate here as many times as it takes — Docker is free and unlimited.

**Gate:** both containers serve, and `/owner/loans/1001/boq` renders with data
when you pass an owner session cookie. Neither Dockerfile has ever been built,
so budget real time for this stage.

### Stage 3 — Lift the dry run and capture · Day 2 · ₹23

Edit `CLAUDE.md`: change the dry-run status to `LIFTED 2026-09-07`.

```bash
export GOOGLE_CLOUD_PROJECT=buildguard-ai-2026
export GOOGLE_API_KEY=...
export NEEV_ALLOW_BILLED_CALLS=1

python3 -m venv src/agents/.venv
src/agents/.venv/bin/pip install -e src/agents

# FREE — the grounding path against real BigQuery, Gemini unreachable
# Reload the benchmark table first -- the 32 new aliases are CSV-only until then
bash scripts/load_bigquery.sh

src/agents/.venv/bin/python scripts/verify_against_bigquery.py

# Then the paid captures
src/agents/.venv/bin/python scripts/record_golden_run.py --loan 1001 --boq fixtures/sample_boq.pdf
src/agents/.venv/bin/python scripts/record_golden_run.py --loan 1002 --boq fixtures/clean_boq.pdf
```

The verifier must show a `benchmark_rate` on the lookups before you pay for
anything. If a capture fails validation, **do not re-run it** — the raw session
state is saved in `.golden_runs/`; fix the parse layer and replay with
`--from-raw`, free.

**Gate:** `pytest tests/test_fixture_contract.py -q` passes on both captures.

### Stage 4 — Generate and score the synthetic set · Day 2 · ₹0

```bash
# Manifest only -- deterministic, committed, and all `score` needs
src/agents/.venv/bin/python scripts/synthetic_boqs.py generate --count 40
src/agents/.venv/bin/python scripts/synthetic_boqs.py score

# Optional: render the documents, if you want a second real PDF to upload
src/agents/.venv/bin/pip install reportlab
src/agents/.venv/bin/python scripts/synthetic_boqs.py generate --count 40 --pdf
```

The PDFs are git-ignored on purpose: reportlab embeds a `CreationDate`, so their
bytes churn on every run. `manifest.json` is the source of truth and is
byte-identical across runs, so the score table is reproducible exactly.

**Gate:** a precision/recall table you are willing to put in the submission.
Widen `rate_benchmarks` synonyms and re-score until coverage stops embarrassing
you — every iteration is free.

### Stage 5 — Deploy once · Day 3 · ₹0

Only now, with the data final and the containers proven:

```bash
bash scripts/deploy_cloudrun.sh
```

**Gate:** the frontend URL serves the owner and bank consoles with captured
figures. **Do not deploy again unless something is broken** — the second deploy
is your only repair.

Warm it before you present:

```bash
curl -fsS "$WEB_URL" >/dev/null && curl -fsS "$API_URL/api/health"
```

---

## Demo plan

Follow `docs/Neev_Demo_Runbook.md` for the four beats. Two additions for this
window:

1. **Warm the services** a minute before you present. `--min-instances 0` means
   the first request pays a cold start.
2. **Do not demo a live upload.** The deployed app runs `FixtureRunner`, so any
   uploaded PDF replays the captured analysis. Say so plainly — the figures are
   real, the analysis is a recording — rather than letting a judge discover that
   their own document produced Ravi's flags.

`adk web` from `src/agents/` is the stronger artifact for showing mechanism: it
displays the five agents and their grounding tool calls, which the polished UI
deliberately hides. Record it once rather than running it live; every message is
a billed run. **Do not deploy `adk web`** — it is a dev UI with no auth.

### Be straight about three things

Judges respect disclosed limits more than they punish them:

- **Auth is stubbed.** `src/backend/app/api/deps.py` says so in its own
  docstring: the cookie is unsigned, there is no OTP. The boundary and the 401
  are real.
- **The pipeline is not driving the screens.** Figures are captured from real
  runs against real BigQuery; live per-upload analysis is built but not wired to
  the upload path.
- **`rate_benchmarks.verified` says `NO - check vs CPWD DSR 2023` on every row**,
  while the tool tells the model its source is "CPWD DSR 2023 × Hyderabad
  factor". Either verify the rates or soften that string before a banker reads
  it closely.

---

## If it goes to production

Modelled at 1,000 loans/month — one BoQ analysis plus four tranche reviews each,
so 5,000 runs.

| Line | Unbatched | Batched | Note |
|---|---|---|---|
| Gemini 3.6 Flash | ₹75,000 | ₹19,000 | Doubles 1 Jan 2027 |
| BigQuery | ₹1,800 | ₹0 | Batched volume stays inside the free tier |
| Cloud Run | ₹12,000 | ₹12,000 | Two warm instances, real traffic |
| Cloud SQL | ₹7,000 | ₹7,000 | SQLite cannot survive a second instance |
| **Per month** | **₹95,800** | **₹38,000** | |
| **Per loan** | **₹96** | **₹38** | |

Against a ₹28 lakh sanction, ₹38 is **0.0014%**. Unit economics are not the
question, and a pitch that dwells on them is answering the wrong one.

The two real risks are structural: the tool-call fan-out, which is now fixed and
would have been four times worse at this volume; and the **1 January 2027 price
doubling**, which turns ₹19,000 a month into ₹38,000 with no code change. Batch
mode halves the rate again for anything non-interactive — nightly portfolio
re-scoring is the obvious candidate.

What production needs and this demo does not have is unchanged by any of the
above: real authentication, a database that survives a second instance, and audit
logging on every disbursement decision.

---

## Open items

- [ ] **Credit expiry date** — console only, *Billing → Credits*. The balance is
      twelve times what you need; an expiry inside the window is the only budget
      fact that could still change this plan.
- [ ] **Ask the organisers what counts as a deploy** — service, revision, or
      command. Changes your margin from zero to one.
- [x] **Widen `rate_benchmarks` synonyms** — done; coverage 67% → 95%.
- [ ] **Reload `rate_benchmarks` into BigQuery.** The aliases live in the CSV and
      have no effect until the table is replaced. `bash scripts/load_bigquery.sh`
      does it, and a `bq load` is **not** a Cloud Run deploy — it costs you
      nothing and consumes neither free deploy. Do this before Stage 3.
- [ ] **Site photos** in `demo_assets/` — without them `inspection_result` is
      absent and the tranche screen's visual evidence stays authored.
