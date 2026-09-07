# agents/neev_pipeline/config.py
# Central configuration for the Neev (BuildGuard) pipeline.
# Every constant that any agent's math depends on lives here — never in a prompt.

import os

# ---------------------------------------------------------------- GCP / models
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "buildguard-ai-2026")
BQ_DATASET = "buildguard_data"
LOCATION = "asia-south1"
GEMINI_MODEL = "gemini-3.6-flash"

# BigQuery tables
TBL_LOAN_HISTORY = f"{PROJECT_ID}.{BQ_DATASET}.loan_history"
TBL_METRO_PRICES = f"{PROJECT_ID}.{BQ_DATASET}.metro_city_prices"
TBL_RATE_BENCHMARKS = f"{PROJECT_ID}.{BQ_DATASET}.rate_benchmarks"
TBL_DRAW_SCHEDULE = f"{PROJECT_ID}.{BQ_DATASET}.draw_schedule"

# ------------------------------------------------------------- BoQ analysis
# Rate deviation beyond which a line item is flagged (fraction of benchmark).
RATE_DEVIATION_THRESHOLD = 0.15

# Material price reference ranges, INR. Sources (accessed Aug 2026):
#   TMT Fe500: civilsite.in/steel-price-list (₹42-55/kg; +18% GST if quoted exclusive)
#   Cement 50kg bag: civiconcepts.com market price list (₹320-400)
# These are sanity ranges for flagging, not billing rates.
MATERIAL_REFS = {
    "tmt_fe500_per_kg": (42, 55),
    "cement_50kg_bag": (320, 400),
}
GST_RATE_MATERIALS = 0.18  # flag if BoQ is silent on GST treatment

# Engineering sanity ratios (standard QS practice for RCC-framed residential).
# steel_kg_per_cum_rcc: typical 80-120 kg steel per cum of RCC in low-rise homes.
ENG_RATIOS = {
    "steel_kg_per_cum_rcc": (80, 120),
}

# Scope a complete residential BoQ should contain. Absence = MISSING_SCOPE flag
# (these are the items that most often return later as paid "extras").
# Each scope maps to the phrases that count as evidence of its presence —
# real BoQs write "concealed wiring per point", not the word "electrical".
# Phrase lists widened 2026-09-07 after scripts/synthetic_boqs.py measured a 35%
# precision on MISSING_SCOPE across 40 varied BoQs. "External cement plaster
# 18mm in CM 1:4" -- an entirely ordinary Indian BoQ line -- matched neither
# "external plaster" nor "exterior plaster", so a priced item was reported as
# absent scope. Ravi's fixture never caught it because external plaster is a
# seeded omission there, so the present-but-differently-worded case was never
# exercised. Re-score after any edit here.
EXPECTED_SCOPE = {
    "waterproofing": ["waterproofing", "water proofing", "waterproof treatment"],
    "electrical": ["electrical", "wiring", "conduit"],
    "plumbing": ["plumbing", "cpvc", "water lines", "water supply", "drainage"],
    "anti-termite": ["anti-termite", "termite"],
    "external plaster": [
        "external plaster", "exterior plaster",
        "external cement plaster", "exterior cement plaster",
        "external plastering", "exterior plastering",
        "outside wall plaster", "outer wall plaster",
        "weathering coat plaster",
    ],
}

# How much of a scope there would be, as a multiple of built-up area, when the
# BoQ omits it entirely. Pricing absent work needs a quantity from somewhere,
# and a model inventing one is the "no fake precision" failure this project
# forbids -- so the assumption lives here, in the open, next to the rates.
#
# Standard QS practice for a low-rise residential build:
#   waterproofing     terrace footprint plus toilet sunks (~0.95 of built-up)
#   external plaster  external wall area runs slightly over built-up (~1.10)
#   anti-termite      plinth area, which for G+0 is the footprint (~1.00)
# Anything not listed cannot be quantified from area alone (electrical is per
# point, plumbing per bath set) and is reported unpriced rather than as zero.
MISSING_SCOPE_AREA_FACTORS = {
    "waterproofing": 0.95,
    "external plaster": 1.10,
    "anti-termite": 1.00,
}
SQFT_PER_SQM = 10.7639

# Payment schedule: flag if more than this fraction of contract value
# is demanded before the (ground-floor) slab is cast.
MAX_PAYMENT_PCT_BEFORE_SLAB = 0.30

# ---------------------------------------------------------- Disbursal risk
# Milestone completion weights (fraction of total construction value in place
# once the stage is COMPLETE). Cumulative sum reaches 1.0 at finishing.
MILESTONE_WEIGHTS = {
    "foundation": 0.15,
    "plinth": 0.10,
    "slab": 0.25,
    "brickwork_roof": 0.30,
    "finishing": 0.20,
}
MILESTONE_ORDER = ["foundation", "plinth", "slab", "brickwork_roof", "finishing"]

def cumulative_weight(stage: str) -> float:
    """Fraction of total value in place when `stage` is complete."""
    total = 0.0
    for s in MILESTONE_ORDER:
        total += MILESTONE_WEIGHTS[s]
        if s == stage:
            return round(total, 4)
    raise ValueError(f"Unknown stage '{stage}'. Must be one of {MILESTONE_ORDER}")

# Exposure ratio above which the tranche recommendation is HOLD.
EXPOSURE_HOLD_THRESHOLD = 1.0

# LTV -> historical default-rate bands. Derived as a LOOKUP PRIOR from
# Kaggle Loan_Default.csv (148,670 US mortgages, 2019). NOT a trained model —
# the dataset has fatal leakage (missing rate_of_interest == 100% default)
# and must never be fit. Bands verified by direct groupby:
#   LTV <=60: 13.9% | 60-75: 12.6% | 75-85: 15.7% | 85-95: 18.7% | >95: 26.7%
LTV_RISK_BANDS = {60: 0.139, 75: 0.126, 85: 0.157, 95: 0.187, 999: 0.267}

def ltv_default_prior(ltv_pct: float) -> float:
    for ceiling in sorted(LTV_RISK_BANDS):
        if ltv_pct <= ceiling:
            return LTV_RISK_BANDS[ceiling]
    return LTV_RISK_BANDS[999]
