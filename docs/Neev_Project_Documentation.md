# Neev (नींव)

*The home builder's side of the table.*

**One liner.** Your contractor has priced four hundred houses. You're pricing
one. Neev reads your Bill of Quantities, flags what's inflated, missing or
vaguely worded, then keeps checking it against real site progress through every
loan disbursement until the house is finished.

*Neev — नींव — is the foundation of a building. It is also the first
construction stage the system verifies.*

**Repository:** https://github.com/vaishnavigurram6-ui/neev

> **This file is the source for the Patchamomma Touchpoint 3 Q7 documentation
> link.** That question requires a *Google Docs* link, shared "anyone with the
> link", carrying three sections beyond the title — project description, project
> use case, architecture diagram. The three headings below are those three, in
> that order and with those names.
>
> To produce the Google Doc: create it **in the account you are submitting
> from**, then paste this content in. Two things that caught me out doing it
> once — Google's HTML importer does **not** fetch remote `<img>` sources, so
> insert each figure by hand (*Insert → Image → By URL*, or drag the PNG from
> `figures/`); and bold inside a table cell can survive as literal `**`, so keep
> table cells plain.

---

## 1. Project description

### 1.1 What it is

Neev is a two-sided web application over a five-agent Google ADK pipeline. It
reads the document at the centre of a self-construction home loan — the Bill of
Quantities — and then keeps checking that document against what is actually
built, at every disbursement, until the house is finished.

The borrower gets their contract read line by line before they sign it. The
lender gets their whole book ranked by exposure and, for each disbursement, the
site photographs beside the milestone that was claimed. Both sides read one
document and one set of numbers. That is the design: the disputes this prevents
are disputes about what was agreed.

### 1.2 The five agents

| Agent | What it does | Grounded in |
|---|---|---|
| boq_analyst | Prices every line item; flags RATE_OUTLIER, MISSING_SCOPE, UNDERSPECIFIED, FRONT_LOADED and GST_SILENT | BigQuery benchmark lookups, locality-adjusted |
| cost_estimation | Prices the scope that is absent, and the gap against the sanctioned amount | BigQuery metro price table, then arithmetic |
| visual_inspector | Reads site photographs and decides which construction stage they actually show, with banded confidence and a human-review fallback | Gemini vision, zero-shot |
| disbursal_risk | Exposure ratio = disbursed ÷ verified value in place; cost-to-complete gap; RELEASE / HOLD / ESCALATE | Pure arithmetic — no model call produces any figure |
| explainer | Writes the finding twice — once for the borrower, once for the credit officer | Only the numbers the four agents above produced |

### 1.3 The rule the whole build follows

**No number on any screen comes from model memory.** Every figure traces to a
tool call. The consequences are deliberate, and visible in the product:

- A line item with no benchmark is **withheld**, not guessed at.
- A photograph the inspector cannot assess produces **no measurement**, and
  therefore no cost-to-complete figure. We shipped a bug where a fully-disbursed
  loan displayed a ₹35,95,327 shortfall nobody had measured; the fix was to make
  the *absence* of a measurement propagate rather than default to zero.
- Benchmarks that are still provisional say so on screen.

A system that invents a shortfall is worse than one that says nothing, because a
credit officer would act on it.

---

## 2. Project use case

### 2.1 Who this is for

A large share of Indian housing finance is **self-construction**: the borrower
already owns the plot — often inherited, often semi-urban — and borrows to build
on it. Affordable-housing finance companies do substantial business in this
segment.

The person at the centre of it builds **one house in their lifetime**. Their
contractor has built hundreds.

![The asymmetry the product exists to close](../figures/fig0_problem.png)

*Figure 1 — The asymmetry the product exists to close.*

### 2.2 Where the asymmetry lives

It lives in the **Bill of Quantities** — the line-item breakdown of every
activity in the build, with quantities and rates. A complete BoQ for a 2,000
sqft independent house runs to roughly 80–150 line items across 12–18 sections.

The BoQ is not paperwork. It is the contract. It determines what "branded
fittings" actually means, what is inside scope and what will later be billed as
an extra, and what the owner can point to when a dispute arises.

Published guidance for Indian homeowners identifies the same failure modes every
time:

| Red flag | What it enables |
|---|---|
| No brand or model named | Material substitution with cheaper equivalents |
| No IS standard cited | Sub-grade material, no recourse |
| Vague item descriptions | Scope argued after work has started |
| Lump-sum lines with no breakdown | Unverifiable pricing |
| No GST treatment stated | An unbudgeted 12–18% at settlement |
| Implausibly low headline rate | The low-bid trap — margin recovered via change orders |

