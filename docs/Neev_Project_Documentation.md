# Neev (नींव)

**Your contractor has priced four hundred houses. You're pricing one.**

Neev reads the Bill of Quantities sitting at the centre of a self-construction
home loan, flags what's inflated, missing or vaguely worded — and then keeps
checking that same contract against what's actually been built, at every
disbursement, until the house is finished. It has two faces: one for the family
building the house, one for the credit officer funding it. Both looking at the
same numbers.

| | |
|---|---|
| **Live app** | https://neev-web-516665930454.asia-south1.run.app |
| **Sign in** | `ravi` (flagged contract) · `prasad` (clean) · `officer` (whole book) — password `password` |
| **Repository** | https://github.com/vaishnavigurram6-ui/neev |
| **Built on** | Google ADK · Gemini 3.7 Flash on Vertex AI · Cloud Run · BigQuery |

> **Turning this into the Q7 Google Doc.** Make the Doc **in whichever account
> you're submitting from**, paste this in, then add the figures by hand —
> Google's HTML importer won't fetch remote images. Sections 1, 2 and 3 are the
> three the form asks for, named the way it names them, and
> `figures/fig3_pipeline.png` in §3 is the architecture diagram it specifically
> wants. Last step: set sharing to "anyone with the link → Viewer" and open it
> in a private window to check.

---

# 1. Project description

## The moment this exists for

Picture a kitchen table on a weekday evening.

A family's sitting at it. They've got a plot — maybe it came down from a
grandparent, maybe it's on the edge of a city that's been growing out toward it
for twenty years. They've got a sanction letter from a housing finance company,
which took months to get. And they've got a document the contractor dropped
off: a Bill of Quantities. Eighty lines. Sometimes a hundred and fifty. Every
job in the build, with a quantity and a rate beside it.

Somebody's going to sign it tonight, or maybe tomorrow. The contractor's
waiting.

Here's the thing about that piece of paper, though. It isn't paperwork. It's
*the contract*. It decides what "branded fittings" turns out to mean six months
from now. It decides what's included and what gets billed later as an extra.
And when there's an argument in month seven — and there usually is one — it's
the only thing anyone can point at.

So it matters enormously. And the person signing it will build exactly one
house in their life. The person who wrote it has built hundreds.

![The asymmetry](../figures/fig0_problem.png)

*One house against four hundred — and the gap lives in a single document.*

## Why this isn't a story about crooked builders

I want to get that out of the way early, because it's where everyone's mind
goes, and it's mostly wrong.

Think about your first ever hand of cards against someone who's played four
hundred. They're not cheating. They don't need to. They just know which way
things tend to go, and you're finding out as you play.

That's the situation. A contractor who's priced four hundred houses knows what
RCC actually costs in that neighbourhood this year. They know which line items
get quietly left out and argued about later. They know how much of the money to
ask for up front, before there's anything standing on the plot to show for it.
None of that needs bad intentions. It only needs that one person's done this
before and the other hasn't.

My favourite example is steel, because it's the one that convinced me this is a
real problem and not just a feeling.

If someone's overcharging you on steel in an Indian house build, it usually
isn't the rate. It's the **grade**. Fe 415, Fe 500, Fe 500D — stronger steel
means a properly designed structure needs fewer kilos of it to do the same job.
So a line that just says "TMT bars," with no grade written down, has quietly
left the door open: supply the weaker stuff, more of it, at a rate that looks
completely fine.

And it *does* look fine. That's what gets me. The owner checks the rate, decides
it seems about right, and they're correct — the rate was never where the money
was going.

## The advice is already out there. It just can't get through.

There's no shortage of help. Red-flag checklists, line-by-line walkthroughs,
free spreadsheet templates, and now thousands of reels and videos made by people
who genuinely know construction.

It fails in two different ways, and both are worth naming.

The **written** stuff quietly assumes you'll sit down and work through a
hundred-odd technical lines across a dozen sections, checking each rate against
local benchmarks you don't have, and spotting the things that *aren't* there —
which is so much harder than spotting something wrong, because a missing item
has nothing on the page for your eye to snag on. You can't skim for an absence.

The **videos** don't fail when you watch them. They fail months later. You watch
a reel about terrace waterproofing in February; the decision turns up on site in
September with a mason standing there asking whether you want it done now, and
you can't remember whether it said two coats or three. The knowledge went in. It
just isn't available in the ninety seconds where it would change anything.

