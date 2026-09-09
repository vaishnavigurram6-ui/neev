# Neev — demo runbook

*Written 2026-08-28, updated 2026-09-09 when the dry run was lifted and live mode
was first executed. The four beats below run in fixture mode: no Gemini, no BigQuery,
no billed Google call. There is no `google` package in the backend venv at all,
so nothing can bill even by accident.*

## Start it

**Safety update (2026-09-08):** see [Review remediation](Review_Remediation.md).
The dev script explicitly enables sandbox login; direct backend starts need
NEEV_DEMO_AUTH=true. Uploaded documents are retained, but fixture mode replays
the sample rather than analyzing the upload. Rates are provisional, not verified
CPWD authority. All-items now includes every document item; question counts follow
the selected revision. Existing local state is preserved rather than reset.

```bash
bash scripts/dev.sh
```

First run creates the backend venv, installs frontend dependencies and seeds the
database; later runs skip straight to serving. It prints the four demo URLs and
stops both servers on Ctrl-C.

If a port is busy: `BE_PORT=8010 FE_PORT=3010 bash scripts/dev.sh`.

**Log in as the owner** at `/login` — role "home builder", any 10-digit number,
any 6-digit code. **As the bank**, pick "lender" instead. There is no real OTP;
the code is not checked.

## The four beats

Run them in this order. The story is one loan — **1001, Ravi Kumar, Plot 47,
Kompally** — seen from both sides of the table.

### 1 · Before signing — the contract, checked line by line

`/owner/loans/1001/boq`

**Say:** Ravi's contractor sent a 40-item BoQ totalling ₹28,47,930. Neev priced
the same scope at Kompally benchmark rates: ₹26,77,618. Twenty-six items carry
a flag, grouped so the three that matter sit at the top.

**Point at:** the first group, **RATES ABOVE BENCHMARK** — three RCC rows at
₹9,800/cum against a ₹8,036 benchmark. Read the note aloud; it is the tool's
own sentence, not prose: *"Quoted rate of Rs 9,800/cum exceeds the benchmark
rate of Rs 8,036/cum by 22%."*

**Then:** scroll to **EXPECTED BUT ABSENT** — waterproofing, anti-termite and
external plaster, ₹1,42,654 of scope that is not in the contract at all and
comes back later as "extras". Note that anti-termite shows a quantity but no
rupee figure: there is no benchmark for it, and Neev will not invent one.

**The line that lands:** 45% of the money falls due before the slab is cast.
₹12,81,569 before there is meaningful structure to show for it.

**If asked about the last group:** *NO BENCHMARK TO COMPARE AGAINST* holds
twelve fittings — a teak door frame, modular switches, an MS gate — priced by
brand and model, which a structural benchmark table has no rate for. It sits
last on purpose, so it cannot crowd the three real findings.

**Then:** the rail's four questions. Neev doesn't accuse anyone — it writes the
questions Ravi can send his contractor in writing. Hit **Send 4 questions**.

### 2 · At sanction — will the loan actually finish the house?

`/owner/loans/1001/sanction`

**Say:** the bank approved ₹28,00,000. The realistic cost at Kompally rates,
including the scope the contract left out, is ₹32,35,794. That's a ₹4,35,794
shortfall, visible before a rupee is drawn rather than at tranche four.

**Point at:** the gap table — five rows showing where the shortfall comes from.
Two have no quoted figure and say "not stated" rather than printing a zero.

**Then:** the three ways forward. The first quotes **≈ ₹2,50,000**, derived from
this loan's own negative section deltas — not a number typed into a design.
Loan 1002's version of the same screen says "reduces the quote", because it has
no over-priced sections and Neev will not quote a saving that isn't there.

### 3 · The bank's view — worst loans first

`/bank/portfolio`

**Say:** same product, other side of the table. Ten active construction loans,
ranked by exposure, worst first. Three need action, and ₹21,27,897 is at risk.

**Point at:** the "seen on site" column against "paid up to". Loan 1003 has been
paid to slab; photos show plinth only. That's the whole thesis in one column.

**Then:** click row 1001 to drill in. Every row drills into its own loan.

### 4 · The decision — with evidence

`/bank/loans/1001/tranches/4`

**Say:** the contractor has requested the brickwork-and-roof draw, ₹4,40,000.
Neev recommends **HOLD**, and shows its arithmetic in one line each:

| | |
|---|---|
| Disbursed so far | ₹18,00,000 |
| Verified value in place | ₹16,17,897 |
| Disbursement exposure | 1.11 |
| Cost to complete | ₹16,17,897 |
| Cost-to-complete gap | −₹6,17,897 |

Every one of those five figures came out of a real pipeline run. The gap
reconciles in front of the audience: ₹28,00,000 sanctioned less ₹18,00,000 drawn
leaves ₹10,00,000, against ₹16,17,897 still to build.

