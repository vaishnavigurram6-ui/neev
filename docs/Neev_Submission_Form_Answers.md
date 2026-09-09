# Patchamomma 2026 — Touchpoint 3 FINAL Form

**Form:** https://forms.gle/1Xt8X4kzqdDyQRNq7
**Read on 2026-09-10.** 21 required-or-optional questions across five sections.
Every answer below is drafted from this repository, so each one is checkable.

> **Do not submit until the deploy is done.** Q13 needs the live URL and Q14 the
> demo video. There is one submission and no edit link.

## Two warnings from the form itself

1. **Q2 must be the Patchamomma registration email** — the address the form link
   arrived at. A different address means the entry is not matched to the
   shortlisted profile and *is invalid*. This is the single highest-risk field on
   the form, and nothing in this repo can tell you which address it is.
2. Submissions are retained only until **24 September**, then purged.

---

## Section 1 — Identity

**Q1. Full Name** · short text · required
*Your full name as mentioned in Patchamomma Registration.*

> `Vaishnavi Gurram` — assumed from the repo's git identity
> (`vaishnavigurram6@gmail.com`). **Confirm this matches the registration.**

**Q2. Your Patchamomma Registered Email Id** · short text · required

> **YOU MUST FILL THIS.** Not derivable from the repo. Use the mailbox that
> received the form link. See warning 1.

**Q3. Your Team's Patchamomma Registered Email Ids** · paragraph · required
*Comma separated. If you are the only team member, enter SELF.*

> `SELF` if solo. Otherwise every member's **registered** address.

---

## Section 2 — Project Details

**Q4. Idea Title** · short text · required

```
Neev (नींव) — the home builder's side of the table
```

**Q5. Idea One Liner** · short text · required

```
Your contractor has priced four hundred houses. You're pricing one. Neev reads
your Bill of Quantities, flags what's inflated, missing or vaguely worded, then
keeps checking it against real site progress through every loan disbursement
until the house is finished.
```

**Q6. Idea description** · paragraph · required

```
A large share of Indian housing finance is self-construction: the borrower
already owns the plot, often inherited and often semi-urban, and borrows to
build on it. The person at the centre of that transaction builds one house in
their lifetime. Their contractor has built hundreds.

The asymmetry lives in the Bill of Quantities — the line-item contract that
fixes what "good quality tiles" means, what is inside scope, and what will later
be billed as an extra. A complete BoQ for a 2,000 sqft house runs to 80-150 line
items across 12-18 sections. Published guidance for Indian homeowners names the
same failure modes every time: no brand or IS standard cited, vague descriptions,
lump-sum lines, no GST treatment, an implausibly low headline rate recovered
later through change orders. Steel is the textbook case — overcharging happens
through grade confusion, Fe 415 against Fe 500 against Fe 500D, not through the
rate, and an owner who does not know that cannot detect it.

The knowledge to audit a BoQ exists in abundance. The person who needs it cannot
apply it, once, under time pressure, with a contractor waiting on a signature.

Neev is a five-agent Google ADK pipeline that reads the document instead. A BoQ
analyst prices every line against locality-adjusted benchmarks and flags rate
outliers, missing scope, underspecified items, front-loaded payment schedules
and GST silence. A cost estimator prices what is absent and computes the gap
against the sanctioned amount. A visual inspector reads site photographs and
decides which construction stage they actually show. A disbursal-risk agent
turns that into an exposure ratio and a RELEASE / HOLD / ESCALATE
recommendation. An explainer writes the same finding twice — once for the
borrower, once for the credit officer.

It is deliberately two-sided. The borrower sees their contract read line by
line before they sign it, and a plain-language note they can send their
contractor themselves. The lender sees the whole book ranked by exposure, and
for each disbursement the site photographs beside the milestone that was
claimed. Both are looking at one document and one set of numbers, which is the
point: the disputes this prevents are disputes about what was agreed.

Every number a screen shows comes from a tool call — BigQuery benchmark lookups
and pure-arithmetic risk math — never from model memory. An unbenchmarked line
is withheld rather than guessed at, and a photograph the inspector cannot
assess produces no measurement and no cost-to-complete figure at all. That
restraint is the feature: a system that invents a shortfall on a loan nobody
measured is worse than one that says nothing.
```

**Q7. Documentation Link** · paragraph · required
*Mandatory. Strictly a Google Docs link, access "anyone with the link". Must
carry three sections beyond the title: **1. Project description · 2. Project use
case · 3. Architecture diagram**.*

