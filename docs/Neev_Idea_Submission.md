# Neev (नींव)
## The Home Builder's Side of the Table

**One liner:** Your contractor has priced four hundred houses. You're pricing one. Neev reads your Bill of Quantities, flags what's inflated, missing or vaguely worded, then keeps checking it against real site progress through every loan tranche until the house is finished.

*Neev — नींव — is the foundation of a building. It is also the first stage of construction the system verifies.*

---

## 1. The Problem

### 1.1 Who this is for

A large share of Indian housing finance is **self-construction**: the borrower already owns the plot — often inherited, often semi-urban or rural — and borrows to build on it. Affordable-housing finance companies do substantial business in this segment.

The person at the centre of it builds **one house in their lifetime**. Their contractor has built hundreds.

### 1.2 Where the asymmetry lives

It lives in the **Bill of Quantities** — the line-item breakdown of every activity in the build, with quantities and rates. A complete BoQ for a 2,000 sqft independent house runs to roughly 80–150 line items across 12–18 sections.

The BoQ is not paperwork. It is the contract. It determines:

- What "branded fittings" or "good quality tiles" actually means
- What is inside scope, and what will later be billed as an extra
- What the owner can point to when a dispute arises

Published guidance for Indian homeowners consistently identifies the same failure modes:

| Red flag | What it enables |
|---|---|
| No brand or model named | Material substitution with cheaper equivalents |
| No IS standard cited | Sub-grade material, no recourse |
| Vague item descriptions | Scope argued after work has started |
| Lump-sum lines with no breakdown | Unverifiable pricing |
| Missing remarks / exclusions column | Everything omitted becomes a paid extra |
| No GST treatment stated | An unbudgeted 12–18% at settlement |
| Implausibly low headline rate | The low-bid trap — margin recovered via change orders |

A well-documented specific case: steel overcharging in Indian residential construction usually happens not through the rate but through **weight and grade confusion** — Fe 415 against Fe 500 against Fe 500D. Higher grade means fewer kilograms needed for the same strength. An owner who does not know this cannot detect it.

### 1.3 Why existing help doesn't work

There is a great deal of *content* teaching homeowners to audit their own BoQ — red-flag checklists, line-by-line walkthrough articles, free Excel templates.

Every one of them assumes the owner will manually audit 80–150 technical line items, in a domain they will encounter exactly once, under time pressure from a contractor waiting on a signature.

**The knowledge exists. The person who needs it cannot apply it.** That is the gap Neev fills.

### 1.4 The downstream consequence

When the BoQ is weak, the failure surfaces months later:

- **For the owner** — funds exhausted before the structure is habitable. A half-built house is worth *less* than the bare plot was, because clearance now costs money. By the time it is obvious, there is no leverage left and no room to re-scope.
- **For the lender** — money disbursed against work that does not exist, or against a budget that was never going to complete. If the borrower walks, the lender holds an unfinished structure.

Both failures trace back to the same document, unread.

---

## 2. The Solution

Neev takes the owner's side across the full lifecycle. One document — the BoQ — ingested once, used at every stage.

![Neev across the build lifecycle](figures/fig1_lifecycle.png)
*Figure 1 — The four stages. Stages 0 and 1 protect the owner before money moves; stages 2 and 3 protect both parties during the build.*

### Stage 0 — Before signing

**Input:** the contractor's BoQ (PDF, Excel, or photographed pages), plot location, built-up area.

**Output — a marked-up BoQ with:**
- Rates sitting outside local benchmarks, flagged per line
- Scope commonly present in comparable BoQs but **absent here** — the items that reappear later as paid extras
- Under-specified lines: no grade, no brand, no IS standard
- Quantity sanity checks against engineering ratios (e.g. steel tonnage against RCC volume)
- Payment schedule weighting — how much is demanded before meaningful work exists
- Missing GST, escalation and penalty terms

**Framed as questions, not verdicts.** Every flag becomes a specific line the owner can put to their contractor in writing: *"Please confirm the TMT grade for item 4.2 in the BoQ."* Neev corrects an information gap; it does not adjudicate a contract or accuse anyone.

### Stage 1 — At sanction

Does the sanctioned amount cover this BoQ at current local rates? A shortfall flagged **before** drawdown, while the scope can still be adjusted.

### Stage 2 — Through the build

Site photographs checked against BoQ line items at each tranche. One calculation, two readings:

```
Lender view    — Disbursement Exposure Ratio
                 cumulative_disbursed / verified_value_in_place
                 > 1.0  →  paid out more than exists on site

Owner view     — Cost-to-Complete Gap
                 (sanctioned - disbursed) - (remaining_BoQ_items x current_rates)
                 < 0    →  the house will stall; re-scope now
```

### Stage 3 — On every variation

Each change order re-priced against the original BoQ, so mid-build scope changes are visible against what was agreed rather than argued from memory.

### 2.1 Scope discipline: triage, not replacement

Neev does **not** remove the physical site valuation. That certificate carries regulatory weight and no lender will drop it.

It **prioritises**. Where BoQ, photographic evidence and disbursement history agree, the case is fast-tracked. Where they diverge, it escalates for urgent physical inspection. The claim is *fewer visits doing more work* — never *zero visits*.

### 2.2 Known adversarial case

**"What stops a borrower photographing someone else's house?"**

Geotag and timestamp validation against registered plot coordinates; same-angle comparison across successive tranches, so the structure must evolve consistently; and cross-checks of claimed stage against elapsed time and amount disbursed. Any inconsistency routes to physical inspection rather than to automated refusal.

---

## 3. Why the BoQ Unifies Both Users

This is the design insight the whole system rests on.

In standard construction practice, **the BoQ becomes the schedule of values** — the document against which progress payments are measured. Work completed is assessed as quantities delivered against BoQ line items.

So this is not two products bolted together:

![One document, two users](figures/fig2_boq_hub.png)
*Figure 2 — The same parse serves the owner at signing and grounds the lender's tranche decisions for the rest of the build.*

The same parse serves the owner at signing and grounds the lender's tranche decisions for the rest of the build. Improving one improves the other.

---

## 4. Why an Agentic Architecture

**There is no dataset for these judgements**, and this is not an oversight in the data landscape. These decisions have never been made from a table. They are made from a PDF, a photograph, and knowledge of local rates.

If clean tabular training data existed, the right answer would be a gradient-boosted classifier and there would be no case for an LLM pipeline. The inputs here are unstructured and arrive at inference time — precisely the condition under which an agent pipeline is the correct tool rather than a fashionable one.

### 4.1 Pipeline (Google ADK `SequentialAgent`)

| Agent | Responsibility |
|---|---|
| `boq_analyst_agent` | Parses the BoQ into structured line items; flags rate outliers, missing scope, under-specification, quantity inconsistencies; drafts negotiation questions |
| `cost_estimation_agent` | Prices the parsed BoQ against location-level market rates; establishes expected total and completed value |
| `visual_inspector_agent` | Reads build stage and completion from site photographs; flags evidence-quality issues |
| `disbursal_risk_agent` | Computes disbursement exposure and cost-to-complete gap; issues tranche recommendation |
| `explainer_agent` | Produces two rationales from one analysis — plain language for the owner, audit-grade for the credit officer |

![Agent pipeline](figures/fig3_pipeline.png)
*Figure 3 — Five agents in sequence. `boq_analyst_agent` sits first, feeding structured line items into cost estimation.*

Each agent writes to shared state via `output_key`, so the final recommendation carries a full evidence trail rather than a bare score. In regulated lending, an unexplained recommendation cannot be actioned — traceability is a requirement, not a feature.

---

## 5. Data Positioning

Honest accounting of what is grounded and what is illustrative:

| Component | Source | Status |
|---|---|---|
| Location-level valuation | 32,963 real listings, six Indian metros, 1,776 named locations | **Real data.** Median rates per sq ft anchor completed value. |
| LTV-to-risk relationship | Historical mortgage default records | **Calibration prior, not a trained model.** Used as a lookup band. |
| Construction rates and engineering ratios | Published Indian residential construction references | **Documented assumptions**, held in central config, adjustable per region. |
| BoQ red-flag taxonomy | Published homeowner guidance and standard QS practice | **Rules, not learned.** Auditable and explainable by design. |
| Tranche draw schedule | Constructed scenario | **Illustrative.** Tranche-level lending records are proprietary to banks. |

The last row is the argument rather than the gap. Designing around the absence of that data — reasoning over evidence instead of fitting a curve to records that do not exist — is what makes the agentic approach appropriate here.

---

## 6. For Lending Institutions

