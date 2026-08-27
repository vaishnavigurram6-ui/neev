# Neev — Implementation Plan

*From current state (4-agent pipeline in adk web, Gemini API-key auth, BigQuery loaded, shared config.py) to demo-ready. Each step lists input → output so nothing is ambiguous at build time. Estimated effort: ~2 working days.*

---

## 0. System I/O — the contract at the top

**System inputs (per case):**

| Input | Format | Example |
|---|---|---|
| Contractor's BoQ | PDF / image / Excel | ravi_boq.pdf, ~40 line items |
| Plot location + built-up area | text fields | "Kompally, Hyderabad", 1800 sqft |
| Sanctioned amount | number | ₹28,00,000 |
| Disbursement history | rows from draw schedule | tranches 1–2 paid, ₹18L cumulative |
| Site photos (current tranche) | 1–4 images | slab-stage photos |

**System outputs (per case):**

| Output | Consumer | Form |
|---|---|---|
| Marked-up BoQ: flags + negotiation questions | Owner | list of {line_item, flag_type, evidence, question_to_ask} |
| Feasibility verdict at sanction | Both | expected_cost vs sanctioned, gap in ₹ |
| Tranche recommendation | Lender | RELEASE / HOLD / ESCALATE + exposure_ratio |
| Cost-to-complete gap | Owner | ₹ figure + plain-language warning |
| Dual rationale | Both | owner paragraph + credit-officer paragraph with evidence trail |

---

## 1. Data layer (Day 1 morning, ~2.5 hrs)

### 1.1 DSR benchmark table → BigQuery `rate_benchmarks`
- **Input:** CPWD DSR 2023 Vol 1 PDF (Indian Railways mirror via infralens.in/sor/cpwd); manually extract ~30 items matching the sample BoQ
- **Schema:** `item_code STRING, description STRING, unit STRING, dsr_rate FLOAT, hyd_factor FLOAT, effective_rate FLOAT`
- **Output:** the benchmark lookup the analyst tool queries
- Existing `metro_city_prices` stays as the completed-value table (median ₹/sqft by location)

### 1.2 config.py additions
- **Input:** published references (linked in the Data Inventory doc)
- **Output:** documented constants:

```python
MATERIAL_REFS = {"tmt_fe500_per_kg": (42, 55), "cement_50kg_bag": (320, 400)}  # +18% GST if quoted exclusive
ENG_RATIOS = {"steel_kg_per_cum_rcc": (80, 120)}
LTV_RISK_BANDS = {60: 0.139, 75: 0.126, 85: 0.157, 95: 0.187, 999: 0.267}
MILESTONE_WEIGHTS = {"foundation": 0.15, "plinth": 0.10, "slab": 0.25, "brickwork_roof": 0.30, "finishing": 0.20}
```

### 1.3 Fixtures (hand-built)
- **sample_boq.pdf** — ~40 items, 4 seeded flaws: RCC @ ₹9,800/cum (benchmark ~₹8,000 adjusted), waterproofing absent, "TMT bars" with no grade, payment schedule 45% before slab
- **draw_schedule.csv → BigQuery `draw_schedule`** — ~50 rows across ~10 loans: `loan_id, tranche_no, milestone, planned_cum_pct, sanctioned, disbursed_cum, inspection_date, observed_stage`
- 5–10 site photos in `demo_assets/` (own phone / Wikimedia)

---

## 2. Agent layer (Day 1 afternoon → Day 2)

Pipeline: `SequentialAgent([boq_analyst, cost_estimation, visual_inspector, disbursal_risk, explainer])` — one NEW agent (boq_analyst, prepended), four existing agents MODIFIED to read its state.

### 2.1 boq_analyst_agent (NEW — build first)
- **Input:** BoQ file (Gemini multimodal), location, built-up area
- **Tools:** `lookup_benchmark_rate(item) → effective_rate` (BigQuery); config ratios
- **Logic:** parse to line items → per line: rate vs benchmark (>15% deviation = flag), spec completeness (grade / brand / IS standard), quantity vs engineering ratios; whole-document: missing-scope checklist (waterproofing, electrical, GST clause, exclusions column), payment-schedule weighting
- **output_key `boq_findings`:**

