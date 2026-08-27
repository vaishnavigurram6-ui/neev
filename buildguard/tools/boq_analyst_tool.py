# buildguard/tools/boq_analyst_tool.py
# Tools for the boq_analyst_agent. The agent (Gemini) READS the BoQ document
# and extracts line items; these tools supply every FACT (benchmark rates,
# ratios, thresholds). Grounding rule: no number in a flag may come from
# model memory — only from a tool result or the document itself.

from google.cloud import bigquery

from ..config import (
    TBL_RATE_BENCHMARKS,
    RATE_DEVIATION_THRESHOLD,
    ENG_RATIOS,
    EXPECTED_SCOPE,
    MAX_PAYMENT_PCT_BEFORE_SLAB,
)

_bq = None
def _client():
    global _bq
    if _bq is None:
        _bq = bigquery.Client()
    return _bq


def lookup_benchmark_rate(item_description: str) -> dict:
    """Looks up the CPWD-DSR-derived benchmark rate for a BoQ line item.

    Args:
        item_description: Free-text item description from the BoQ,
            e.g. "RCC M25 for slab" or "TMT reinforcement bars".
    Returns:
        dict with 'matched_item', 'unit', 'benchmark_rate' (INR, Hyderabad-
        adjusted), and 'source'. If no match: {'matched_item': None}.
    """
    query = f"""
        SELECT description, unit, effective_rate
        FROM `{TBL_RATE_BENCHMARKS}`
        WHERE LOWER(@desc) LIKE CONCAT('%', LOWER(keyword), '%')
        ORDER BY LENGTH(keyword) DESC
        LIMIT 1
    """
    job = _client().query(query, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("desc", "STRING", item_description)]
    ))
    rows = list(job.result())
    if not rows:
        return {"matched_item": None,
                "note": "No benchmark found — do not flag rate; note as UNBENCHMARKED."}
    r = rows[0]
    return {
        "matched_item": r.description,
        "unit": r.unit,
        "benchmark_rate": float(r.effective_rate),
        "source": "CPWD DSR 2023 x Hyderabad factor (rate_benchmarks table)",
    }


def check_rate_deviation(boq_rate: float, benchmark_rate: float) -> dict:
    """Compares a BoQ rate against its benchmark.

    Args:
        boq_rate: Rate quoted in the contractor's BoQ (INR per unit).
        benchmark_rate: Benchmark rate from lookup_benchmark_rate (INR per unit).
    Returns:
        dict with 'deviation_pct' and 'flag' (True if |deviation| exceeds threshold).
    """
    dev = (boq_rate - benchmark_rate) / benchmark_rate
    return {
        "deviation_pct": round(dev * 100, 1),
        "threshold_pct": RATE_DEVIATION_THRESHOLD * 100,
        "flag": abs(dev) > RATE_DEVIATION_THRESHOLD,
    }


def check_steel_rcc_ratio(steel_qty_kg: float, rcc_qty_cum: float) -> dict:
    """Sanity-checks steel tonnage against RCC volume (the padding trick lives here).

    Args:
        steel_qty_kg: Total TMT/reinforcement quantity in the BoQ, in kg.
        rcc_qty_cum: Total RCC volume in the BoQ, in cubic metres.
    Returns:
        dict with 'ratio_kg_per_cum', 'expected_range', 'flag'.
    """
    lo, hi = ENG_RATIOS["steel_kg_per_cum_rcc"]
    ratio = steel_qty_kg / rcc_qty_cum if rcc_qty_cum else 0.0
    return {
        "ratio_kg_per_cum": round(ratio, 1),
        "expected_range": [lo, hi],
        "flag": not (lo <= ratio <= hi),
    }


def check_missing_scope(item_descriptions: list[str]) -> dict:
    """Checks the whole BoQ for scope that commonly returns as paid extras.

    Args:
        item_descriptions: Every line-item description parsed from the BoQ.
    Returns:
        dict with 'missing' (list of expected-but-absent scope keywords).
    """
    joined = " ".join(item_descriptions).lower()
    missing = [scope for scope, evidence in EXPECTED_SCOPE.items()
               if not any(phrase in joined for phrase in evidence)]
    return {"missing": missing, "checked_against": list(EXPECTED_SCOPE)}


def check_payment_schedule(pct_before_slab: float) -> dict:
    """Flags front-loaded payment schedules.

    Args:
        pct_before_slab: Fraction (0-1) of contract value payable before
            the ground-floor slab is cast, per the BoQ/agreement.
    Returns:
        dict with 'flag' and the threshold used.
    """
    return {
        "pct_before_slab": round(pct_before_slab * 100, 1),
        "max_reasonable_pct": MAX_PAYMENT_PCT_BEFORE_SLAB * 100,
        "flag": pct_before_slab > MAX_PAYMENT_PCT_BEFORE_SLAB,
    }
