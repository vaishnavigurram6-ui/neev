# agents/neev_pipeline/tools/boq_analyst_tool.py
# Tools for the boq_analyst_agent. The agent (Gemini) READS the BoQ document
# and extracts line items; these tools supply every FACT (benchmark rates,
# ratios, thresholds). Grounding rule: no number in a flag may come from
# model memory — only from a tool result or the document itself.

from google.cloud import bigquery
from .units import rate_in_unit

from ..config import (
    MISSING_SCOPE_AREA_FACTORS,
    SQFT_PER_SQM,
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


_UNBENCHMARKED = "No benchmark found — do not flag rate; note as UNBENCHMARKED."
_SOURCE = "Provisional Hyderabad benchmark table; CPWD DSR verification pending"


def lookup_benchmark_rates(item_descriptions: list[str]) -> dict:
    """Looks up CPWD-DSR-derived benchmark rates for EVERY line item at once.

    Call this ONCE per Bill of Quantities, with every priced item's description.
    One query, not one per item: each tool call is a separate model turn, so
    looking items up individually cost 81 turns, ~2 minutes of wall clock and
    85% of the run's price for an answer a single query already contains.

    Args:
        item_descriptions: Every priced item's free-text description, e.g.
            ["RCC M25 for slab", "TMT reinforcement bars", ...].
    Returns:
        dict keyed by the description you passed in. Each value has
        'matched_item', 'unit', 'benchmark_rate' (INR, Hyderabad-adjusted) and
        'source'; an item with no benchmark has {'matched_item': None, 'note': ...}.
        Every description you pass is present in the result -- a missing key
        would be an unchecked rate.
    """
    if not item_descriptions:
        return {}
    return _shape_benchmark_rows(item_descriptions, _query_benchmark_rows(item_descriptions))


def _query_benchmark_rows(item_descriptions: list[str]):
    """One BigQuery round trip for the whole BoQ.

    LEFT JOIN so an item with no benchmark still comes back (as NULLs) rather
    than vanishing, and QUALIFY keeps the longest matching keyword per item --
    the same "most specific match wins" rule the single-item query got from
    ORDER BY LENGTH(keyword) DESC LIMIT 1.
    """
    query = f"""
        WITH items AS (
            SELECT DISTINCT desc_text FROM UNNEST(@descs) AS desc_text
        )
        SELECT i.desc_text, b.description, b.unit, b.effective_rate
        FROM items i
        LEFT JOIN `{TBL_RATE_BENCHMARKS}` b
          ON LOWER(i.desc_text) LIKE CONCAT('%', LOWER(b.keyword), '%')
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY i.desc_text ORDER BY LENGTH(IFNULL(b.keyword, '')) DESC
        ) = 1
    """
    job = _client().query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("descs", "STRING", list(item_descriptions))
            ]
        ),
    )
    return list(job.result())


