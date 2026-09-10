# Neev (नींव)

**Your contractor has priced four hundred houses. You're pricing one.**

Neev reads the Bill of Quantities at the centre of a self-construction home
loan, flags what is inflated, missing or vaguely worded, and then keeps checking
that same contract against real site progress at every disbursement until the
house is finished. It has two faces — one for the family building the house, one
for the credit officer funding it — over one set of numbers.

| | |
|---|---|
| **Live app** | https://neev-web-516665930454.asia-south1.run.app |
| **Sign in** | `ravi` (flagged contract) · `prasad` (clean) · `officer` (whole book) — password `password` |
| **Repository** | https://github.com/vaishnavigurram6-ui/neev |
| **Built on** | Google ADK · Gemini 3.7 Flash on Vertex AI · Cloud Run · BigQuery |

> **How to turn this into the Q7 Google Doc.** Create the Doc **in the account
> you are submitting from**, paste this in, then insert the figures: Google's
> HTML importer does not fetch remote images. Sections 1, 2 and 3 below are the
> three the form mandates, named as it names them. `figures/fig3_pipeline.png` in
> §3 is the architecture diagram it specifically requires. Finally set sharing to
> "anyone with the link → Viewer" and check it in a private window.

---

# 1. Project description

## The moment this exists for

A family has a plot — often inherited, often on the edge of a city that grew out
to meet it. They have a sanction letter from a housing finance company. And they
have a document from a contractor: a Bill of Quantities, eighty to a hundred and
fifty lines, every activity in the build with a quantity and a rate.

Someone signs it, usually after one evening of looking at it.

That document is not paperwork. It is the contract. It decides what "branded
fittings" turns out to mean, what is inside scope and what will be billed later
as an extra, and what anyone can point at when there is an argument in month
seven. The person signing it will build **one house in their lifetime**. The
person who wrote it has built hundreds.

*[INSERT `figures/fig0_problem.png` — the asymmetry]*

## Why it is not a story about dishonesty

A contractor who has priced four hundred houses knows the fair rate for RCC in
that locality this year, which line items are usually left out and argued about
later, and how much of the money to ask for before the slab is cast. None of
that requires malice. It requires only that one side has done this before.

The clearest example is steel. Overcharging in Indian residential construction
usually happens not through the rate but through the **grade** — Fe 415 against
Fe 500 against Fe 500D. Higher-grade steel is stronger, so a correctly designed
structure needs fewer kilograms for the same result. A line reading "TMT bars"
with no grade named leaves room to supply a lower grade in a higher quantity at
a rate that looks entirely normal. The owner checks the rate, finds it
reasonable, and is right — the rate was never the problem.

Guidance for homeowners exists in abundance: red-flag checklists, line-by-line
walkthroughs, spreadsheet templates. Every one assumes the owner will manually
audit a hundred-odd technical lines against local benchmarks they do not have,
hunting for scope that is *absent* — which is harder than finding scope that is
wrong, because absence has nothing on the page to catch the eye. **The knowledge
exists; the person who needs it cannot apply it.**

## What Neev does

It reads the document instead — every line, against what that item actually
costs in that locality — and then keeps reading it, because a construction loan
is not disbursed once. It goes out in tranches against milestones, and each
milestone is a moment where somebody says "this stage is done, release the
money."

*[INSERT `figures/fig1_lifecycle.png` — four checkpoints on one contract]*

| Checkpoint | The question actually being answered |
|---|---|
| **Before signing** | What in here is inflated, missing, or vague enough to be argued about later? |
| **At sanction** | Will the approved amount finish this house at local rates — not "is the budget consistent", but "does this end with a roof"? |
| **Through the build** | Do the photographs from site show the stage being claimed for payment? |
| **On every change** | What is this extra worth, measured against the line that was signed? |

## The one rule the whole build follows

> **Every number comes from somewhere checkable, and where there is nothing to
> check, the system says nothing.**

An item with no benchmark is withheld, not estimated. A photograph the inspector
cannot read produces no measurement, and therefore no figure derived from one.
Provisional data says on screen that it is provisional.

This is not modesty for its own sake — it is the difference between a tool a
credit officer can use and one they cannot. A confident wrong number in a
lending decision is worse than a blank, because somebody acts on it. The hardest
part of this project was not getting five agents to speak; it was getting them
to stop.

---

# 2. Project use case

Two people use Neev, at different moments, over the same document. What follows
is the actual flow through the deployed app.

## 2.1 The borrower — Ravi Kumar, Plot 47, Kompally

**Sign in as `ravi`.**

**Before signing.** Ravi uploads his contractor's quote — 40 line items,
₹28,47,930. Five agents run against it in about two minutes. What comes back is
not a score:

- **14 flags** — 3 rate outliers, 3 items of missing scope, 6 vague
  specifications