The bank-facing product is not a second build. It is an **aggregation layer over the same per-loan pipeline** — every capability below is derived from outputs the agents already produce.

![What the bank gets](figures/fig4_bank.png)
*Figure 4 — Five capabilities, all derived from per-loan agent state. No additional agents required.*

### 6.1 Pre-sanction feasibility

Today a bank sanctions against a cost estimate supplied by the borrower or contractor. Nobody checks whether that estimate is **achievable**. Under-costed BoQs are common and sometimes deliberate — the estimate is trimmed to fit the borrower into an eligibility band, and the shortfall surfaces eighteen months later as a stalled build.

Neev already prices the BoQ against local rates, so it can answer at underwriting time:

> *"This BoQ under-prices by approximately 18% against current Hyderabad rates. The sanctioned amount will not reach a habitable structure."*

This is a **new underwriting input**, not the automation of an existing one. It is the strongest lender-side claim in the product.

### 6.2 End-use verification

Construction loans are disbursed in tranches precisely so the lender can evidence that funds entered the building rather than going elsewhere. That evidence is currently a paper certificate in a file.

Neev produces a dated, photographic, BoQ-linked record of what each tranche bought — a compliance artifact rather than an operational convenience.

### 6.3 Contractor scorecard

A bank sees the same local contractors across dozens of loans and currently retains nothing about them.

Neev accumulates, per contractor:

- Whose BoQs are systematically under-specified
- Whose projects overrun budget or schedule
- Whose sites go quiet between tranches

After a few hundred loans this is a private credit signal **on builders rather than borrowers** — something no Indian lender holds for small contractors, and an asset that compounds with use. This is the defensibility answer.

### 6.4 Portfolio early warning

Per-loan metrics roll up into a ranked view of every construction loan in the book, ordered by cost-to-complete gap and schedule slippage.

The bank sees a project heading for a stall at **tranche three**, not at NPA classification.

### 6.5 Real-time loan-to-value

Verified value-in-place is already computed at each tranche. Most lenders track LTV against sanctioned amount or final projected valuation. Neev reports it as the structure actually rises, giving a live collateral position rather than a modelled one.

### 6.6 Why a bank buys this

Self-construction lending is under-served for one structural reason: **monitoring cost per loan is high relative to ticket size**. A ₹15 lakh loan requires roughly the same five site visits as a ₹1.5 crore loan, so the smaller loan is not worth writing.

Reduce the monitoring cost and the arithmetic changes. The lender can profitably write smaller tickets in geographies it currently declines.

That reframes Neev from a cost-saving tool into a **market-expansion tool** — the version a bank actually buys, because saving money on existing loans is a line item, while writing loans you previously could not is a business case.

**A note on incentive alignment.** During construction the borrower typically services interest only, converting to full EMI on completion. A house that finishes on schedule begins earning full yield sooner. Neev preventing the owner's build from stalling is therefore *directly* the lender's revenue interest — the owner-side and bank-side benefits are not a trade-off requiring justification.

---

## 7. Impact

**For the land owner**
- An 80–150 line contract audited in minutes instead of not at all
- Concrete questions to raise *before* signing, when leverage still exists
- Early warning that the money will not reach a habitable roof, while re-scoping is still possible

**For the lender**
- Reduced site-visit load through triage, with the statutory inspection intact
- Earlier detection of over-disbursement, before exposure becomes unrecoverable
- An auditable rationale attached to every tranche decision

**Why the incentives align.** The lender pays; the owner benefits. These are not in tension. Fewer disputes, fewer stalled builds and fewer abandoned structures are exactly what protects the lender's book. Neev makes small-ticket self-construction lending cheap enough to service — which is precisely why that segment is under-served today.

---

## 8. Technology

- **Google ADK** — multi-agent orchestration via `SequentialAgent`
- **Gemini** — multimodal reasoning over BoQ documents and site imagery
- **BigQuery** — location-level valuation reference data and loan records
- **Google Cloud** — deployment, region `asia-south1`

---

## 9. What Exists Today, and What Doesn't

Construction *loan management* software is a mature category, with established platforms offering draw administration, inspection reports and portfolio risk scoring. Those products are sold to lenders, priced for institutional portfolios, and built around US construction lending.

What does not exist is anything pointed at **the individual self-builder** — the person with the most at stake, the least information, and no budget for a quantity surveyor.

Neev is that product. The lender-facing capability is how it gets paid for.