So the knowledge exists, in enormous quantity. It just can't reach the person who
needs it, in the shape they need it, at the moment they need it. That's the gap.

## What Neev actually does

It reads the document instead. Every line, against what that item really costs in
*that* neighbourhood, this year.

And then it keeps reading it — which is the part I think matters most. Because a
construction loan doesn't get handed over in one go. It comes out in tranches
against milestones: foundation, plinth, slab, brickwork, finishing. Every one of
those is a moment where somebody says "right, this stage is done, release the
money." So the same contract can be checked again at every single one.

![Four checkpoints on one contract](../figures/fig1_lifecycle.png)

*Four checkpoints on one contract, from signing through to finishing.*

| Checkpoint | The question actually being answered |
|---|---|
| **Before signing** | What in here is inflated, missing, or vague enough to become an argument later? |
| **At sanction** | Will the approved amount actually finish this house at local rates? Not "does the budget add up", but "does this end with a roof"? |
| **Through the build** | Do the photos from site show the stage being claimed for payment? Answered while the stage is still happening, not in a report afterwards. |
| **On every change** | What's this extra worth, against the line that was signed? |

## The one rule the whole thing follows

> **Every number has to come from somewhere you can check. And where there's
> nothing to check, the system says nothing.**

An item with no benchmark gets withheld, not estimated. A photo the inspector
can't read produces no measurement — and therefore no number that depends on a
measurement. Data that's still provisional says so, on the screen, where you can
see it.

That's not modesty for its own sake. It's the whole difference between something
a credit officer can use and something they can't. A confident wrong number in a
lending decision is worse than a blank space, because somebody will act on it.

Honestly, the hardest part of building this wasn't getting five agents to talk.
It was getting them to stop.

---

# 2. Project use case

Two people use Neev, at different moments, over the same document. Here's how it
actually goes on the deployed app — you can follow along and check every number.

## 2.1 The borrower — Ravi Kumar, Plot 47, Kompally

**Sign in as `ravi`.**

**Before he signs.** Ravi uploads his contractor's quote: 40 line items,
₹28,47,930. Five agents run over it in about two minutes. What comes back isn't
a score — it's a list of specific things, each with the number it was measured
against:

- **14 flags** — 3 rate outliers, 3 bits of missing scope, 6 vague specs
- The RCC line quoted at **₹9,800/cum** where the Kompally benchmark is
  **₹8,036** — 22% over, with both numbers shown so he can argue about either
- **₹1,42,654 of scope that simply isn't in the document** — external plaster
  and terrace waterproofing
- **45% of the money due before the slab** — ₹12,81,568 before there's anything
  meaningful standing on the plot
- **14 items withheld**, because no benchmark exists for them and a guess would
  be worse than a gap

Then the bit that matters: *Before you sign* hands him plain-language text he can
send his contractor **himself**. Neev doesn't message anyone on his behalf. The
point is that *he* negotiates, from a position of knowing.

**At sanction.** His sanction is ₹28,00,000 against a quote of ₹28,47,930 — and
re-pricing at benchmark rates puts the real cost higher still. So "will this
finish the house?" gets a number instead of a reassurance.

**Through the build.** At each milestone he photographs the site and reports it.
The visual inspector reads the frames and works out which stage they actually
show. And where it can't tell, it says so and escalates to a human rather than
guessing.

**On every change.** When the contractor proposes a kitchen platform upgrade,
it's priced against the line that was signed — granite at ₹18,850 against quartz
at ₹35,100. Ravi can counter with a number.

## 2.2 The credit officer — the whole book

**Sign in as `officer`.**

**The portfolio.** Ten loans, sorted by exposure, worst first. Exposure is
disbursed ÷ verified value in place, so anything above 1 means money's gone out
ahead of what's standing on site.

| Loan | Exposure | What the screen says |
|---|---|---|
| 1004 | 1.71 | ESCALATE — the inspector disagreed with the stage claimed |
| 1009 | 1.13 | ESCALATE — reached on its own, nobody prompted it |
| 1001 | 1.11 | The golden case: flagged contract, slab stage |
| 1003 | 0.87 | Within tolerance |

**One loan.** Drill into 1001 and you get the disbursement schedule: every
tranche, the milestone it pays for, what it releases, where it stands.