> **ACTION NEEDED — the largest remaining task.** You have a doc already:
> https://docs.google.com/document/d/1JYcsxk8gSDNYBVRSKt3crod9Y1vm0gMUkrvz9cVM1YE/edit
>
> Before pasting it, check it has all three required sections and that sharing is
> "anyone with the link → Viewer". Source material is in this repo:
> - **Project description** — `docs/Neev_Idea_Submission.md` §1-2
> - **Project use case** — §1.1-1.4 (self-construction borrower, the BoQ, the
>   downstream consequence for both sides)
> - **Architecture diagram** — `figures/fig3_pipeline.png` (the five-agent
>   pipeline) and `figures/fig1_lifecycle.png`. Paste the images in; a link to a
>   GitHub file is not a diagram in the doc.

---

## Section 3 — Technology Details

**Q8. Data Source** · multiple choice · required
Options: `Kaggle Dataset` · `BigQuery Public Dataset` · `Synthetic Generated
Data` · `Other`

> **Recommend `Other`**, with this text — the honest answer is all three, and
> single-selecting one misstates the build:
>
> ```
> Kaggle (metro_city_prices: 32,963 listings across 6 metros and 1,776
> localities; Loan_Default: 148,670 mortgages, used only as an LTV to
> default-rate lookup prior, never trained on) + CPWD DSR 2023-derived rate
> benchmarks + synthetic BoQs and disbursement schedules. All four tables
> loaded into our own BigQuery dataset.
> ```
>
> If you would rather select a listed option, pick **Kaggle Dataset** — two of
> the four BigQuery tables come from Kaggle — and put the rest in Q9/Q11.

**Q9. Google Cloud Services Used** · paragraph · required

```
- Vertex AI — Gemini 3.7 Flash, all five agents. The deployment authenticates
  as the Cloud Run service account rather than with an API key, because the
  Gemini API free tier allows 20 generateContent requests per day per model
  (about two analyses) while Vertex bills the project's billing account.
- Google Agent Development Kit (ADK) — SequentialAgent, five agents sharing
  state through output_key, with HttpRetryOptions on every model call.
- Cloud Run — two services, neev-api (backend) and neev-web (frontend),
  region asia-south1. Server-to-server only: the backend's address is never
  sent to the browser, so no CORS configuration exists.
- Cloud Build — builds both container images from source at deploy time.
- Artifact Registry — stores those images.
- BigQuery — four tables in dataset buildguard_data (rate_benchmarks,
  metro_city_prices, loan_history, draw_schedule) plus a portfolio_hotlist
  view. Every benchmark a flag cites comes from a tool call against these.
- Secret Manager — used on the optional API-key path; the key is never passed
  through --set-env-vars.
- IAM — the runtime service account holds aiplatform.user, bigquery.jobUser
  and bigquery.dataViewer, and nothing more.
```

**Q10. AI Details** · multiple choice · required
*It is mandatory to use Google models for the build.*
Options: `Gemini API` · `Gemini Agent Platform from Google Cloud` · `Gemma` ·
`Other`

> **Recommend `Gemini Agent Platform from Google Cloud`** — the build is Google
> ADK orchestrating five Gemini agents on Vertex AI, which is that option rather
> than a bare API call. Name the model in Q11.

**Q11. Tech Stack (other tech details)** · paragraph · required

```
Agents      Google ADK SequentialAgent, five agents (boq_analyst,
            cost_estimation, visual_inspector, disbursal_risk, explainer)
            sharing state via output_key. Model: gemini-3.7-flash, set by
            one environment variable. Grounding tools are plain Python:
            BigQuery benchmark lookups and pure-arithmetic risk math, so no
            figure on any screen comes from model memory.
Backend     Python 3.11, FastAPI, SQLAlchemy ORM, SQLite. 23 API paths.
            Authorization is dependency-injected per loan, so a borrower
            cannot read another borrower's contract and only a credit
            officer can read the book.
Frontend    Next.js 16 App Router, React server components, server actions,
            Tailwind v4. 17 routes. SSE streams live pipeline phase events
            while a run is in progress, with a heartbeat so a two-minute
            analysis never looks stalled.
Auth        Username and password. Three provisioned demo accounts share one
            password from the environment; self-created accounts are hashed
            with hashlib.scrypt. Sign-up creates borrowers only.
Testing     264 backend tests, 60 offline tests that need no credentials and
            no network, 13 frontend tests, plus typecheck, lint and build.
            An autouse fixture blocks outbound sockets, so no test can bill.
            A checked-in OpenAPI contract fails the suite if the API drifts.
Containers  Two Dockerfiles, both built and run locally as a pair before
            deploying: 508MB backend, 371MB frontend.
```

---

## Section 4 — Deployed App Details and Link