```json
{"line_items":[{"id":"4.2","desc":"TMT bars","qty":4.8,"unit":"MT","rate":62000}],
 "flags":[{"item":"4.2","type":"UNDERSPECIFIED",
           "evidence":"no grade named; Fe415 vs Fe500 differs in kg needed for same strength",
           "question":"Please confirm the TMT grade for item 4.2 in writing."}],
 "boq_total":3200000,"payment_pct_before_slab":45}
```

- **Rule:** every number in a flag comes from a tool call or the document itself — never model memory. Questions, not verdicts.

### 2.2 cost_estimation_agent (MODIFY)
- **Input:** `boq_findings` + location
- **Tools:** BigQuery median ₹/sqft (completed value); benchmark re-pricing of parsed items
- **output_key `cost_estimate`:** `{expected_total_cost, sanction_gap, completed_value_estimate, per_milestone_cost[]}` — Beat 2's ₹35L-vs-₹28L comes from here

### 2.3 visual_inspector_agent (MODIFY)
- **Input:** site photos + `boq_findings.line_items`
- **Logic:** Gemini vision zero-shot → stage ∈ {foundation, plinth, slab, brickwork_roof, finishing}, confidence ∈ {high, med, low}, evidence-quality notes (angle, lighting, site identifiability). Low confidence never fails silently — it routes to escalation downstream
- **output_key `inspection_result`:** `{stage:"slab", confidence:"high", pct_complete_est:0.45, evidence_notes:[...]}`

### 2.4 disbursal_risk_agent (MODIFY — flat scalar params, per the earlier KeyError lesson)
- **Input:** `cost_estimate`, `inspection_result`, draw-schedule row for this loan
- **Logic (pure arithmetic — no LLM inside the math):**
  - `verified_value = expected_total_cost × cumulative_milestone_weight(stage)`
  - `exposure = disbursed_cum / verified_value` → >1.0 HOLD; low confidence → ESCALATE regardless
  - `cost_to_complete_gap = (sanctioned − disbursed_cum) − (expected_total_cost × (1 − pct_complete))`
  - LTV band lookup for context only
- **output_key `risk_assessment`:** `{exposure_ratio:1.4, recommendation:"HOLD", cost_to_complete_gap:-420000, reasons:[...]}`

### 2.5 explainer_agent (MODIFY)
- **Input:** all four upstream keys
- **output_key `explanation`:** `{owner_view: "plain language — names the ₹4.2L gap and what to do about it", officer_view: "exposure 1.4, evidence list, DSR citations"}`
- **Rule:** may only reference numbers present in upstream state.

---

## 3. Wiring & test loop (Day 2)

- Run: `adk web --allow_origins 'regex:https://.*\.cloudshell\.dev'` from the parent directory
- **Golden test — the Ravi case:** BoQ in → 4 flags found; sanction check → ₹7L gap; slab photo + ₹18L disbursed → exposure 1.4, HOLD; explainer → both paragraphs cite the right numbers
- **Negative test:** clean BoQ + consistent photo → RELEASE (proves the system isn't flag-happy)
- **Confidence test:** blurry photo → ESCALATE (proves the safety valve works)
- Record the golden run end-to-end as the demo backup

## 4. Optional polish (only after §3 passes)

- Portfolio query: one BigQuery view over draw_schedule × risk outputs, sorted by cost-to-complete gap (Beat 4)
- Thin HTML/Streamlit layer over Beats 1 & 4 only

## Priority if time collapses

boq_analyst + fixtures (Beats 1–2 alone are a coherent demo) → disbursal math (Beat 3) → explainer → portfolio (cut first).

---

## Judge-proofing built into the design

- **No hallucinated rates:** rates enter only via tool calls (the grounding rule)
- **No fake precision:** stage classes + confidence flags, not percentages
- **No leakage:** Loan_Default used as lookup bands, never trained
- **Honest fixtures:** draw schedule labeled illustrative, in one sentence, during the demo
