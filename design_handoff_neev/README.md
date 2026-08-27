# Handoff: Neev — self-construction loan guardian (owner + bank portals)

## Overview
Neev protects self-construction home loans on both sides of the table. The **owner** uploads their contractor's Bill of Quantities (BoQ); Neev flags inflated rates, missing scope, vague specs and front-loaded payment schedules, then keeps verifying money against real site progress through every loan tranche. The **bank** gets a portfolio early-warning console, per-loan tranche decisions with photo evidence, and a contractor scorecard. Backend is an existing Google ADK 5-agent pipeline (repo: `neev/` — `boq_analyst → cost_estimation → visual_inspector → disbursal_risk → explainer`, BigQuery benchmarks). These designs are the UI for that pipeline.

## About the Design Files
The `.dc.html` files in this bundle are **design references created in HTML** — prototypes showing intended look, copy and behavior, not production code. Each file opens directly in a browser (ignore the `<x-dc>` wrapper and `support.js` reference; the meaningful content is the inline-styled markup plus a `Component` class whose `renderVals()` holds the screen's mock data). The task is to **recreate these screens in the target codebase's environment** (e.g. React/Next.js + Tailwind, or whatever the team picks) using real data from the ADK pipeline. `image-slot.js` is a prototype-only drag-drop image placeholder — replace with a real upload component.

## Fidelity
**High-fidelity.** Colors, type, spacing, copy and layout are final intent. Recreate pixel-perfectly; all values are inline in the files. (Color theme was still under discussion at handoff — treat the token table below as the current source of truth, and centralize tokens so retoning is cheap.)

## Information architecture — three entities
- **Owner (borrower)** — light warm-neutral theme. Nav: My contract · Sanction check · Build progress · Changes. Profile chip top-right (name, "Owner · plot"), accessibility cluster (language EN/हिंदी/తెలుగు, listen-aloud, theme toggle).
- **Bank (credit officer)** — same layout system but **dark ink top bar** (#111827) to signal console context. Nav: Portfolio · Contractors · Setup. Tranche Decision is a drill-in from Portfolio (breadcrumb).
- **Contractor** — no login in v1; interacts via written questions the owner sends. (Future: magic-link respond page.)

## Screens (file → purpose)
Owner journey, in order:
1. **Neev Landing.dc.html** — minimal hero (headline, one line, one CTA, family photo slot), 1-2-3 row, footer. Has a WORKING dark-mode toggle via CSS custom properties on `body` + `body.dark` — use this pattern app-wide.
2. **Neev Login.dc.html** — role toggle (home builder / lender); phone + OTP, "link your bank sent" fallback; no passwords.
3. **Neev 0 Owner Onboarding.dc.html** — BoQ upload dropzone (PDF/Excel/photos), 3-step stepper (Upload → Plot → Loan), 4-stage journey strip.
4. **Neev 0b Analyzing.dc.html** — post-upload processing: 5 pipeline phases with done/running/queued states (maps 1:1 to the ADK agents), animated progress bar, "Found so far" live findings feed.
5. **Neev 1 BoQ Review.dc.html** — THE core screen. 4 stat cards; flagged-items table grouped by BoQ section (flag pill + benchmark note per row, "Flagged/All" toggle); right rail: payment-schedule card (segmented bar, front-loaded warning), "Send before you sign" 4-question list with copy CTA, GST notice. Actions: Marked-up PDF, Upload revised BoQ, Send 4 questions.
6. **Neev 1a Upload Revision.dc.html** — revision dropzone + status of the 4 questions (replied/awaiting) + "why we re-check everything".
7. **Neev 1b Revised Contract.dc.html** — Rev 1/Rev 2 toggle, green "signable" verdict banner, flag-by-flag diff (struck-through old pill → what changed → ₹ delta), Rev1-vs-Rev2 totals card ("honest numbers cost less").
8. **Neev 2 Sanction Check.dc.html** — 3 comparison bars (quote / realistic cost / sanction), shortfall callout, "where the gap comes from" table (quoted vs market vs Δ), 3 ways-forward option cards.
9. **Neev 3 Build Progress.dc.html** — tranche timeline (paid / on-hold / upcoming), where-you-stand math card, monthly photo slots, next-steps checklist, "Report a milestone" link.
10. **Neev 3b Update Progress.dc.html** — milestone picker (footings selected), 3 photo slots with same-spot guidance, geotag/timestamp check chips, optional bills upload (cross-checked against BoQ quantities), voice-note hint, "what happens on submit" rail with release amount.
11. **Neev 6 Change Orders.dc.html** — change-order cards: signed-BoQ vs proposed side-by-side, "Neev's read" note with benchmark, Accept/Counter/Decline for pending; running-total rail vs sanction.

Bank console:
12. **Neev 7 Bank Onboarding.dc.html** — bring the book on: CSV upload (recommended) / LOS API / single loan; invite borrowers via WhatsApp links; threshold settings (hold exposure > 1.00, flag > 25% before slab, escalate below MEDIUM confidence — these mirror `buildguard/config.py`).
13. **Neev 4 Portfolio Hotlist.dc.html** — header w/ All·Needs action·On track filter + Export; 4 stat cards; loans table ranked worst-first (paid-up-to vs seen-on-site, disbursed, exposure ratio, cost-to-complete gap, HOLD/INSPECT/ON TRACK pills). Row 1001 links to Tranche Decision.
14. **Neev 3 Tranche Decision.dc.html** — release request header + HOLD banner (exposure 1.29); photo evidence grid + geotag/timestamp/same-angle chips; 5-stage checklist; "math in one line each" table (disbursed, verified value, exposure, cost-to-complete, gap); owner/officer rationale tabs; Release/Hold/Escalate decision card.
15. **Neev 5 Contractor Scorecard.dc.html** — per-contractor rows: flags/BoQ, under-specified share, overrun, sites gone quiet → WATCH/REVIEW/RELIABLE tiers; "why this compounds" note.

Reference: **Neev Logo Explorations.dc.html** — brand exploration turns; turn 5 (ids 5a/5b) is the decided identity.

## Interactions & Behavior
- Nav links are real `<a href>` between files — recreate as routes. Role determines which nav renders.
- Analyzing screen: phases advance sequentially; findings append as flags are detected; auto-advance to BoQ Review on completion (prototype links "see the finished report").
- BoQ Review: Flagged/All toggle filters the table; "Send 4 questions" composes a WhatsApp/share message from the question list.
- Change orders: Accept/Counter/Decline mutate status pill + running total.
- Tranche decision: Release/Hold/Escalate writes decision + full evidence trail to the loan file.
- Theme toggle (landing): toggles `dark` class on body; all colors are CSS vars. Hovers: buttons darken (#3d7a52 → #336847); table rows tint (#f7f6f4); outlined buttons darken border to ink.
- Accessibility cluster (owner pages): language switcher (EN/हिंदी/తెలుగు), text-to-speech "listen to this page", theme toggle — mocked in prototype, must be functional in build.

## State Management
Per loan: BoQ revisions[] (items, flags, totals), questions[] (sent/replied), sanction analysis, tranches[] (planned, disbursed, verified stage, evidence, decision), change orders[], exposure + cost-to-complete (from `disbursal_risk` agent). Bank: loans[] with computed hotlist ordering; thresholds config. All numbers on screen come from pipeline state — never hardcode.

## Design Tokens (current light theme — centralize these)
Colors: bg `#faf9f7` · card `#fff` · line `#ece9e4` · chip bg `#f2f0ec` · row-line `#f5f3f0` · hover `#f7f6f4` · ink `#2b2622` · sub `#6d665e` · faint `#9b938a` · action green `#3d7a52` (hover `#336847`) · green text `#2f6647` · green tint `#eaf4ee` · brick (logo only) `#e07856` · urgent brick text `#b4552e`, tint `#f9ece5` · sand flag text `#8a6d4f`, tint `#f4efe6`.
Dark theme (landing `body.dark`): bg `#241c15` · card `#2e251d` · ink `#f3e9dc` · sub `#b8a794` · line `#3f342a` · action `#4c9367`.
Bank chrome: bar `#111827`, inactive `#9ca3af`, active pill white-on-ink, officer avatar `#2d5bff`.
Type: **Baloo 2** (500–700) for h1/brand/CTAs — chosen for warmth + Devanagari support; **Instrument Sans** (400–700) body/UI; **JetBrains Mono** (400–600) for all numbers, ids, ratios. Sizes: h1 28px/700, section titles 14–14.5px/700, body 12.5–13.5px, labels 10.5–12px w/ letter-spacing .04–.08em, stat numbers 23px mono.
Radii: cards 14–16px, buttons/pills 20–24px (owner) or 10px (bank), chips 20px. Shadows: `0 1px 2px rgba(20,15,10,.05)` cards. Top bar 58px, sticky, blur + 1px line. Content max-width 920–1280px depending on screen.
Logo: brick rounded square + white house glyph (SVG path `M20 6 L34 18 L31 18 L31 30 L9 30 L9 18 L6 18 Z`) + "Neev" in Baloo 2. Money format: full Indian grouping `₹32,00,000`.

## Voice
Owner-side copy is plain, warm, second-person, never accusatory ("Worth asking", "Questions, not accusations", "we wrote them for you"). Bank-side copy is compact and factual. Keep the exact copy in the files.

## Assets
No binary assets. `image-slot.js` marks every place a real image/photo goes (hero family photo, site photos, bills). Fonts from Google Fonts. All fixture numbers derive from the repo's `fixtures/` (sample_boq, draw_schedule.csv, rate_benchmarks.csv) — the golden demo case is loan 1001 / Ravi Kumar / Kompally.

## Files
All `.dc.html` files listed above + `image-slot.js`, in this folder.