**Q12. Deployed App Details** · paragraph · required
*Steps to access and test?*

```
Sign in at <APP LINK>/login. Three accounts, one shared password: `password`.

  ravi     — a borrower whose contract is flagged (loan 1001, Kompally)
  prasad   — a borrower whose contract is clean (loan 1002)
  officer  — the credit officer, who sees all ten loans

The four things to try, in this order:

1. Sign in as `ravi` and open "My contract". This is a real recorded run of the
   five-agent pipeline over a 40-item BoQ: 30 flags, the inflated RCC rate, the
   absent waterproofing priced from benchmarks, the unspecified TMT grade, and
   the payment schedule that wants 45% before the slab. "Before you sign" gives
   a note the borrower can send their contractor themselves.

2. To watch the agents run live, go to "Upload a revision" and choose "Use our
   sample BoQ" — no file needed. Five agents run against Vertex AI and the
   phases stream as they complete. It takes about two minutes; it is a real
   billed run, so please do it once rather than repeatedly.

3. Sign in as `officer` and open the portfolio. Ten loans ranked by exposure,
   worst first. Click the top row, then the disbursement awaiting a decision.

4. On that decision screen: the borrower's site photographs beside the
   milestone claimed, the exposure arithmetic, and the recommendation
   (RELEASE / HOLD / ESCALATE) with the reasons that produced it. Loans 1004
   and 1009 reached ESCALATE on their own — the visual inspector disagreed with
   the stage that was claimed.

You can also create your own borrower account at /signup and upload a BoQ to
it; a new account starts with an empty contract and the upload ready.

Two honest notes. The rate benchmarks are CPWD-DSR-derived and still marked
provisional in the data, which the screens say rather than hide. And the
database is seeded from the repository on every cold start, so anything you
create lives as long as the instance.
```

**Q13. Deployed App Link** · paragraph · required
*Anyone must be able to access it or the submission cannot be validated.*

> **AFTER THE DEPLOY.** It will be, exactly:
> ```
> https://neev-web-516665930454.asia-south1.run.app
> ```
> Composed from service `neev-web`, project number `516665930454`, region
> `asia-south1`. The deploy script prints the real one; paste that, not this.
> Both services deploy `--allow-unauthenticated`, so no Google sign-in is
> needed — which satisfies "anyone should be able to access". Open it in a
> private window before pasting, to prove it.

**Q14. Demo Video Link of your App** · short text · required
*Mandatory · under 3 minutes · screen share is enough · accessible to anyone
with the link — YouTube unlisted, or Google Drive with open access.*

> **ACTION NEEDED.** The shot list is already written for exactly this:
> `docs/Neev_Demo_Video_Plan.md` — 9 beats, 180 seconds, silent screen
> recording, every figure checkable against the deployed data.
> Upload unlisted to YouTube, then **open the link in a private window** to
> confirm it plays without a sign-in.

**Q15. Github Repo Link** · short text · required

```
https://github.com/vaishnavigurram6-ui/neev
```

> Check it is **public** before submitting. It is the panel's source of truth
> for everything they cannot click.

**Q16. Medium Blog Link** · short text · **optional**
*Voluntary. Published, and on Medium. Does not affect ranking, but appears on
the leaderboard if shortlisted.*

> Skip unless you have spare time after the deploy and the video. If you write
> it, `docs/Neev_Idea_Submission.md` plus the `figures/` diagrams are most of a
> draft already.

---

## Section 5 — Uniqueness

**Q17. What is unique about your idea / implementation?** · paragraph · required

```
Three things, and the third is the one that took the work.

1. It is two-sided over one document. Products in this space serve either the
   lender's underwriting or the homeowner's budgeting. Neev reads one BoQ and
   writes two views of the same finding — the borrower's and the credit
   officer's — from the same upstream numbers. The disputes it prevents are
   disputes about what was agreed, so both parties have to be looking at the
   same reading of it.

2. It follows the document through the whole build, not just at sanction. The
   BoQ is checked before signing, the sanctioned amount is tested against local
   rates, every disbursement is verified against site photographs of the stage
   claimed, and every change order is priced against the line that was signed.
   Four checkpoints on one contract.

3. No number on any screen comes from model memory. Every figure traces to a
   tool call: BigQuery benchmark lookups and pure-arithmetic risk math. The
   consequences are deliberate and visible. A line item with no benchmark is
   withheld rather than guessed at. A photograph the visual inspector cannot
   assess produces no measurement, and therefore no cost-to-complete figure --
   we shipped a bug where a fully-drawn loan displayed a Rs 35,95,327 shortfall
   nobody had measured, and the fix was to make the absence of a measurement
   propagate instead of defaulting to zero. Provisional benchmarks say so on
   screen. A system that invents a shortfall is worse than one that says
   nothing, because a credit officer would act on it.
```