def _shape_benchmark_rows(item_descriptions: list[str], rows) -> dict:
    """Turn query rows into one entry per requested description. Pure."""
    matched = {}
    for row in rows:
        # A LEFT JOIN miss arrives as a row whose benchmark columns are NULL.
        if getattr(row, "description", None) is None:
            continue
        matched[row.desc_text] = {
            "matched_item": row.description,
            "unit": row.unit,
            "benchmark_rate": float(row.effective_rate),
            "source": _SOURCE,
        }

    return {
        desc: matched.get(desc, {"matched_item": None, "note": _UNBENCHMARKED})
        for desc in dict.fromkeys(item_descriptions)  # de-duplicated, order kept
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


def check_rate_deviations(quotes: list[dict]) -> dict:
    """Scores EVERY quoted rate against its benchmark in one call.

    Call this ONCE, after lookup_benchmark_rates, with one entry per item that
    came back with a benchmark_rate. Calling it per item costs a model turn each
    for arithmetic that is free.

    Args:
        quotes: [{"item": "3.1", "boq_rate": 9800, "benchmark_rate": 8036}, ...].
            Omit benchmark_rate for an item that had no benchmark.
    Returns:
        dict keyed by item id, each value as check_rate_deviation returns. An
        item with no benchmark gets flag=false and an UNBENCHMARKED note rather
        than a made-up deviation.
    """
    results = {}
    for quote in quotes:
        item = str(quote.get("item"))
        benchmark = quote.get("benchmark_rate")
        if not benchmark:
            results[item] = {"flag": False, "note": _UNBENCHMARKED}
            continue
        try:
            rate = rate_in_unit(float(benchmark), quote.get("benchmark_unit"), quote.get("unit"))
        except ValueError as exc:
            results[item] = {"flag": False, "assessable": False, "note": str(exc)}
            continue
        results[item] = {**check_rate_deviation(float(quote["boq_rate"]), rate),
                         "assessable": True, "benchmark_rate": rate, "unit": quote["unit"]}
    return results


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


def price_against_benchmarks(
    line_items: list[dict], missing_scopes: list[str], built_up_sqft: float
) -> dict:
    """What the quoted scope SHOULD cost, and what the absent scope would cost.

    Call this ONCE, after check_missing_scope, with the parsed line items and
    the scope names that came back missing.

    Two figures the screens need and no other tool produces:

      fair_price_for_quoted_scope -- every benchmarked line repriced at its
        benchmark, plus the quoted amount for lines with no benchmark. Dropping
        the unbenchmarked ones would understate the fair price and so overstate
        how much the owner is being overcharged.
      missing_scope_value -- what the omitted work would cost, from the same
        benchmark table, at a quantity derived from built-up area using the
        documented factors in config.MISSING_SCOPE_AREA_FACTORS.

    A scope with no benchmark rate, or no area factor, comes back with
    amount=None and a note saying why. Reporting zero would assert the missing
    work is free.

    Args:
        line_items: [{id, desc, qty, unit, rate, amount}, ...] as parsed.
        missing_scopes: names from check_missing_scope, e.g. ["waterproofing"].
        built_up_sqft: the loan's built-up area, for quantifying absent scope.
    Returns:
        dict with 'fair_price_for_quoted_scope', 'missing_scope' (one entry per
        name, each {scope, qty, unit, rate, amount, note}) and
        'missing_scope_value'.
    """
    descriptions = [str(i.get("desc", "")) for i in line_items]
    descriptions += [str(s).strip().lower() for s in missing_scopes]
    # One query for the line items and the absent scopes together.
    return _price(
        line_items, missing_scopes, built_up_sqft, lookup_benchmark_rates(descriptions)
    )


def _price(
    line_items: list[dict],
    missing_scopes: list[str],
    built_up_sqft: float,
    benchmarks: dict,
) -> dict:
    """The arithmetic, with the benchmark lookups already done. Pure."""
    fair = 0.0
    unpriced = []
    for item in line_items:
        entry = benchmarks.get(str(item.get("desc", ""))) or {}
        rate = entry.get("benchmark_rate")
        if rate:
            try:
                rate = rate_in_unit(float(rate), entry.get("unit"), item.get("unit"))
            except ValueError:
                rate = None
        qty = float(item.get("qty") or 0)
        if rate and qty:
            fair += qty * float(rate)
        else:
            unpriced.append(str(item.get("id", item.get("desc", ""))))
            # No benchmark: the quoted amount is the only figure there is.
            fair += float(item.get("amount") or 0)

    built_up_sqm = float(built_up_sqft or 0) / SQFT_PER_SQM
    priced: list[dict] = []
    total = 0.0
    for scope in missing_scopes:
        key = str(scope).strip().lower()
        factor = MISSING_SCOPE_AREA_FACTORS.get(key)
        entry = benchmarks.get(key) or {}
        rate = entry.get("benchmark_rate")

        if factor is None:
            priced.append({"scope": scope, "qty": None, "unit": None, "rate": rate,
                           "amount": None,
                           "note": "Cannot be quantified from area alone."})
            continue

        qty = round(built_up_sqm * factor, 1)
        if not rate:
            priced.append({"scope": scope, "qty": qty, "unit": "sqm", "rate": None,
                           "amount": None,
                           "note": "No benchmark rate for this scope; quantity only."})
            continue

        try:
            rate = rate_in_unit(float(rate), entry.get("unit"), "sqm")
        except ValueError:
            priced.append({"scope": scope, "qty": qty, "unit": "sqm", "rate": None,
                           "amount": None, "note": "Benchmark unit is incompatible with area."})
            continue
        amount = round(qty * float(rate))
        total += amount
        priced.append({"scope": scope, "qty": qty, "unit": "sqm",
                       "rate": float(rate), "amount": amount,
                       "note": f"{factor:g} x built-up area at the benchmark rate."})

    return {
        "fair_price_for_quoted_scope": round(fair, 2),
        "missing_scope": priced,
        "missing_scope_value": round(total, 2),
        "unpriced_items": unpriced,
        "missing_scope_complete": all(p["amount"] is not None for p in priced),
    }
