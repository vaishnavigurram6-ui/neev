# Neev — Data Inventory for Implementation

*What we have, what we need, what doesn't exist (and why that's fine). One row per pipeline input.*

---

## Summary table

| # | Data need | Feeds | Status | Source |
|---|---|---|---|---|
| 1 | Property valuation (₹/sqft by location) | cost_estimation_agent | ✅ **Have** — loaded in BigQuery | metro_city_prices.csv — 32,963 listings, 6 metros, 1,776 locations (Kaggle) |
| 2 | Rate benchmarks (per-item construction rates) | boq_analyst_agent | ⬇️ **Get — the one real download** | CPWD DSR 2023 (links below) |
| 3 | LTV → default risk bands | disbursal_risk_agent | ✅ **Have** — as lookup prior only | Loan_Default.csv (Kaggle) — bands: LTV ≤60 → 13.9%, 60–75 → 12.6%, 75–85 → 15.7%, 85–95 → 18.7%, >95 → 26.7% |
| 4 | Material price constants (TMT, cement) | config.py | ✍️ **Hardcode** — no dataset exists | Published references (links below) |
| 5 | Engineering ratios (steel/RCC etc.) | boq_analyst_agent sanity checks | ✍️ **Hardcode** | Standard QS references; document in config |
| 6 | Sample BoQ with seeded flaws | Demo Beat 1 | 🔨 **Hand-build** | ~40 line items; flaws: inflated RCC rate, missing waterproofing, unspecified TMT grade, front-loaded payments |
| 7 | Tranche draw schedule | disbursal_risk_agent | 🔨 **Hand-build** — proprietary to banks, no public data anywhere | ~50 rows: loan_id, tranche_no, milestone, planned %, disbursed, inspection date |
| 8 | Site progress photos | visual_inspector_agent | 📷 **5–10 phone photos** — no labeled dataset exists | Own photos (Hyderabad outskirts) or Wikimedia Commons; Gemini classifies stage zero-shot, no training data needed |
| 9 | BoQ red-flag taxonomy | boq_analyst_agent prompt | ✍️ **Rules in prompt** | Published homeowner guidance (links below) |

Retired: home_loan_prediction.csv (approval labels, not defaults; 614 usable rows — reduce to income/EMI heuristic or drop). Loan_Default.csv must never be trained on (missing rate_of_interest = 100% default → fatal leakage); bands only.

---

## Links

### 2 — CPWD DSR (rate benchmarks) ★ priority download
- Official portal: https://www.cpwd.gov.in/Documents/cpwd_publication.aspx (note: cpwd.gov.in serves an invalid SSL cert; browsers may warn)
- Verified free mirrors (Indian Railways-hosted, cleaner SSL) via directory: https://infralens.in/sor/cpwd
  - CPWD DSR Civil Vol 1 (2023), ~50 MB
  - CPWD DSR Civil Vol 2 (2023), ~60 MB
  - CPWD AOR Vol II (2023) — rate build-up, optional
- Telangana / state SoRs directory (for Hyderabad-specific rates): https://infralens.in/sor
- Usage: extract only the ~30 items in the sample BoQ into a BigQuery table `(item, unit, dsr_rate, city_factor)`. Public-domain government document — free to use.

### 1 — Property valuation (already loaded; alternates if ever needed)
- Current: metro_city_prices (Kaggle, in BigQuery)
- Alternates (all redundant, listed for completeness):
  - https://www.kaggle.com/datasets/mohamedafsal007/house-price-dataset-of-india
  - https://www.kaggle.com/datasets/amitabhajoy/bengaluru-house-price-data
  - https://www.kaggle.com/datasets/goelyash/housing-price-dataset-of-delhiindia
- Trend context (optional): RBI Housing Price Index — https://www.data.gov.in/catalog/housing-price-index-india

### 4 — Material price references (constants, not datasets)
- Multi-city live reference (200 items, 50 cities): https://infralens.in/prices
- TMT ranges & GST framing: https://civilsite.in/steel-price-list/
- General 2026 price lists: https://civiconcepts.com/blog/construction-and-building-materials-market-price
- Values to hardcode with source comments: TMT ₹42–55/kg (Fe500, +18% GST if quoted exclusive), cement ₹320–400 per 50 kg bag

### 9 — BoQ red-flag taxonomy (rules for the analyst prompt)
- Line-by-line BoQ walkthrough (80–150 items, what contractors inflate/omit): https://gharkabudget.com/articles/how-to-read-contractor-boq/
- Red flags + 8 essential elements per line: https://www.studiomatrx.org/guides/boq-explained-india
- TMT grade/weight overcharging mechanics: https://fixtoofinish.com/
- Contract clauses (payment schedule, penalties): https://www.houseyog.com/blog/construction-contractor-agreement-india-template/

### Confirmed gaps — searched, does not exist publicly
- Tranche-level construction loan disbursement records → proprietary to banks. Hand-build; state as illustrative.
- Stage-labeled Indian residential construction photos → nearest datasets are PPE/safety detection and building-defect sets (wrong task). Not needed: Gemini does stage classification zero-shot.
- Per-item material price CSV for India → reference pages exist, datasets don't. Constants suffice.

---

## Grounding rule (why the gaps don't matter)

The model does perception and reasoning; tools supply facts. Gemini reads the BoQ and the photo; every rate, ratio and threshold enters through a BigQuery/config lookup — never from the model's memory. So the only data that must exist is the benchmark table (#2, one download) and the fixtures we author ourselves (#6, #7). The absence of public tranche data is the argument for the agentic design, stated as such in the submission.

## Build order
1. Download DSR Vol 1 → extract ~30 items → BigQuery table (≈1 hr)
2. Author sample BoQ with 4 seeded flaws (≈45 min)
3. Author draw schedule, ~50 rows (≈30 min)
4. Hardcode material constants + ratios in config.py with source comments (≈20 min)
5. Take/collect 5–10 site photos (evening errand)
