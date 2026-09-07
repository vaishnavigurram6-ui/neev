# Neev — demo runbook

*Written 2026-08-28. Everything here runs in fixture mode: no Gemini, no BigQuery,
no billed Google call. There is no `google` package in the backend venv at all,
so nothing can bill even by accident.*

## Start it

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

**Staged.** The pipeline is not driving the screens *live*. The app replays a
recorded run rather than analysing on upload, so **whatever PDF you upload, you
will see loan 1001's recorded analysis.** Say so rather than letting a judge
discover it. Wiring live analysis to the upload path needs an artefact store and
the ADK in the backend image; the seam is built and `get_runner()` is the only
place that would change.

**Not built.** Real OTP, translation, text-to-speech, marked-up PDF export,
WhatsApp sending. Each renders as a disabled control that says why, rather than
a dead button that lies.

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