**One decision.** Open the tranche that's waiting on an answer and the screen
carries the borrower's site photographs right beside the milestone claimed, the
exposure arithmetic, the cost-to-complete gap, and a recommendation — RELEASE,
HOLD or ESCALATE — with the reasons that produced it.

![What the lender gets](../figures/fig4_bank.png)

*The book ranked by exposure, and the evidence behind each release decision.*

An officer can also create their own borrower account at `/signup` and take a
contract through from an empty state, if they want to see the whole loop.

## 2.3 Why both sides, over one document

The arguments this is meant to head off are arguments about **what was agreed**.
So it's not enough for the family to have a good reading of the contract, and it
isn't enough for the lender to have one either. They both need to be looking at
the same reading.

![One document, two readers](../figures/fig2_boq_hub.png)

*The same BoQ, read once, used by both sides.*

The family sees their contract gone through line by line, plus a note they can
send. The lender sees the same findings, plus their whole book sorted by
exposure, plus the site photos sitting next to the claim. One document, one set
of numbers, and a specific conversation instead of a vague one.

## 2.4 And what happens if nobody reads it

Nothing bad happens at signing. That's what makes this so easy to skip. It shows
up months later, when there's nothing to be done.

**For the family**, the money runs out before the house is liveable — and that's
worse than it sounds, because a half-built structure is worth *less* than the
empty plot was. Clearing it costs money. By then there's no leverage left,
nothing to renegotiate with, and they're still paying rent somewhere else.

**For the lender**, money's gone out against work that isn't there, or against a
budget that was never going to reach a roof. If the borrower walks away, what's
left as security is an unfinished building.

Both trace back to the same document nobody read. And this isn't a rare edge
case — self-construction is a big slice of affordable-housing lending in India.

---

# 3. Architecture diagram

![The five-agent ADK pipeline](../figures/fig3_pipeline.png)

*Five agents in sequence. Each one writes an `output_key`; the next one reads it.*

## 3.1 Five agents, and state that only moves one way

It's a Google ADK `SequentialAgent`. Each agent writes one `output_key` into
shared session state and the next one reads it — which means the explainer at the
end can only talk about numbers the four before it actually produced. It can't
invent one, because it never sees anything else.

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
| `boq_analyst` | Prices every line; raises the five flag types | BigQuery benchmark lookups, adjusted for locality |
| `cost_estimation` | Prices the scope that's absent; the gap against sanction | BigQuery metro price table, then arithmetic |
| `visual_inspector` | Which construction stage the photographs show | Gemini vision, zero-shot, banded confidence |
| `disbursal_risk` | Exposure ratio, cost to complete, the verdict | Pure arithmetic — no model call produces any figure |
| `explainer` | The same finding, written twice for two readers | Only what the four above produced |

Every model call carries retry options — six attempts, exponential backoff with
jitter. That's not belt-and-braces: one run is five-plus calls, and a 3%
per-call failure rate compounds rather than averages.

## 3.2 How that "says nothing" rule is actually enforced

This is the part I'd point at if you only had a minute. The restraint isn't a
line in a prompt asking the model to be careful — it's structural.

- `pipeline_parse.py` raises `Unassessable` when the inspector comes back with
  `matches_claim: null`. A null isn't a "no".
- Cost-to-complete only gets written when something was actually measured. We
  shipped a bug where a fully-disbursed loan displayed a **₹35,95,327 shortfall
  nobody had measured**, because an absent measurement defaulted to zero instead
  of propagating as absent. The fix was to make absence a value that flows
  through.
- `OBSERVABLE_STAGES` gates the evidence: a stage outside it yields no
  measurement, and therefore no figure derived from one.
- Unbenchmarked line items are withheld from the flag list rather than shown as
  clean — so "unflagged" never quietly means "unchecked".

## 3.3 How it's deployed

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
                       |  so there's no CORS configuration at all
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

Region `asia-south1`. `max-instances 1` looks like a cost setting but it's
actually a correctness one: SQLite lives on the instance's own disk, so a second
instance would be a second database. The runtime service account holds
`aiplatform.user`, `bigquery.jobUser` and `bigquery.dataViewer`, and nothing
else.

The deployment talks to **Vertex AI** as that service account rather than using
an API key, and that's a cost decision. AI Studio's free tier allows 20
`generateContent` requests a day per model — about two analyses — whereas Vertex
bills the project's billing account, which is where the credits are. Three
environment variables, no code change.

