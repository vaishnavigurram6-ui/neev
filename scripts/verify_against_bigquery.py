#!/usr/bin/env python3
"""Exercise the whole grounding path against REAL BigQuery, with NO model calls.

The expensive half of a pipeline run is Gemini. The grounded half -- every rate,
ratio, threshold and recommendation -- is BigQuery plus pure arithmetic, and
these tables are kilobytes, comfortably inside the free tier. So the data path
can be verified end to end for approximately nothing, and this script is that
verification:

    real rate_benchmarks   -> lookup_benchmark_rate  -> check_rate_deviation
    real loan_history      -> estimate_construction_cost
    real metro_city_prices ->        "
    real draw_schedule     -> assess_tranche
    all of the above       -> pipeline_parse -> PipelineOutput  (schema check)

What it CANNOT check is the part only a model can do: reading the PDF into line
items, and classifying a site photo. Those are the two things a capture buys.

Gemini is not merely avoided here, it is made unreachable: google.genai is
replaced in sys.modules with a stub that raises on any attribute access, before
any pipeline module is imported. A model call in this script raises rather than
bills. BigQuery is left completely alone, so it talks to your real dataset.

    export GOOGLE_CLOUD_PROJECT=buildguard-ai-2026
    python3 scripts/verify_against_bigquery.py               # loan 1001
    python3 scripts/verify_against_bigquery.py --variant clean --loan 1002

No GOOGLE_API_KEY is needed, because nothing that would use it can run.
BigQuery needs Application Default Credentials, which Cloud Shell already has.
"""