**The point:** the site photo checks out. Gemini read it against a stage
checklist and reported *slab*, high confidence, matching the claim — the caption
on screen is its own words about columns, shuttering and props. **The work is
real; the money is ahead of it.** Releasing the next draw funds a house that
cannot be finished with what is left.

**If asked how reliable that photo check is:** honestly. It is a model
judgement and it varies. On one recorded run of loan 1002 it caught that the
photo showed a G+1 structure against a G+0 plan and refused the release; on
another it did not. Both runs are in `.golden_runs/`. That variance is why the
escalation gate exists — when the check fires, `assess_tranche` stops the money
regardless of how comfortable the ratio looks.

**Then:** the officer/owner tabs — the same decision explained twice, in two
registers. And the decision card, which writes the full evidence trail to the
loan file.

## If something breaks

| Symptom | Do this |
|---|---|
| A screen shows an error state | The backend died. Check the `dev.sh` output; `curl localhost:8000/api/health` should return `{"status":"ok","mode":"fixture"}`. |
| Figures look wrong or absent | Re-seed: `cd src/backend && .venv/bin/python -m app.db.seed --reset`. |
| The Analyzing screen sits still | It needs a `?job=` param. Reach it by uploading from `/owner/onboarding`, not by typing the URL. |
| A page redirects to `/login` | Role enforcement. Owner routes reject bank sessions and vice versa; log in as the other role. |
| Port already in use | `BE_PORT=8010 FE_PORT=3010 bash scripts/dev.sh` |

**Offline fallback:** every beat above is a server-rendered page reading a local
SQLite database. Nothing needs the internet. If a screen fails entirely, the API
answers directly — `curl localhost:8000/api/loans/1001/boq/latest` — and
`adk web` from `src/agents/` remains a separate, independent surface.

## What is real and what is staged

Say this plainly if asked; it is more convincing than the alternative.

**Real.** Every figure on the demo path came out of a captured pipeline run on
2026-09-07 — Gemini reading `fixtures/sample_boq.pdf`, benchmark rates from a
62-row BigQuery table, construction cost from `loan_history` and
`metro_city_prices`, and the stage judgement from two real site photos through
`verify_construction_stage`. The raw runs are in `.golden_runs/`; the parsed
results are the fixtures the app serves. Also real: the five-agent ADK pipeline,
the risk arithmetic and its thresholds, the whole web application, role
enforcement, and the audit trail a decision writes.

**Two live paths, not one.** Uploading a BoQ runs all five agents. Reporting a
milestone runs the two that judge photographs — `visual_inspector_agent` then
`disbursal_risk_agent` — because the BoQ has not changed and re-reading it would
spend three more agents to reproduce stored numbers. That path used to store the
frames and hardcode ESCALATE without asking the model anything, which made the
landing page's "photos verify each payment" the one promise the product did not
keep.

Worth demoing, because the model reaches the demo's own conclusion unaided. On
2026-09-09, Ravi's real slab photographs against a claimed `brickwork_roof`:
stage `slab`, confidence `high`, **`matches_claim` false**, ESCALATE, exposure
1.11 — in 33 seconds. The borrower asked for the brickwork draw and the
photographs show a slab, and nothing seeded that.

**Live, if the key allows it.** `NEEV_MODE=live` drives the real five-agent ADK
pipeline on whatever is uploaded. It is built and it has been run: on
2026-09-09, `fixtures/sample_boq.pdf` through the live runner produced 40 line
items, 27 flags, a ₹28,47,930 total and a ₹32,35,794 cost estimate with zero
parse errors, in 107 seconds.

Two things to know before demoing it:

*Go through Vertex AI, not the Gemini API key.* The Gemini API's free tier
allows **20 `generateContent` requests per day per model**
(`GenerateRequestsPerDayPerProjectPerModel-FreeTier`) — one analysis is five
agents plus tool round-trips, so that is about **two analyses a day**, and
lifting it means putting a card on an AI Studio account. Vertex AI runs the same
models with no such cap, authenticates as the Cloud Run service account, and
bills the project's Cloud Billing account, which is where hackathon credits sit.
`scripts/deploy_cloudrun.sh` uses Vertex by default; locally, set
`GOOGLE_GENAI_USE_VERTEXAI=true GOOGLE_CLOUD_PROJECT=buildguard-ai-2026
GOOGLE_CLOUD_LOCATION=global`. Proven end to end on 2026-09-09: 40 line items,
30 flags, no parse errors, 161 seconds.

*It is capped on purpose.* Twelve analyses per loan per day, sixty across the
service (`NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY`, `NEEV_MAX_ANALYSES_PER_DAY`). The
demo URL is public and its sign-in takes any ten-digit number, so without a cap
anyone who finds it can spend credits at about ₹3.81 a click.

*It takes 107 seconds.* The last three agents all fire after the final tool
call, so the Analyzing screen sits on "Reviewing the payment schedule" for the
best part of ninety seconds. The stream writes a heartbeat every 15s to keep the
connection open, but the progress bar genuinely does not move. Narrate it, or
demo fixture mode, where the same five phases play in about eight seconds.