- The RCC line quoted at ₹9,800/cum where the Kompally benchmark is ₹8,036 —
  **22% above**, stated with both numbers
- **₹1,42,654 of scope absent** — external plaster and terrace waterproofing are
  simply not in the document
- **45% of the money due before the slab**, which is ₹12,81,568 before there is
  meaningful structure to show for it
- **14 items withheld**, because no benchmark exists for them and a guess would
  be worse than a gap

Then the part that matters: *Before you sign* gives him plain-language text he
can send his contractor **himself**. Neev does not message anyone on his behalf.
The point is that he negotiates from a position of knowing, not that software
negotiates for him.

**At sanction.** His sanction is ₹28,00,000 against a quote of ₹28,47,930, and
benchmark re-pricing puts the real cost higher still. The question "will this
finish the house?" gets a number instead of an assurance.

**Through the build.** At each milestone Ravi photographs the site and reports
it. The visual inspector reads the frames and decides what stage they actually
show — and if it cannot tell, it says so and escalates to a human rather than
guessing.

**On every change.** When the contractor proposes a kitchen platform upgrade,
the change is priced against the line that was signed: granite at ₹18,850
against quartz at ₹35,100. Ravi can counter with a number.

## 2.2 The credit officer — the whole book

**Sign in as `officer`.**

**The portfolio.** Ten loans ranked by exposure, worst first — 1004 at 1.71,
1009 at 1.13, 1001 at 1.11. Exposure is disbursed ÷ verified value in place, so
a ratio above 1 means money has gone out ahead of what is standing on site.

**One loan.** Drill into 1001 and the disbursement schedule shows every tranche:
the milestone it pays for, what it releases, and where it stands.

**One decision.** Open the tranche awaiting an answer and the screen carries the
borrower's site photographs beside the milestone claimed, the exposure
arithmetic, the cost-to-complete gap, and a recommendation — RELEASE, HOLD or
ESCALATE — with the reasons that produced it. Loans 1004 and 1009 reached
ESCALATE on their own: the inspector disagreed with the stage that was claimed.

An officer can also create their own borrower account at `/signup` and take a
contract through from an empty state.

## 2.3 Why both sides, over one document

The disputes this prevents are disputes about **what was agreed**. So it is not
enough for the borrower to have a good reading of the contract, or the lender to
have one — they must be looking at the *same* reading.

*[INSERT `figures/fig2_boq_hub.png` — one document, two readers]*

The borrower gets their contract read line by line and a note to send. The
lender gets the same findings, plus the book ranked by exposure and the
photographs next to the claim. One document, one set of numbers, and a specific
conversation instead of a vague one.

*[INSERT `figures/fig4_bank.png` — what the lender gets]*

## 2.4 What happens when nobody reads it

The failure never shows up at signing. It shows up months later, when nothing
can be done.

**For the family:** the money runs out before the house is habitable — and a
half-built structure is worth *less* than the bare plot was, because clearing it
costs money. By then there is no leverage and no room to re-scope, and they are
still paying rent somewhere else.

**For the lender:** money has gone out against work that does not exist, or
against a budget that was never going to complete. If the borrower walks, the
security is an unfinished building.

Both trace to the same document, unread — and it is not a rare document.
Self-construction is a substantial share of affordable-housing lending in India.

---

# 3. Architecture diagram

*[INSERT `figures/fig3_pipeline.png` — the five-agent ADK pipeline]*

## 3.1 Five agents, one direction of state

A Google ADK `SequentialAgent`. Each agent writes one `output_key` into shared
session state and the next reads it, so the explainer can only speak about
numbers the four before it actually produced.

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

| Agent | Its job | What grounds it |
|---|---|---|
| boq_analyst | Prices every line; raises the five flag types | BigQuery benchmark lookups, locality-adjusted |
| cost_estimation | Prices absent scope; the gap against sanction | BigQuery metro price table, then arithmetic |
| visual_inspector | Which construction stage the photographs show | Gemini vision, zero-shot, banded confidence |
| disbursal_risk | Exposure ratio, cost to complete, the verdict | Pure arithmetic — no model call yields any figure |
| explainer | The same finding written for two readers | Only what the four above produced |

Every model call carries retry options — six attempts, exponential backoff with
jitter — because one run is five-plus calls, and a 3% per-call failure rate
compounds rather than averages.

## 3.2 How the rule is enforced in code

The restraint described in §1 is structural, not a prompt instruction:

- `pipeline_parse.py` raises `Unassessable` when the inspector returns
  `matches_claim: null` — a null is not a "no".
- Cost-to-complete is written only when something was actually measured. A
  fully-disbursed loan once displayed a **₹35,95,327 shortfall nobody had
  measured**, because an absent measurement defaulted to zero instead of
  propagating as absent. The fix made absence a value that flows.