import argparse
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "agents"))
sys.path.insert(0, str(REPO_ROOT / "src" / "backend"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _make_gemini_unreachable() -> None:
    """Replace google.genai with a stub that raises. Must run before imports.

    Mirrors tests/test_offline.py, inverted: that stubs both Google clients, this
    stubs only the billed-per-token one and lets BigQuery reach real data.
    """

    class _Refuses:
        def __init__(self, *_a, **_k) -> None:
            pass

        def __getattr__(self, name: str):
            raise RuntimeError(
                f"Gemini was called ({name}). This script verifies the BigQuery "
                "path only and must never bill a model."
            )

    google = sys.modules.setdefault("google", types.ModuleType("google"))
    genai = types.ModuleType("google.genai")
    genai.Client = _Refuses
    sys.modules["google.genai"] = genai
    google.genai = genai


_make_gemini_unreachable()

import boq_data  # noqa: E402
from neev_pipeline.config import ENG_RATIOS, MAX_PAYMENT_PCT_BEFORE_SLAB  # noqa: E402
from neev_pipeline.tools.boq_analyst_tool import (  # noqa: E402
    check_missing_scope,
    check_payment_schedule,
    check_rate_deviation,
    check_steel_rcc_ratio,
    lookup_benchmark_rate,
)
from neev_pipeline.tools.cost_estimation_tool import estimate_construction_cost  # noqa: E402
from neev_pipeline.tools.disbursal_risk_tool import assess_tranche  # noqa: E402

OK = "  ok  "
BAD = " FAIL "


def _rule(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m\n" + "-" * 72)


def check_benchmarks(items: list[tuple]) -> tuple[list[dict], int]:
    """Look every priced line item up against the real benchmark table."""
    _rule("1 · rate_benchmarks — every line item, against real BigQuery")

    flags, matched = [], 0
    for _section, item_id, desc, qty, unit, rate in items:
        result = lookup_benchmark_rate(desc)
        if not result.get("matched_item"):
            print(f"  ---   {item_id:<5} no benchmark  · {desc[:46]}")
            continue

        matched += 1
        benchmark = result["benchmark_rate"]
        deviation = check_rate_deviation(float(rate), float(benchmark))
        marker = "FLAG" if deviation.get("flag") else " ok "
        print(
            f"  {marker}  {item_id:<5} quoted {rate:>7,.0f} vs "
            f"{benchmark:>7,.0f}  {deviation.get('deviation_pct', 0):>+6.1f}%  "
            f"· {desc[:34]}"
        )
        if deviation.get("flag"):
            flags.append(
                {
                    "item": item_id,
                    "type": "RATE_OUTLIER",
                    "evidence": (
                        f"Quoted INR {rate:,.0f} against a benchmark of "
                        f"INR {benchmark:,.0f} ({result['matched_item']})."
                    ),
                    "question": (
                        f"Could you share the rate basis for item {item_id}?"
                    ),
                    "deviation_pct": round(deviation["deviation_pct"], 1),
                    "benchmark_rate": benchmark,
                }
            )

    print(f"\n  {matched}/{len(items)} items matched a benchmark; {len(flags)} flagged")
    if matched == 0:
        print(
            f"{BAD} nothing matched. The `keyword` column does not overlap this "
            "BoQ's phrasing,\n       so a paid run would flag nothing. Fix the "
            "table before capturing."
        )
    return flags, matched


def check_ratios_and_scope(
    items: list[tuple], payment: list[tuple]
) -> tuple[list[dict], float]:
    _rule("2 · engineering ratios, missing scope, payment terms — pure arithmetic")

    flags = []

    steel_kg = sum(
        q
        for _s, _i, d, q, u, _r in items
        if u == "kg" and any(w in d.lower() for w in ("steel", "tmt"))
    )
    rcc_cum = sum(q for _s, _i, d, q, u, _r in items if u == "cum" and "rcc" in d.lower())
    if steel_kg and rcc_cum:
        ratio = check_steel_rcc_ratio(steel_kg, rcc_cum)
        low, high = ENG_RATIOS["steel_kg_per_cum_rcc"]
        print(
            f"  steel/RCC: {steel_kg:,.0f} kg over {rcc_cum:,.1f} cum = "
            f"{steel_kg / rcc_cum:,.1f} kg/cum (expected {low}-{high})  "
            f"-> flag={ratio.get('flag')}"
        )
        if ratio.get("flag"):
            flags.append(
                {
                    "item": "steel",
                    "type": "STEEL_RATIO",
                    "evidence": str(ratio),
                    "question": "Could you confirm the steel quantity for this RCC volume?",
                }
            )
    else:
        print(f"  steel/RCC: not derivable from line items (steel={steel_kg}, rcc={rcc_cum})")

    scope = check_missing_scope([d for _s, _i, d, _q, _u, _r in items])
    missing = scope.get("missing", scope.get("missing_scope", []))
    print(f"  missing scope: {missing or 'none'}")
    for name in missing:
        flags.append(
            {
                "item": name,
                "type": "MISSING_SCOPE",
                "evidence": f"No line item covers {name}.",
                "question": f"Is {name} included, and if so under which item?",
            }
        )

    before_slab = _pct_before_slab(payment)
    terms = check_payment_schedule(before_slab)
    print(
        f"  payment before slab: {before_slab:.0%} "
        f"(threshold {MAX_PAYMENT_PCT_BEFORE_SLAB:.0%})  -> flag={terms.get('flag')}"
    )
    if terms.get("flag"):
        flags.append(
            {
                "item": "payment schedule",
                "type": "FRONT_LOADED",
                "evidence": str(terms),
                "question": "Could the schedule be tied to completed milestones instead?",
            }
        )
    return flags, before_slab


def _pct_before_slab(payment: list[tuple]) -> float:
    """Fraction of contract value due BEFORE the slab is cast.

    Stops at the slab stage without counting it -- the threshold asks how much
    money the owner has parted with while the structure is still unproven, and
    the slab payment is due once it is cast. Counting it gives 65% for Ravi's
    schedule where the true figure is 45%, which the authored fixture agrees
    with (payment_pct_before_slab: 0.45).
    """
    total = 0.0
    for label, pct in payment:
        if "slab" in label.lower():
            break
        total += float(str(pct).rstrip("%")) / 100
    return round(total, 4)


def check_cost(built_up: int, locality: str, region: str) -> dict:
    _rule("3 · loan_history + metro_city_prices — real BigQuery")
    estimate = estimate_construction_cost(
        plot_area_sqft=float(built_up), region=region, location=locality
    )
    for key, value in estimate.items():
        shown = f"{value:,.0f}" if isinstance(value, (int, float)) else value
        print(f"  {key:<28} {shown}")
    return estimate


def check_risk(estimate: dict, facts: dict, stage: str) -> dict:
    _rule("4 · assess_tranche — real draw_schedule figures, pure arithmetic")
    risk = assess_tranche(
        expected_total_cost=float(estimate["estimated_cost"]),
        observed_stage=stage,
        # 'high' is an assumption, not a measurement: only a vision call can
        # establish it. Stated here so the printed recommendation is not
        # mistaken for a verified one.
        stage_confidence="high",
        sanctioned_amount=float(facts["sanctioned"]),
        disbursed_cumulative=float(facts["disbursed"]),
        completed_value_estimate=float(estimate["completed_value_estimate"]),
    )
    for key, value in risk.items():
        shown = f"{value:,.2f}" if isinstance(value, float) else value
        print(f"  {key:<28} {shown}")
    return risk


def check_schema(
    flags: list[dict],
    estimate: dict,
    risk: dict,
    items: list[tuple],
    pct_before_slab: float,
) -> bool:
    """Assemble real tool output into the shape every screen reads."""
    _rule("5 · pipeline_parse -> PipelineOutput — the shape the UI consumes")

    from app.services.pipeline_parse import parse_state

    state = {
        "boq_findings": {
            "line_items": [
                {"id": i, "desc": d, "qty": q, "unit": u, "rate": r, "amount": q * r}
                for _s, i, d, q, u, r in items
            ],
            "flags": flags,
            "boq_total": sum(q * r for _s, _i, _d, q, _u, r in items),
            "payment_pct_before_slab": pct_before_slab,
        },
        "cost_estimate": {
            "estimated_cost": estimate["estimated_cost"],
            "completed_value_estimate": estimate["completed_value_estimate"],
        },
        "risk_assessment": risk,
        # The one thing no tool can produce. A capture fills it from the model;
        # here it stands in so the schema check covers everything else.
        "explanation": {
            "owner_view": "Placeholder — only the explainer agent writes this.",
            "officer_view": "Placeholder — only the explainer agent writes this.",
        },
    }

    result = parse_state(state)
    for key, message in result.errors.items():
        print(f"{BAD} {key}: {message.splitlines()[0]}")
    if result.output is None:
        print("\n  The real tool output does NOT satisfy the schema the screens read.")
        return False

    findings = result.output.boq_findings
    print(f"{OK} PipelineOutput validates")
    print(f"  {len(findings.line_items)} line items, {len(findings.flags)} flags")
    for flag in findings.flags:
        print(f"    {flag.type:<15} {flag.label:<13} {flag.tone:<8} item {flag.item}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--loan", default="1001")
    parser.add_argument("--variant", default="ravi", choices=sorted(boq_data.VARIANTS))
    parser.add_argument("--region", default="Hyderabad")
    args = parser.parse_args()

    from app.fixtures.loader import load_loan_facts

    facts = load_loan_facts(args.loan)
    items, payment, _meta = boq_data.VARIANTS[args.variant]

    print("=" * 72)
    print(f"  Neev — grounding verification, loan {args.loan} ({args.variant})")
    print(f"  {facts['locality']} · {facts['built_up_sqft']} sqft · "
          f"sanctioned INR {facts['sanctioned']:,}")
    print("  BigQuery: REAL.  Gemini: unreachable by construction.")
    print("=" * 72)

    flags, matched = check_benchmarks(items)
    scope_flags, pct_before_slab = check_ratios_and_scope(items, payment)
    flags += scope_flags
    estimate = check_cost(facts["built_up_sqft"], facts["locality"].split(",")[0], args.region)
    risk = check_risk(estimate, facts, facts["stage"])
    valid = check_schema(flags, estimate, risk, items, pct_before_slab)

    _rule("verdict")
    print(f"  benchmarks matched   {matched}/{len(items)}")
    print(f"  flags raised         {len(flags)}")
    print(f"  schema validates     {'yes' if valid else 'NO'}")
    print(
        "\n  Verified without a model: benchmark lookups, deviation maths, scope\n"
        "  and ratio checks, cost estimation, exposure and the recommendation,\n"
        "  and that all of it fits the shape the screens read.\n"
        "  Still unverified, because only a model can do it: reading the PDF into\n"
        "  line items, and classifying a site photo."
    )
    sys.exit(0 if valid and matched else 1)


if __name__ == "__main__":
    main()
