# Neev (नींव)

**Your contractor has priced four hundred houses. You're pricing one.**

*Pronounced "neev" — one syllable, like leave with an n. नींव is Hindi for a
building's foundation: the first thing built, and the first thing anyone checks
before building on top of it.*

| | |
|---|---|
| **What it is** | A two-sided web app over five Google ADK agents. It reads the Bill of Quantities behind a self-construction home loan, flags what's inflated, missing or vaguely worded, then keeps checking that contract against site photographs at every disbursement. |
| **Live app** | https://neev-web-516665930454.asia-south1.run.app |
| **Sign in** | `ravi` (flagged contract) · `prasad` (clean) · `officer` (whole book) — password `password` |
| **Repository** | https://github.com/vaishnavigurram6-ui/neev |
| **Stack** | Google ADK · Gemini 3.7 Flash on Vertex AI · Cloud Run · BigQuery · FastAPI · Next.js 16 |
| **Proven** | One live run on the deployed service: 40 line items, 14 flags, 200 seconds, **₹3.81**. 338 automated tests. |

---

# 1. Project description

A family has a plot, a sanction letter, and a document the contractor dropped
off: a Bill of Quantities, eighty to a hundred and fifty lines, every job in the
build with a quantity and a rate. Somebody signs it after one evening of looking
at it. That document isn't paperwork — it's the contract, and it's the only
thing anyone can point at when there's an argument in month seven. **The person
signing it will build one house in their life. The person who wrote it has built
hundreds.**

It isn't a story about dishonesty. Steel is the clearest case: overcharging
usually isn't the rate, it's the **grade**. Fe 415, Fe 500, Fe 500D — stronger
steel needs fewer kilos for the same structure, so a line reading "TMT bars"
with no grade named leaves room for a weaker grade in a higher quantity at a
rate that looks entirely normal. The owner checks the rate, finds it reasonable,
and is right. The rate was never the problem. And no amount of guidance fixes
that, because all of it assumes someone will audit a hundred technical lines
against benchmarks they don't have, hunting for scope that's *absent* — harder
than finding scope that's wrong.

So Neev reads the document instead, and keeps reading it, because a construction
loan is disbursed in tranches and each one is a moment where somebody claims a
stage is done:

| Checkpoint | The question answered |
|---|---|
| **Before signing** | What's inflated, missing, or vague enough to be argued about later? |
| **At sanction** | Will the approved amount finish this house at local rates — does this end with a roof? |
| **Through the build** | Do the site photographs show the stage being claimed? Answered while the stage is happening, not in a report afterwards. |
| **On every change** | What's this extra worth against the line that was signed? |

**The one rule the whole build follows:** every number comes from somewhere
checkable, and where there's nothing to check, the system says nothing. An item
with no benchmark is withheld, not estimated; a photograph the inspector can't
read produces no measurement, and so no figure derived from one. A confident
wrong number in a lending decision is worse than a blank, because somebody acts
on it.

---

# 2. Project use case

**The borrower.** Signed in as `ravi`, he uploads his contractor's quote: 40
line items, ₹28,47,930. Five agents run in about two minutes. These are the
figures the deployed service actually produced, all checkable on the live app:

| Finding | Detail |
|---|---|
| 14 flags | across five types — rate outliers, missing scope, underspecified items, front-loaded payment terms, GST silence |
| RCC at ₹9,800/cum | against a ₹8,036 Kompally benchmark — **22% over**, with both numbers shown |
| ₹1,42,654 absent | external plaster and terrace waterproofing aren't in the document at all |
| 45% due before the slab | ₹12,81,568 before there's meaningful structure |
| 14 items withheld | no benchmark exists, and a guess would be worse than a gap |

Then the part that matters: *Before you sign* gives him plain-language text he
sends his contractor **himself**. Neev messages nobody on his behalf — the point
is that he negotiates from a position of knowing. Through the build he
photographs each milestone and the inspector decides which stage the frames
show, escalating to a human where it can't tell. Every change order is priced
against the line that was signed.

**The credit officer.** Signed in as `officer`: ten loans ranked by exposure,
worst first — disbursed ÷ verified value in place, so above 1 means money went
out ahead of what's standing on site. Loans 1004 (1.71) and 1009 (1.13) both
reached ESCALATE unprompted, because the inspector disagreed with the stage
claimed. Opening a tranche gives the decision screen: the borrower's
photographs beside the milestone claimed, the exposure arithmetic, the
cost-to-complete gap, and RELEASE / HOLD / ESCALATE with its reasons.

**Why both sides, over one document.** The disputes this prevents are disputes
about *what was agreed*, so it isn't enough for the borrower to have a good
reading of the contract, or the lender to have one. They have to be reading the
same one.

---

# 3. Architecture diagram

![The five-agent ADK pipeline](../figures/fig3_pipeline.png)