A well-documented specific case: steel overcharging in Indian residential
construction usually happens not through the rate but through **weight and grade
confusion** — Fe 415 against Fe 500 against Fe 500D. Higher grade means fewer
kilograms for the same strength. An owner who does not know this cannot detect
it.

### 2.3 Why existing help does not work

There is a great deal of *content* teaching homeowners to audit their own BoQ —
red-flag checklists, line-by-line walkthroughs, free spreadsheet templates.
Every one of them assumes the owner will manually audit 80–150 technical line
items, in a domain they will encounter exactly once, under time pressure from a
contractor waiting on a signature.

**The knowledge exists. The person who needs it cannot apply it.** That is the
gap Neev fills.

### 2.4 What happens if nobody reads the document

The failure surfaces months later, when nothing can be done about it.

- **For the owner** — funds exhausted before the structure is habitable. A
  half-built house is worth *less* than the bare plot was, because clearance now
  costs money. By the time it is obvious there is no leverage left and no room
  to re-scope.
- **For the lender** — money disbursed against work that does not exist, or
  against a budget that was never going to complete. If the borrower walks, the
  lender holds an unfinished structure that is security for nothing.

Both failures trace back to the same document, unread. And it is not a rare
document: self-construction is a substantial share of affordable-housing
lending, and every one of those loans has a BoQ nobody audited line by line.

### 2.5 The four checkpoints

![Neev across the build lifecycle](../figures/fig1_lifecycle.png)

*Figure 2 — Neev across the build lifecycle: four checkpoints on one contract.*

| Stage | Question answered | Who acts |
|---|---|---|
| Before signing | What in this contract is inflated, missing or vague? | Borrower |
| At sanction | Will the approved amount actually finish the house at local rates? | Borrower and lender |
| Through the build | Do the site photographs show the stage being claimed? | Lender |
| On every change | What is this extra worth against the line that was signed? | Both |

### 2.6 One document, two readers

![One document, two readers](../figures/fig2_boq_hub.png)

*Figure 3 — The same BoQ, read for the borrower and for the credit officer.*

### 2.7 What the lender sees

![What the lender gets](../figures/fig4_bank.png)

*Figure 4 — The book ranked by exposure, and the evidence behind each release
decision.*

---

## 3. Architecture diagram

![The five-agent ADK pipeline](../figures/fig3_pipeline.png)

*Figure 5 — The five-agent ADK pipeline. Each agent writes one output_key; the
next reads it.*

### 3.1 The pipeline, and how state moves

```
BoQ pdf + site photos + loan context
   |
   v
boq_analyst        flags: RATE_OUTLIER, MISSING_SCOPE, UNDERSPECIFIED,
   |               FRONT_LOADED, GST_SILENT
   |  output_key:  boq_analysis
   v
cost_estimation    expected cost, completed-value estimate, sanction gap
   |  output_key:  cost_estimate
   v
visual_inspector   observed stage, banded confidence, needs_human_review
   |  output_key:  inspection
   v
disbursal_risk     exposure ratio, cost-to-complete gap,
   |               RELEASE / HOLD / ESCALATE
   |  output_key:  risk_assessment
   v
explainer          owner_view + officer_view
      output_key:  explanation
```

A Google ADK `SequentialAgent`. Each agent writes one `output_key` into shared
session state and the next reads it, so the explainer can only speak about
numbers the four agents before it actually produced. Every model call carries
retry options — six attempts, exponential backoff with jitter — because one run
is five-plus calls and a 3% per-call failure rate compounds rather than
averages.

### 3.2 Deployment topology

```
                    browser
                       |  HTTPS
                       v
        +--------------------------------+
        |  neev-web   (Cloud Run)        |  Next.js 16 standalone,
        |  min-instances 0               |  server components + actions
        +--------------------------------+
                       |  server-to-server, private
                       |  NEEV_API_BASE never reaches the browser,
                       |  so there is no CORS configuration at all
                       v
        +--------------------------------+
        |  neev-api   (Cloud Run)        |  FastAPI + SQLAlchemy + SQLite,
        |  min-instances 1, max 1        |  23 API paths
        +--------------------------------+
             |                      |
             v                      v
        Vertex AI              BigQuery
        gemini-3.7-flash       dataset: buildguard_data
        5 agents via ADK       rate_benchmarks, metro_city_prices,
                               loan_history, draw_schedule,
                               portfolio_hotlist (view)
```

`max-instances 1` is a correctness requirement rather than a cost one: SQLite
lives on the instance's own disk, so a second instance would be a second
database. The runtime service account holds `aiplatform.user`,
`bigquery.jobUser` and `bigquery.dataViewer`, and nothing more. Region
`asia-south1`.

