# Neev — three-minute silent screen recording

*A shot list, not a script. There is no audio, so every claim has to be legible
on screen or captioned in the edit. Written 2026-09-10 against the data in this
repo; every figure below is one you can check before you record.*

## The one rule that shapes everything

**No narration means the screen carries the argument alone.** Two consequences:

1. **Hold long enough to read.** A viewer needs roughly 300ms per word. A stat
   card is 2 seconds; a paragraph is 6–8. Anything held for under 2 seconds is
   decoration, not evidence — cut it or hold it.
2. **Never show a screen whose point needs explaining.** If a beat only works
   with a voice-over, it does not belong in this video. Where the product's own
   copy already says it — and mostly it does — let the copy do the work and keep
   the cursor still.

Budget: **180 seconds, 9 beats.** Two beats carry the whole thing (the flagged
contract, and the photograph that disagrees with the claim); the other seven
exist to set those up and to prove they are real.

## Before you press record

| | Why |
|---|---|
| `NEEV_MODE=live bash scripts/dev.sh` | Live mode leaves no "Demo replay" line on the contract page. That line is honest in fixture mode and a distraction in a marketing video — so earn its absence rather than crop it out. |
| Reset first: `pkill -f uvicorn; cd src/backend && rm -rf artifacts && .venv/bin/python -m app.db.seed --reset` | Identical figures across takes. Without it, take three shows numbers take one did not. |
| One live analysis **before** recording, then reset? No — see below | The upload beat has to be live in-take, or the contract page reverts to a replay. Budget ~2 minutes of real waiting and speed-ramp it in the edit. |
| Browser: 1440px wide, no bookmarks bar, no extensions, one tab | The runbook verifies 1280/1440/1920. 1440 fills a 1080p frame with readable type. |
| Pick one theme and stay in it | The toggle is a nice detail and a terrible mid-video surprise. |
| Two windows, signed in separately: `ravi` and `officer` | Switching accounts on camera costs 15 seconds and shows a login form twice. Cut between windows instead. |
| Password for both: `neev-demo` | See the runbook. |

**Cost of a take:** about ₹3.81 for the BoQ analysis plus ₹1.50 for the
milestone inspection. Five takes is under ₹30. Do not rehearse in live mode —
rehearse in fixture (`bash scripts/dev.sh`), which is free and eight seconds.

## The shot list

### 1 · The promise — 0:00–0:12
`http://localhost:3000/`

Land on the hero. Hold still for 4 seconds — the headline and the photograph
are the whole beat. Then one slow scroll to the three steps, hold 4, and stop.

> On screen already: *"The home you dream of. Built the way you were promised."*

Do not scroll further. The page ends there on purpose.

### 2 · How little it asks — 0:12–0:26
Click **Check my contract — free** → sign in as `ravi` → onboarding.

Click **Use our sample BoQ**. Hold 2 seconds on *"Sample BoQ ready — a real
40-line builder's quote."* Enter the built-up area, click through step 3, and
press **Start the check**.

The point of this beat is that a homeowner needs one file and two minutes. Keep
it brisk — no lingering on form fields.

### 3 · Five agents, working — 0:26–0:42
The Analyzing screen.

**This is the credibility beat.** Five phases tick over: reading the document,
checking every rate against Kompally benchmarks, looking for missing scope,
checking specifications, reviewing the payment schedule. Findings appear beside
them as they are found.

In live mode this genuinely takes about two minutes. **Speed-ramp it to 16
seconds in the edit** — 8× on the quiet stretches, real time on each phase
flipping to done. Do not fake it with a cut; the ticking is the proof.

### 4 · The indictment — 0:42–1:20
`/owner/loans/1001/boq`

The longest beat, and the one that sells the product. Hold on the four stat
cards for 5 seconds:

| | |
|---|---|
| QUOTED vs FAIR PRICE | **₹28,47,930** — *Kompally rates price this scope at ₹26,77,618* |
| FLAGS RAISED | **14 items** — 3 rate outliers · 3 missing scope · 6 vague specs |
| MISSING SCOPE | **₹1,42,654** |
| DUE BEFORE SLAB | **45%** — *₹12,81,569 before meaningful structure exists* |

Then scroll the flagged table slowly, pausing about 3 seconds per group:

- **RATES ABOVE BENCHMARK** — three RCC items at ₹9,800/cum against a ₹8,036
  benchmark. The `Rate +22%` pills are the money shot.
- **EXPECTED BUT ABSENT** — waterproofing and external plaster, priced from
  benchmarks rather than guessed.
- **PAYMENT TERMS** — front-loaded, and GST unstated.

Finish by clicking **All 40** and holding 3 seconds: forty lines, three marked
red. That contrast — a whole contract, three real problems — is worth more than
any caption.

### 5 · What to actually do about it — 1:20–1:34
Same page, scroll to **Send before you sign**.

Eight questions, numbered, in the borrower's voice — *"Could you review the rate
for plinth beam RCC M20, as it is higher than the standard benchmark rate for
Hyderabad?"* Hold 6 seconds on the list, then click **Copy as WhatsApp
message** and hold 3 on the confirmation.

This is the beat that makes it a product rather than a report.

### 6 · Will the loan even finish the house — 1:34–1:48
`/owner/loans/1001/sanction`

Hold on the shortfall figure and the "cost to complete" bars. Six seconds. This
is the question no borrower knows to ask and every lender needs answered.

### 7 · The photograph that disagrees — 1:48–2:10
`/owner/loans/1001/progress/report`

Pick **Brickwork & roof**. Add the two slab photographs from
`fixtures/site_photos/`. Press **Send for verification**.

Two phases: *reading your site photos*, then *re-checking this payment against
the work in place*. About 35 seconds live — ramp to 10 in the edit.

**Then hold on the result.** Gemini looked at the photographs, said *slab*, and
set `matches_claim` false — the borrower asked for the brickwork draw and the
photographs show a slab. Nothing seeded that; the model reached it.

> Caption to add here, because the screen states the fact but not its weight:
> **"The photos show a slab. The borrower asked to be paid for brickwork."**

### 8 · The lender's side — 2:10–2:45
Cut to the `officer` window.

`/bank/portfolio` — the book, ranked worst-first. Hold 5 seconds; ten loans,
each with exposure and an action. The top three are P. Anjali at 1.71 and
M. Farhan at 1.13, both ESCALATE because their photographs showed a slab where
brickwork was claimed, then Ravi at 1.11 on HOLD. Then click **Ravi Kumar** —
third row, not the first — because his is the contract the rest of the video
has been about.

`/bank/loans/1001` — the loan file. Sanctioned, disbursed, exposure, stage on
site, the contract check, the draw schedule. Hold 5.

`/bank/loans/1001/tranches/4` — the decision. This is where the product pays
off: the evidence grid with the borrower's own photographs, the five-stage
strip, the math in one line each, and **RECOMMEND HOLD · exposure 1.11**. Hold
8 seconds, then scroll to *Why this recommendation* and hold 6 on the credit
note's opening sentence.

Finish on the three buttons — Release, Hold, Escalate — without clicking. The
officer decides; the product does not.

### 9 · Close — 2:45–3:00
Back to `/` and hold on the headline for 5 seconds. Cut to black.

## What to leave out, and why

- **The login form.** Dead time with no audio. Sign in before recording; cut
  between two windows.
- **Change orders.** A good screen and a fourth story. Three minutes cannot
  hold four.
- **The BoQ revision history and contractor scorecard.** Same reason.
- **Anything disabled.** A control that says why it does nothing is honest in
  the product and reads as unfinished on video.
- **The theme toggle, the accessibility cluster.** Craft a judge will notice in
  the product and will not notice in a three-minute skim.

## Captions worth adding in the edit

The UI says all of this except where noted. Keep them short, bottom-left, one
line, and never over a figure.

| At | Caption |
|---|---|
| 0:26 | Five agents. One contract. |
| 0:42 | Every rate checked against CPWD DSR and 32,963 local listings. |
| 2:10 | The photos show a slab. The borrower asked to be paid for brickwork. |
| 2:45 | Neev · नींव — the foundation. |

## The honest caveat, if anyone asks

The eight loans beyond Ravi and Prasad were analysed from **synthetic bills of
quantities** generated in this repo, each matched to its loan so the contract
total sits within 0.95–1.35× of the sanction. The pipeline that read them is the
same one that reads a real upload, and the runs are recorded rather than
replayed from an authored guess. `docs/Neev_Demo_Runbook.md` says which is which.