A Google ADK `SequentialAgent`. Each agent writes one `output_key` into shared
state and the next reads it: `boq_analyst` prices every line against BigQuery
benchmarks and raises the flags, `cost_estimation` prices absent scope and the
sanction gap, `visual_inspector` reads the site photographs with Gemini vision,
`disbursal_risk` computes exposure and the verdict in pure arithmetic, and
`explainer` writes the finding twice — once for the family, once for the
officer. Because each agent only sees what the ones before it wrote, the
explainer can't invent a number. **No model call produces any figure on any
screen.** Every call carries six retry attempts with backoff, since one run is
five-plus calls and a 3% per-call failure rate compounds rather than averages.

**How the rule is enforced** — structurally, not as a prompt instruction:

- `pipeline_parse.py` raises `Unassessable` when the inspector returns
  `matches_claim: null`. A null isn't a "no".
- Cost-to-complete is written only when something was measured. A
  fully-disbursed loan once displayed a **₹35,95,327 shortfall nobody had
  measured**, because an absent measurement defaulted to zero instead of
  propagating as absent. The fix made absence a value that flows.
- Unbenchmarked items are withheld from the flag list rather than shown clean,
  so "unflagged" never quietly means "unchecked".

**Deployment.** Two Cloud Run services in `asia-south1`: `neev-web` (Next.js)
calls `neev-api` (FastAPI + SQLite) server-to-server, so the backend's address
never reaches the browser and there's no CORS configuration at all.
`max-instances 1` on the backend is a correctness requirement rather than a cost
one — SQLite is on the instance disk, so a second instance would be a second
database. It reaches Gemini through Vertex AI as its own service account rather
than an API key, because AI Studio's free tier allows about two analyses a day
while Vertex bills the project account.

**Costs, measured not estimated:** ₹3.81 a full analysis (down from ₹26.08,
once the benchmark lookups were batched instead of each billing BigQuery's 10 MB
minimum), ₹1.50 a milestone check, ₹740 for a fortnight of warm backend, and a
worst case of about ₹229 a day under caps of 12 analyses per loan and 60 per
service — which on an `--allow-unauthenticated` URL is the only thing between a
crawler and the billing account. No upkeep beyond that, because **nothing is
trained**: keeping the pricing current is a CSV reload, which is what makes a
second city plausible.

| Data | Origin |
|---|---|
| `metro_city_prices` | Kaggle — 32,963 listings, 6 metros, 1,776 localities |
| `rate_benchmarks` | CPWD DSR 2023-derived, Hyderabad-factored. Marked provisional in the data, and on screen |
| `loan_history` | Kaggle Loan_Default, 148,670 mortgages — used **only** as an LTV lookup prior, never trained on: the dataset has fatal target leakage |
| `draw_schedule` | Synthetic. No public dataset of bank disbursement ladders exists |

**What you can check.** The ten seeded loans are real recorded runs, not
mockups — captured through `scripts/record_golden_run.py` and validated against
the same schemas a live run must emit. Nothing in the test suite can spend
money: an autouse fixture blocks outbound sockets, live mode needs two separate
switches, and authorization is injected per loan, so one borrower reading
another's contract gets a 403. **338 tests** — 265 backend, 60 offline, 13
frontend — plus typecheck, lint and a production build.

And the accuracy claim is measurable, not asserted. `fixtures/synthetic/` holds
40 generated quotes whose defects are known because the generator planted them,
so `src/agents/.venv/bin/python scripts/synthetic_boqs.py score` grades the
grounding tools against ground truth — no model, no cost, half a minute. Today:
**100% recall and precision** on rate outliers, absent scope, front-loading and
GST silence, over a benchmark table that priced 826 of 866 items. The rest are
wordings nobody wrote a rate for, and that gap is exactly what gets withheld
rather than passed as clean.

---

# 4. Where it stands

Four things aren't finished. None is load-bearing for what the app does today,
and each has a specific next step.

- **The benchmark rates aren't audited line by line.** They're CPWD-derived, and
  the data and the screens both say provisional. Closing it is a check against
  the published DSR — the benchmarks are a BigQuery table, so better numbers are
  a reload.
- **The database is disposable.** SQLite on the instance disk is what makes the
  demo reproducible, but what a visitor creates lives as long as the instance.
  Point `DATABASE_URL` at Cloud SQL and it's durable; everything goes through
  the ORM, so not one query moves.
- **Sign-in isn't verified identity.** Every screen already reads who it's
  talking to from one endpoint, so a real provider drops in behind that seam.
- **It's English only.** The interface says "coming" for Hindi and Telugu rather
  than pretending — and given who this is for, that's the first thing worth
  building next.

What's there today: a borrower uploads a quote and gets it read line by line
against local rates, every flag naming the number it was measured against, plus
a note they can send themselves. An officer opens the whole book by exposure
and, for any disbursement, sees the photographs beside the milestone claimed,
the arithmetic, and a recommendation with its reasons. Both are reading the same
document — running now, on live agents, at
[neev-web-516665930454.asia-south1.run.app](https://neev-web-516665930454.asia-south1.run.app).