## 3.4 Where the data comes from

| Table | Size | Origin | Feeds |
|---|---|---|---|
| `metro_city_prices` | 32,963 listings · 6 metros · 1,776 localities | Kaggle | `cost_estimation` |
| `rate_benchmarks` | 30 items | CPWD DSR 2023-derived, Hyderabad-factored — still marked provisional in the data, and on screen | `boq_analyst` |
| `loan_history` | LTV → default-rate bands | Kaggle Loan_Default, 148,670 mortgages. Used **only** as a lookup prior, never trained on — the dataset has fatal target leakage | `disbursal_risk` |
| `draw_schedule` | 40 tranches · 10 loans | Synthetic. There's no public dataset of bank disbursement ladders anywhere | `disbursal_risk` |

## 3.5 The fixture seam

One interface, `PipelineRunner`, with two implementations behind it: a live
runner that calls Vertex, and a fixture runner that replays a recorded run.
`NEEV_MODE` picks, and it's read in exactly one place — there's a test that fails
if a second reader appears.

The ten seeded loans are **real recorded runs**, not mockups. They were captured
through `scripts/record_golden_run.py` and validated against the same schemas a
live run has to emit, which is what stops a recording and a live run from
drifting apart. The raw ADK session state for each one is committed, saved
*before* parsing, so a capture can be re-parsed later at no cost.

## 3.6 The guardrails

| Concern | How it's handled |
|---|---|
| Tests must never bill | An autouse fixture blocks outbound sockets; 60 offline tests run with no credentials at all |
| A stray live mode | `NEEV_MODE=live` also needs `NEEV_ALLOW_BILLED_CALLS=1`, and an unrecognised mode falls back to fixture |
| A public URL spending money | Per-loan and per-service daily analysis caps, enforced server-side |
| API drift | A checked-in OpenAPI contract fails the suite if the API changes without being regenerated |
| A two-minute analysis looking stalled | Server-sent phase events with a 15-second heartbeat |
| Cross-borrower access | Authorization is injected per loan — one borrower reading another's contract gets 403, and only an officer can read the book |
| Uploads | 10 MB cap, PDF envelope validation, image decode-and-verify, decompression-bomb guard; evidence served only through an authorizing endpoint |

**337 automated tests** — 264 backend, 60 offline, 13 frontend — plus typecheck,
lint and a production build. Both container images were built and run as a pair
locally before either of them was deployed.

---

# 4. The stack

| Layer | What |
|---|---|
| Agents | Google ADK `SequentialAgent`, five agents sharing state via `output_key`; `gemini-3.7-flash` on Vertex AI |
| Grounding | Plain Python tools — BigQuery benchmark lookups and pure-arithmetic risk math |
| Backend | Python 3.11, FastAPI, SQLAlchemy, SQLite — 23 API paths |
| Frontend | Next.js 16 App Router, server components and actions, Tailwind v4 — 17 routes |
| Auth | Username and password. The provisioned accounts share one password from the environment; self-created accounts use `hashlib.scrypt`. Sign-up makes borrowers only — officer access to the whole book is never self-served |
| Google Cloud | Vertex AI, Cloud Run, Cloud Build, Artifact Registry, BigQuery, Secret Manager, IAM |

---

# 5. What isn't built, honestly

Saying it here rather than leaving it for a reviewer to find.

- **The benchmark rates are provisional.** They're CPWD DSR 2023-derived and
  Hyderabad-factored, but not independently verified line by line. The
  `verified` column says so, and so do the screens.
- **The database is ephemeral.** SQLite sits on the Cloud Run instance disk and
  gets re-seeded from the repository on every cold start, so anything a visitor
  creates lasts as long as the instance does. Moving to Cloud SQL is a
  connection-string change — the ORM means no query would have to move.
- **There's no identity verification.** Signing in is a username and a password,
  not a KYC'd identity. The seam for a real provider is one endpoint that every
  screen already reads its identity from.
- **Nothing is trained.** The LTV bands are a lookup prior taken from a public
  dataset that must never be fit, because it has fatal target leakage. We took
  the bands and left the dataset alone.
- **Hindi, Telugu and read-aloud aren't built.** The interface says "coming"
  rather than pretending they work.

---

*Neev — नींव — is the Hindi word for the foundation of a building. It's the first
thing that gets built, and the first thing worth checking.*