- `OBSERVABLE_STAGES` gates the evidence: a stage outside it produces no
  measurement and no derived figure.
- Unbenchmarked line items are withheld from the flag list rather than shown as
  clean, so "unflagged" never silently means "unchecked".

## 3.3 Deployment

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

Region `asia-south1`. `max-instances 1` is a correctness requirement rather than
a cost one: SQLite lives on the instance's own disk, so a second instance would
be a second database. The runtime service account holds `aiplatform.user`,
`bigquery.jobUser` and `bigquery.dataViewer`, and nothing more.

The deployment authenticates to **Vertex AI** as that service account rather
than with an API key, and that is a cost decision: AI Studio's free tier allows
20 `generateContent` requests per day per model — about two analyses — while
Vertex bills the project's billing account. Three environment variables, no code
change.

## 3.4 Data, and where it comes from

| Table | Size | Origin | Feeds |
|---|---|---|---|
| metro_city_prices | 32,963 listings · 6 metros · 1,776 localities | Kaggle | cost_estimation |
| rate_benchmarks | 30 items | CPWD DSR 2023-derived, Hyderabad-factored — still marked provisional in the data, and on screen | boq_analyst |
| loan_history | LTV → default-rate bands | Kaggle Loan_Default, 148,670 mortgages. Used **only** as a lookup prior, never trained on: the dataset has fatal target leakage | disbursal_risk |
| draw_schedule | 40 tranches · 10 loans | Synthetic — no public dataset of bank disbursement ladders exists | disbursal_risk |

## 3.5 The fixture seam

One interface, `PipelineRunner`, with two implementations: a live runner that
calls Vertex, and a fixture runner that replays a recorded run. `NEEV_MODE`
chooses, and is read in exactly one place — enforced by a test.

The ten seeded loans are **real recorded runs**, not mockups: captured through
`scripts/record_golden_run.py` and validated against the same schemas a live run
must emit, which is what stops a recording and a live run from drifting apart.
The raw ADK session state for each is committed, saved *before* parsing, so a
capture can be re-parsed at no cost.

## 3.6 Guardrails

| Concern | How it is handled |
|---|---|
| Tests must never bill | An autouse fixture blocks outbound sockets; 60 offline tests run with no credentials at all |
| A stray live mode | `NEEV_MODE=live` additionally requires `NEEV_ALLOW_BILLED_CALLS=1`; an unrecognised mode falls back to fixture |
| A public URL spending money | Per-loan and per-service daily analysis caps, enforced server-side |
| API drift | A checked-in OpenAPI contract fails the suite if the API changes without regeneration |
| A two-minute analysis looking stalled | Server-sent phase events with a 15-second heartbeat |
| Cross-borrower access | Authorization is injected per loan: one borrower reading another's contract gets 403, and only an officer can read the book |
| Uploads | 10 MB cap, PDF envelope validation, image decode-and-verify, decompression-bomb guard; evidence served only through an authorizing endpoint |

**337 automated tests** — 264 backend, 60 offline, 13 frontend — plus typecheck,
lint and a production build. Both container images were built and run as a pair
locally before either was deployed.

---

# 4. Stack

| Layer | What |
|---|---|
| Agents | Google ADK `SequentialAgent`, five agents sharing state via `output_key`; `gemini-3.7-flash` on Vertex AI |
| Grounding | Plain Python tools — BigQuery benchmark lookups and pure-arithmetic risk math |
| Backend | Python 3.11, FastAPI, SQLAlchemy, SQLite — 23 API paths |
| Frontend | Next.js 16 App Router, server components and actions, Tailwind v4 — 17 routes |
| Auth | Username and password. Provisioned accounts share one password from the environment; self-created accounts use `hashlib.scrypt`. Sign-up creates borrowers only — officer access to the whole book is never self-served |
| Google Cloud | Vertex AI, Cloud Run, Cloud Build, Artifact Registry, BigQuery, Secret Manager, IAM |

---

# 5. What is honestly not built

Stated here rather than left for a reviewer to find.

- **The benchmark rates are provisional.** CPWD DSR 2023-derived and
  Hyderabad-factored, but not independently verified line by line. The
  `verified` column says so, and so do the screens.
- **The database is ephemeral.** SQLite sits on the Cloud Run instance disk and
  is re-seeded from the repository on every cold start, so anything a visitor
  creates lasts as long as the instance. Cloud SQL is a connection-string
  change; the ORM means no query would move.
- **No identity verification.** Sign-in is a username and password, not a KYC'd
  identity. The seam for a real provider is one endpoint every screen already
  reads its identity from.
- **Nothing is trained.** The LTV bands are a lookup prior from a public dataset
  that must never be fit, because it has fatal target leakage. We took the bands
  and left the dataset alone.
- **Hindi, Telugu and read-aloud are not built.** The interface says "coming"
  rather than implying they work.