**Q18. What is the problem it solves?** · paragraph · required

```
In Indian self-construction housing finance, the borrower builds one house in
their lifetime and the contractor has built hundreds. That asymmetry is
concentrated in the Bill of Quantities, which is not paperwork but the contract:
it fixes what "good quality tiles" means, what is in scope, and what will later
be billed as an extra. A complete BoQ for a 2,000 sqft house is 80-150 line
items across 12-18 sections.

The failure modes are well documented and always the same: no brand or IS
standard named, vague item descriptions, lump-sum lines with no breakdown, no
GST treatment stated, and an implausibly low headline rate recovered later
through change orders. Steel is the classic case, where overcharging comes
through grade confusion (Fe 415 / Fe 500 / Fe 500D) rather than the rate.

There is no shortage of guidance teaching homeowners to audit their own BoQ.
Every bit of it assumes the owner will manually check 80-150 technical line
items, in a domain they will encounter exactly once, with a contractor waiting
on a signature. The knowledge exists; the person who needs it cannot apply it.
```

**Q19. How are you solving it?** · paragraph · required

```
Five Gemini agents, orchestrated with Google ADK, read the document instead --
and every number they produce is grounded in a tool call rather than in the
model.

  boq_analyst       prices every line against locality-adjusted CPWD-derived
                    benchmarks from BigQuery, and flags rate outliers, missing
                    scope, underspecified items, front-loaded payment
                    schedules and GST silence
  cost_estimation   prices the absent scope and computes the gap against the
                    sanctioned amount, so "will this finish the house?" has a
                    number
  visual_inspector  reads the borrower's site photographs and decides which
                    construction stage they actually show, with banded
                    confidence and a human-review fallback
  disbursal_risk    exposure ratio = disbursed / verified value in place, plus
                    cost-to-complete gap, producing RELEASE / HOLD / ESCALATE
  explainer         writes the finding twice, for the borrower and for the
                    credit officer, using only the numbers upstream produced

The borrower gets their contract read before they sign it, plus a plain note to
send their contractor. The lender gets the book ranked by exposure and, for each
disbursement, the photographs beside the milestone claimed.

Evidence gating is the part that matters. If the inspector cannot assess the
photographs, the run does not release money on a guess -- it escalates to a
human, and no shortfall is reported, because none was measured.
```

**Q20. If you're not solving it, what is the (negative) impact of the problem
in the area you are solving for?** · paragraph · required

```
The failure surfaces months after the document was signed, when nothing can be
done about it.

For the borrower: funds exhausted before the structure is habitable. A
half-built house is worth less than the bare plot was, because clearance now
costs money. By the time it is obvious there is no leverage left and no room to
re-scope -- the contractor holds the work, the money is spent, and the family
is living somewhere else and paying for it.

For the lender: money disbursed against work that does not exist, or against a
budget that was never going to complete. If the borrower walks, the lender is
holding an unfinished structure that is security for nothing.

Both failures trace to the same document, unread. And it is not a rare
document: self-construction is a substantial share of affordable-housing
lending, and every one of those loans has a BoQ nobody audited line by line.
```

**Q21. If you could get just ONE THING from Patchamomma 2026, what would you
want to have accomplished?** · multiple choice · required
- Hands-on Learning, possibly get certified or get in the leaderboard
- See my idea turn to implementation
- Network and find a team to discuss and learn
- Finish / win in TOP 10 and present at the Finale in Nasscom
- Explore and find job opportunities after the Finale.
- *(Other)*

> **Yours to pick — I have no basis for choosing.** Given a deployed app with
> 337 tests behind it, "Finish / win in TOP 10 and present at the Finale in
> Nasscom" is the one the submission supports.

---

## Checklist before you press submit

| # | Item | State |
|---|---|---|
| 1 | Q2 is the **Patchamomma registration email** | **only you can confirm** |
| 2 | Q7 Google Doc has all three required sections, shared "anyone with link" | **to do** |
| 3 | Q13 live URL, opened in a private window | after the deploy |
| 4 | Q14 demo video uploaded, under 3 min, opened in a private window | **to do** |
| 5 | Q15 GitHub repo is public | check |
| 6 | Q12's password matches what was actually deployed (`NEEV_DEMO_PASSWORD`) | check at deploy |
| 7 | Both Cloud Run services answer, signed out, from another network | after the deploy |

One submission. No edit link. Fill every field in a scratch document first, then
paste.