A deployment authenticates to **Vertex AI** as the service account rather than
with an API key, and that is a cost decision: AI Studio's free tier allows 20
`generateContent` requests per day per model — about two analyses — while Vertex
runs the same models against the project's billing account, which is where the
hackathon credits are. Three environment variables, no code change.

### 3.3 Data sources

| Table | Size | Origin | Feeds |
|---|---|---|---|
| metro_city_prices | 32,963 listings, 6 metros, 1,776 localities | Kaggle | cost_estimation |
| rate_benchmarks | 30 items | CPWD DSR 2023-derived, Hyderabad-factored. Still marked provisional in the data, and the screens say so | boq_analyst |
| loan_history | LTV to default-rate bands | Kaggle Loan_Default, 148,670 mortgages. Used only as a lookup prior and never trained on: the dataset has fatal target leakage | disbursal_risk |
| draw_schedule | 40 tranches, 10 loans | Synthetic — no public dataset of bank disbursement ladders exists | disbursal_risk |

### 3.4 The fixture seam

One interface, `PipelineRunner`, with two implementations: a live runner that
calls Vertex, and a fixture runner that replays a recorded run. `NEEV_MODE`
selects between them and is read in exactly one place in the backend, which a
test enforces.

The ten seeded loans are **real recorded pipeline runs**, not mockups —
captured through `scripts/record_golden_run.py` and validated against the same
schemas a live run must emit, which is what stops a recorded run and a live one
from drifting apart. The raw ADK session state for each is committed, saved
before parsing, so a capture can be re-parsed at no cost. Two of the eight
synthetic cases reached ESCALATE on their own, because the visual inspector
disagreed with the stage that was claimed.

### 3.5 Engineering guardrails

| Concern | How it is handled |
|---|---|
| Tests must never bill | An autouse fixture blocks outbound sockets; 60 offline tests run with no credentials at all |
| A stray live mode | NEEV_MODE=live additionally requires NEEV_ALLOW_BILLED_CALLS=1, and an unrecognised mode falls back to fixture |
| A public URL spending money | Per-loan and per-service daily analysis caps, enforced server-side |
| API drift | A checked-in OpenAPI contract fails the suite when the API changes without being regenerated |
| A two-minute analysis looking stalled | Server-sent phase events with a 15-second heartbeat |
| Cross-borrower access | Authorization is dependency-injected per loan: a borrower reading another borrower's contract gets 403, and only a credit officer can read the book |
| Uploads | 10 MB cap, PDF envelope validation, image decode-and-verify, decompression-bomb guard, and evidence served only through an authorizing endpoint rather than a public path |

**337 automated tests:** 264 backend, 60 offline, 13 frontend, plus typecheck,
lint and a production build. Both container images were built and run as a pair
locally before deploying.

---

## 4. Stack

| Layer | What |
|---|---|
| Agents | Google Agent Development Kit — SequentialAgent, five agents sharing state via output_key. Model gemini-3.7-flash on Vertex AI, with retry options on every call. |
| Grounding | Plain Python tools: BigQuery benchmark lookups and pure-arithmetic risk math. No figure on any screen comes from model memory. |
| Backend | Python 3.11, FastAPI, SQLAlchemy ORM, SQLite. 23 API paths. |
| Frontend | Next.js 16 App Router, React server components, server actions, Tailwind v4. 17 routes. |
| Auth | Username and password. Provisioned demo accounts share one password from the environment; self-created accounts are hashed with hashlib.scrypt. Sign-up creates borrowers only — a credit officer's access to the whole book is never self-served. |
| Google Cloud | Vertex AI, Cloud Run, Cloud Build, Artifact Registry, BigQuery, Secret Manager, IAM. |

---

## 5. What is honestly not done

Stated here rather than left for a reviewer to discover:

- **The benchmark rates are provisional.** They are CPWD DSR 2023-derived and
  Hyderabad-factored, but not independently verified line by line. The
  `verified` column in the data says so, and so do the screens.
- **The database is ephemeral.** SQLite lives on the Cloud Run instance disk and
  is re-seeded from the repository on every cold start, so anything a visitor
  creates lasts as long as the instance. Moving to Cloud SQL is a
  connection-string change — the ORM means no query would change.
- **No identity verification.** Sign-in is a username and a password, not a
  KYC'd identity. The seam for a real provider is a single endpoint that every
  screen already reads its own identity from.
- **Not a trained model.** The LTV bands are a lookup prior taken from a public
  dataset that must never be fit, because it has fatal target leakage. We took
  the bands and left the dataset alone.
- **Hindi, Telugu and read-aloud are not built.** The interface says "coming"
  rather than implying they work.
