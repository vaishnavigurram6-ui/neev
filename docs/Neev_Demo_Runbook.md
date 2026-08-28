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

**Say:** Ravi's contractor sent a 40-item BoQ totalling ₹32,00,000. Neev priced
the same scope at Kompally rates: ₹29,15,000. Nine items are flagged — three
rate outliers, two pieces of missing scope, four vague specs.

**Point at:** the RCC M25 rows, priced at ₹9,800/cum against a ₹8,033 benchmark.
Then the *missing* rows — external plaster and terrace waterproofing, ₹1,54,000
of scope that isn't in the contract at all and comes back later as "extras".

**The line that lands:** 45% of the money falls due before the slab is cast.
₹14,40,000 before there is meaningful structure to show for it.

**Then:** the rail's four questions. Neev doesn't accuse anyone — it writes the
questions Ravi can send his contractor in writing. Hit **Send 4 questions**.

### 2 · At sanction — will the loan actually finish the house?

`/owner/loans/1001/sanction`

**Say:** the bank approved ₹28,00,000. The realistic cost at local rates,
including the scope the contract left out, is ₹35,00,000. That's a ₹7,00,000
shortfall, visible before a rupee is drawn rather than at tranche four.

**Point at:** the gap table — where the ₹7,00,000 comes from, line by line. The
GST row reads "not stated", because the contract is silent on it.

**Then:** the three ways forward. Neev doesn't just diagnose.

### 3 · The bank's view — worst loans first

`/bank/portfolio`

**Say:** same product, other side of the table. Ten active construction loans,
ranked by exposure, worst first. Three need action.

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
| Verified value in place | ₹13,90,000 |
| Disbursement exposure | 1.29 |
| Cost to complete | ₹15,80,000 |
| Cost-to-complete gap | −₹5,80,000 |

**The point:** the site photos check out — geotag matches Plot 47, timestamp
10 Aug 11:42, same camera angle as last time. **The work is real; the money is
ahead of it.** Releasing the next draw funds a house that can't be finished with
what's left.

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

- **Real:** the five-agent ADK pipeline (`src/agents/`, runnable in `adk web`),
  the risk arithmetic and its thresholds, the benchmark-comparison logic, the
  whole web application, role enforcement, and the audit trail a decision writes.
- **Staged:** the pipeline is not driving these screens yet. The figures are
  authored fixtures shaped exactly like the pipeline's real output — the five
  ADK `output_key` shapes — and a contract test proves every fixture validates
  against the schemas a live run must emit. Switching to live data changes where
  the object comes from and nothing else.
- **Not built:** real OTP, translation, text-to-speech, marked-up PDF export,
  WhatsApp sending. Each renders as a disabled control that says why, rather
  than a dead button that lies.
- **Why fixtures:** the build ran under a deliberate no-billed-calls rule. The
  live path is written and type-checked but never executed;
  `scripts/record_golden_run.py` captures a real run into the same schema once
  credits are approved, and refuses to start until they are.

## Screens beyond the demo path

Built: `/`, `/login`, `/owner/onboarding`, `/owner/loans/1001/analyzing`.
Preview (real layout, marked with a "Preview" pill): `/owner/loans/1001/boq/revise`,
`/boq/rev/2`, `/progress`, `/progress/report`, `/changes`, `/bank/contractors`,
`/bank/setup`.