**Fixture mode**, the default, replays a recorded run instead: **whatever PDF you
upload, you see loan 1001's recorded analysis.** Say so rather than letting a
judge discover it. It costs nothing, has no quota, and the BoQ screen labels
itself "Demo replay" so the claim is on the page rather than only in your
narration.

**Not built.** Real identity, translation, text-to-speech, marked-up PDF
export, WhatsApp sending. Most render as a disabled control that says why,
rather than a dead button that lies — the exception is the marked-up PDF, whose
button is gone: a dead control explaining itself with a spec section number is
documentation wearing an interface, and this is where documentation goes.

## The demo accounts, and their password

The login screen asks for a username and a password and lists nothing, on
purpose: a product does not tell a visitor whose account to borrow. The
credentials are documentation, so they live here.

| Username | Password | Signs in as |
|---|---|---|
| `ravi` | `neev-demo` | Ravi Kumar — the flagged contract, loan 1001 |
| `prasad` | `neev-demo` | D. Prasad — the clean contract, loan 1002 |
| `officer` | `neev-demo` | Credit officer — the whole book |

One shared password, set by `NEEV_DEMO_PASSWORD`. Override it on a deployment if
you would rather it were not the one printed in this repo:

    NEEV_DEMO_PASSWORD='say-it-out-loud' NEEV_DEPLOY_SANDBOX=1 bash scripts/deploy_cloudrun.sh

It is a gate, not identity. It exists because the deployed URL is public and
sign-in used to take any ten-digit number and any six-digit code, which meant
anyone who found the link could start analyses that cost about ₹3.81 each.

**A username picks the loan**, which is the part that matters for a demo: `ravi`
and `prasad` are two borrowers with two contracts and cannot overwrite each
other. Only 1001 and 1002 have a recorded pipeline run behind them, so those are
the only two borrowers worth offering — any other loan would land a visitor on a
contract screen with nothing to show.

**Two judges on the same account still collide.** Cloud Run runs at
`--max-instances 1` because SQLite lives on the instance's disk, so if two
people sign in as `ravi` and both report a milestone, the second overwrites the
first. Give them one account each, or let one person drive. To reset between
visitors:

    pkill -f "uvicorn app.main:app"
    cd src/backend && rm -rf artifacts && .venv/bin/python -m app.db.seed --reset

Real identity is a phone column on `Loan` plus an OTP provider, and neither
exists. The seam is honest about it rather than hidden: every screen reads its
identity from `GET /api/me`, so an identity provider drops in without touching
a screen.

## A judge with no Bill of Quantities

Most of them, and it used to be a dead end: "no BoQ yet? see a sample report"
jumps to loan 1001's stored analysis, so the visitor watches nothing run and the
agents never fire for them.

There is now a **Use our sample BoQ** button beside the file chooser on
`/owner/onboarding`. It fetches `public/sample/sample-boq.pdf` — the same
40-line quote the recorded runs were captured against — and hands it to the
wizard as though the visitor had chosen it, so the upload, the analysis and the
Analyzing screen are all genuinely theirs. In live mode that is a real run: five
agents, about two minutes, about ₹3.81.

The sample is also just a URL, so a judge can download it and upload it by hand
if they would rather see the file first.

## The measurement worth quoting

Judges ask how you know it works. There is an answer, and it costs nothing to
reproduce:

```bash
src/agents/.venv/bin/python scripts/synthetic_boqs.py score
```

Forty synthetic BoQs carrying 81 planted defects, scored against the grounding
tools with Gemini made unreachable — `google.genai.Client` is replaced with a
stub that raises, so a model call is impossible rather than merely unintended.
It reports **100% precision and recall** on rate outliers, missing scope,
front-loaded payment terms and GST silence, and **95% benchmark coverage** (826
of 866 priced items).

Two caveats to offer before they are asked. `UNDERSPECIFIED` is excluded from
the score, because judging a specification too vague is a model judgement no
tool makes. And the eval measures the grounded half only — whether Gemini
correctly extracts 40 line items from a PDF is not measurable without paid runs.

## Why there is no RAG here

Asked often enough to prepare for. The BoQ is two pages; it fits in one prompt
whole. An audit must check *every* priced line, and top-k retrieval is lossy by
design — a silently skipped line is an unchecked rate. And the benchmark lookup
is a SQL join on a 62-row table, which gives the property a credit officer
needs: every flag names the row that caused it. An embedding match that is wrong
is silent and unexplainable.

RAG would be the right tool for querying the full CPWD DSR — thousands of pages,
rather than the 30 items someone pre-extracted from it. That is post-hackathon.

## Screens beyond the demo path

Built: `/`, `/login`, `/owner/onboarding`, `/owner/loans/1001/analyzing`.
Preview (real layout, marked with a "Preview" pill): `/owner/loans/1001/boq/revise`,
`/boq/rev/2`, `/progress`, `/progress/report`, `/changes`, `/bank/contractors`,
`/bank/setup`.
