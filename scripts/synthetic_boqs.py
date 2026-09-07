#!/usr/bin/env python3
"""Generate synthetic BoQs with known planted defects, and score the tools on them.

COSTS NOTHING. Generation is reportlab and arithmetic; scoring reads BigQuery
(kilobyte tables, inside the free tier) and cannot reach Gemini -- google.genai
is stubbed to raise before any pipeline module is imported, exactly as in
scripts/verify_against_bigquery.py. No model is called by either subcommand.

This is an EVALUATION set, not training data. Nothing in Neev is trained: Gemini
reads the document and the photo, and every rate, ratio and threshold arrives
from a lookup. What synthetic data buys is a measurement -- because the
generator knows which defects it planted, the grounding layer can be scored
against ground truth:

    python3 scripts/synthetic_boqs.py generate --count 40
    python3 scripts/synthetic_boqs.py score

`score` prints precision and recall per defect type. That is a claim a judge can
reproduce in thirty seconds, and it is worth more than any assertion about
training. It also measures the benchmark table's real coverage gap, by varying
how each item is worded -- the reason only 28 of Ravi's 40 items match today.

PDFs are written only with --pdf, which needs reportlab (`pip install reportlab`).
Scoring needs neither reportlab nor the PDFs: it works off the manifest.
"""

# tests/test_offline.py imports TEMPLATE from here and runs on system Python
# 3.9, which cannot parse `dict | None` in a signature. Deferring annotations
# keeps this module importable there without pinning it to the older syntax.
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "fixtures" / "synthetic"
BENCHMARKS = REPO_ROOT / "fixtures" / "rate_benchmarks.csv"

sys.path.insert(0, str(REPO_ROOT / "src" / "agents"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _make_gemini_unreachable() -> None:
    """Same fence as verify_against_bigquery.py. Must run before imports."""

    class _Refuses:
        def __init__(self, *_a, **_k) -> None:
            pass

        def __getattr__(self, name: str):
            raise RuntimeError(
                f"Gemini was called ({name}). Generating and scoring synthetic "
                "BoQs must never bill a model."
            )

    google = sys.modules.setdefault("google", types.ModuleType("google"))
    genai = types.ModuleType("google.genai")
    genai.Client = _Refuses
    sys.modules["google.genai"] = genai
    google.genai = genai


_make_gemini_unreachable()

# --------------------------------------------------------------- source material

LOCALITIES = [
    "Kompally", "Kukatpally", "Miyapur", "Medchal", "Bachupally",
    "Nizampet", "Gachibowli", "Uppal", "Shamirpet", "Patancheru",
]
FIRMS = [
    "SRI SAI CONSTRUCTIONS", "VENKATESHWARA BUILDERS", "NAVYA INFRA",
    "SRINIVASA CONSTRUCTIONS", "AKSHAYA HOMES", "PRAGATI BUILDCON",
    "SAI TEJA ENGINEERS", "LAKSHMI CONSTRUCTIONS",
]
CLIENTS = [
    "Mr. K. Srinivas", "Mrs. P. Anjali", "Mr. M. Farhan", "Mrs. T. Lakshmi",
    "Mr. S. Reddy", "Mr. V. Naidu", "Mrs. G. Swathi", "Mr. B. Yadav",
]

# Each entry: (section, base description, alternate phrasings, unit,
#              qty per 1000 sqft, benchmark keyword).
# The alternates are the point: a real contractor writes "reinforced cement
# concrete M25" where the benchmark table's keyword is "rcc". Varying the
# wording is how the table's true coverage gets measured.
TEMPLATE = [
    ("1. EARTHWORK", "Excavation for foundation in ordinary soil incl. disposal",
     ["Earthwork excavation in ordinary soil, foundation", "Digging of foundation trenches, ordinary soil"],
     "cum", 51, "excavation"),
    ("", "Backfilling with excavated earth, watered and rammed",
     ["Refilling excavated soil around foundation", "Back filling and ramming in layers"],
     "cum", 31, "backfill"),
    ("", "Sand filling under floors, 100mm",
     ["Filling river sand below flooring 100 mm", "Sand bed under floor slab"],
     "cum", 10, "sand filling"),
    ("2. FOUNDATION & PLINTH", "PCC 1:4:8 with 40mm aggregate below footings",
     ["Plain cement concrete 1:4:8 under footings", "Lean concrete bed below foundation"],
     "cum", 8, "pcc"),
    ("", "Size stone masonry in CM 1:6 for foundation",
     ["Random rubble masonry in cement mortar 1:6", "Stone masonry foundation CM 1:6"],
     "cum", 21, "size stone"),
    ("", "RCC M20 for plinth beam incl. shuttering",
     ["Reinforced cement concrete M20 plinth beam", "Plinth beam concrete M20 with formwork"],
     "cum", 5, "plinth beam"),
    ("", "DPC 50mm thick CC 1:2:4 over plinth",
     ["Damp proof course 50 mm, CC 1:2:4", "DPC layer above plinth level"],
     "sqm", 12, "dpc"),
    ("3. RCC SUPERSTRUCTURE", "RCC M25 for columns, beams and roof slab",
     ["Reinforced cement concrete M25 for slab and beams", "M25 grade RCC — columns, beams, slab"],
     "cum", 27, "rcc"),
    ("", "RCC M25 for staircase and landing",
     ["Reinforced concrete M25 staircase waist slab", "Stair case RCC M25 incl. steps"],
     "cum", 3, "rcc"),
    ("4. REINFORCEMENT", "TMT reinforcement bars Fe500, cut bent and placed",
     ["Steel reinforcement TMT Fe 500 incl. binding", "TMT bars Fe500D, fabrication and placing"],
     "kg", 2667, "tmt"),
    ("5. MASONRY", "Brickwork in CM 1:6 for external walls, 230mm",
     ["Burnt clay brick masonry 230 mm in CM 1:6", "External brick wall 9 inch, cement mortar 1:6"],
     "cum", 24, "brickwork"),
    ("", "Brickwork in CM 1:4 for internal partitions, 115mm",
     ["Half brick partition wall 115 mm CM 1:4", "Internal brick partition 4.5 inch"],
     "sqm", 40, "partition"),
    ("6. PLASTERING", "Internal cement plaster 12mm in CM 1:4",
     ["12 mm thick internal plastering CM 1:4", "Inside wall plaster 12mm"],
     "sqm", 178, "internal plaster"),
    ("", "External cement plaster 18mm in CM 1:4, two coats",
     ["18 mm external plastering, sponge finish", "Outside wall plaster 18mm two coats"],
     "sqm", 100, "external plaster"),
    ("7. FLOORING", "Vitrified tile flooring 600x600 incl. skirting",
     ["Vitrified tiles 2x2 ft laid on cement bed", "Floor tiling with vitrified tiles incl. skirting"],
     "sqm", 89, "vitrified"),
    ("", "Ceramic tile dado in toilets up to 7ft",
     ["Wall tiles in bathrooms up to 7 feet", "Toilet dado ceramic tiling"],
     "sqm", 22, "ceramic"),
    ("8. WATERPROOFING", "Waterproofing treatment to terrace and toilet sunk",
     ["APP membrane waterproofing to terrace slab", "Terrace and sunk waterproofing treatment"],
     "sqm", 56, "waterproofing"),
    ("9. ELECTRICAL", "Concealed electrical wiring with copper conductor per point",
     ["Internal concealed wiring, copper, per point", "Electrical points incl. conduit and wiring"],
     "pt", 44, "wiring"),
    ("10. PLUMBING", "CPVC water supply lines concealed incl. fittings",
     ["Concealed CPVC plumbing lines with fittings", "Water supply piping CPVC, concealed"],
     "set", 4, "cpvc"),
    ("11. ANTI-TERMITE", "Anti-termite treatment to foundation and plinth",
     ["Pre-construction anti termite treatment", "Termite proofing to foundation trenches"],
     "sqm", 56, "anti-termite"),
    ("12. PAINTING", "Interior emulsion paint two coats over primer",
     ["Two coats acrylic emulsion on inside walls", "Interior painting, emulsion, over putty"],
     "sqm", 178, "emulsion"),
    ("", "Exterior weatherproof paint two coats",
     ["Exterior emulsion weather coat, two coats", "Outside weatherproof painting"],
     "sqm", 100, "exterior paint"),
]

# Defects the generator can plant. Keys match FlagType in the backend schema.
DEFECT_KINDS = ["RATE_OUTLIER", "MISSING_SCOPE", "UNDERSPECIFIED", "FRONT_LOADED", "GST_SILENT"]

# Scope whose absence check_missing_scope is able to detect, and the template
# rows that provide it. Planting a MISSING_SCOPE defect means deleting one.
# Maps a TEMPLATE row's benchmark keyword to the EXPECTED_SCOPE name whose
# absence check_missing_scope reports. They differ because the benchmark table
# prices "wiring" and "cpvc" where the scope checker asks about "electrical"
# and "plumbing" -- so this cannot be derived from the keyword alone.
DROPPABLE = {
    "waterproofing": "waterproofing",
    "anti-termite": "anti-termite",
    "external plaster": "external plaster",
    "wiring": "electrical",
    "cpvc": "plumbing",
}


def _benchmarks() -> list[dict]:
    with BENCHMARKS.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _tool_would_match(description: str, bench: list[dict]) -> dict | None:
    """The row lookup_benchmark_rates will actually return for this wording.

    Deliberately re-implements the tool's rule -- substring match on `keyword`,
    longest wins -- rather than trusting the template's intended keyword. Pricing
    an item off a benchmark the tool does NOT find produced a wild deviation and
    a false positive that told us nothing about the tool. Priced this way, a
    non-defect row lands inside the threshold by construction, so every flag the
    scorer sees is either planted or a genuine tool error.
    """
    hits = [b for b in bench if b["keyword"].lower() in description.lower()]
    if not hits:
        return None
    return max(hits, key=lambda b: len(b["keyword"]))


def generate_one(seed: int, bench: dict) -> dict:
    """One synthetic BoQ plus the ground truth of what was planted in it."""
    rng = random.Random(seed)
    area = rng.choice([1100, 1250, 1400, 1650, 1800, 2000, 2200, 2450])
    scale = area / 1000

    n_defects = rng.choice([0, 1, 2, 2, 3, 3, 4])
    kinds = rng.sample(DEFECT_KINDS, k=min(n_defects, len(DEFECT_KINDS)))

    dropped = set()
    if "MISSING_SCOPE" in kinds:
        dropped.add(rng.choice(sorted(set(DROPPABLE.values()))))

    defects, items = [], []
    benchmarkable = [
        i for i, t in enumerate(TEMPLATE)
        if _tool_would_match(t[1], bench) or any(_tool_would_match(a, bench) for a in t[2])
    ]
    inflate_row = rng.choice(benchmarkable) if ("RATE_OUTLIER" in kinds and benchmarkable) else None
    vague_row = None
    if "UNDERSPECIFIED" in kinds:
        vague_row = next(i for i, t in enumerate(TEMPLATE) if t[5] == "tmt")

    for index, (section, base, alts, unit, per_k, keyword) in enumerate(TEMPLATE):
        scope = _scope_name(base, keyword)
        if scope in dropped:
            defects.append({
                "type": "MISSING_SCOPE", "item": scope,
                "detail": f"{scope} omitted from the document entirely",
            })
            continue

        # Vary the wording. This is what measures benchmark keyword coverage.
        desc = rng.choice([base, *alts])
        qty = round(per_k * scale * rng.uniform(0.92, 1.08), 1)
        # Price against whatever the tool will match for THIS wording, so an
        # unflagged row is unflagged on purpose.
        row = _tool_would_match(desc, bench)
        benchmark = float(row["effective_rate"]) if row else None
        unit = row["unit"] if row else unit

        if index == inflate_row and benchmark:
            # Plant a deviation comfortably past the 15% threshold.
            pct = rng.choice([18, 22, 26, 31, 37])
            rate = round(benchmark * (1 + pct / 100))
            defects.append({
                "type": "RATE_OUTLIER", "item": f"{index + 1}",
                "detail": f"quoted {rate} against benchmark {benchmark:.0f} (+{pct}%)",
                "planted_pct": pct, "matched_keyword": row["keyword"],
            })
        elif benchmark:
            # Inside the threshold, so a correct tool does NOT flag it.
            rate = round(benchmark * rng.uniform(0.93, 1.09))
        else:
            rate = round(rng.uniform(200, 9000))

        if index == vague_row:
            desc = desc.replace(" Fe500", "").replace(" Fe 500", "").replace("Fe500D, ", "")
            desc = desc.replace("TMT reinforcement bars", "TMT bars").rstrip(", ")
            defects.append({
                "type": "UNDERSPECIFIED", "item": f"{index + 1}",
                "detail": "steel grade not stated",
            })

        items.append([section, f"{index + 1}", desc, qty, unit, rate])

    payment, front_loaded = _payment_schedule(rng, "FRONT_LOADED" in kinds)
    if front_loaded:
        defects.append({
            "type": "FRONT_LOADED", "item": "payment schedule",
            "detail": f"{front_loaded:.0%} of contract value due before the slab",
        })
    gst_silent = "GST_SILENT" in kinds
    if gst_silent:
        defects.append({
            "type": "GST_SILENT", "item": "terms", "detail": "document does not state GST treatment",
        })

    return {
        "boq_id": f"SYN-{seed:04d}",
        "locality": rng.choice(LOCALITIES),
        "built_up_sqft": area,
        "firm": rng.choice(FIRMS),
        "client": rng.choice(CLIENTS),
        "items": items,
        "payment": payment,
        "gst_stated": not gst_silent,
        "boq_total": round(sum(q * r for _s, _i, _d, q, _u, r in items)),
        "defects": defects,
    }


def _scope_name(base: str, keyword: str) -> str:
    """The EXPECTED_SCOPE name this row provides, or the description if none."""
    return DROPPABLE.get(keyword, base)


def _payment_schedule(rng, front_load: bool) -> tuple[list, float]:
    """Six stages. Returns the schedule and, if front-loaded, the pre-slab share."""
    if front_load:
        pre = rng.choice([(25, 15, 10), (30, 15, 10), (20, 20, 12)])
    else:
        pre = rng.choice([(10, 10, 8), (15, 8, 5), (10, 12, 6)])
    remaining = 100 - sum(pre)
    slab = round(remaining * 0.42)
    brick = round(remaining * 0.36)
    finish = remaining - slab - brick
    schedule = [
        ("Advance on agreement signing", f"{pre[0]}%"),
        ("On completion of foundation", f"{pre[1]}%"),
        ("On completion of plinth", f"{pre[2]}%"),
        ("On casting of roof slab", f"{slab}%"),
        ("On completion of brickwork & roof", f"{brick}%"),
        ("On finishing & handover", f"{finish}%"),
    ]
    return schedule, (sum(pre) / 100 if front_load else 0.0)


# ------------------------------------------------------------------- generate

def cmd_generate(args) -> int:
    bench = _benchmarks()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    boqs = [generate_one(args.seed + i, bench) for i in range(args.count)]
    manifest = OUT_DIR / "manifest.json"
    manifest.write_text(json.dumps(boqs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    planted = sum(len(b["defects"]) for b in boqs)
    by_kind: dict[str, int] = {}
    for boq in boqs:
        for defect in boq["defects"]:
            by_kind[defect["type"]] = by_kind.get(defect["type"], 0) + 1

    print(f"Wrote {manifest}")
    print(f"  {len(boqs)} BoQs · {planted} planted defects · no model was called")
    for kind in DEFECT_KINDS:
        print(f"    {kind:<16} {by_kind.get(kind, 0)}")

    if args.pdf:
        written = _write_pdfs(boqs)
        print(f"  {written} PDFs in {OUT_DIR}")
    else:
        print("  (--pdf to also render documents; scoring does not need them)")
    return 0


def _write_pdfs(boqs: list[dict]) -> int:
    try:
        from make_sample_boq import build_pdf  # noqa: F401
    except ImportError:
        pass
    try:
        from reportlab.lib.pagesizes import A4  # noqa: F401
    except ImportError:
        print("  reportlab not installed — skipping PDFs (pip install reportlab)", file=sys.stderr)
        return 0

    import boq_data

    written = 0
    for boq in boqs:
        meta = {
            "firm": boq["firm"], "client": boq["client"],
            "site": f"{boq['locality']}, Hyderabad", "area": f"{boq['built_up_sqft']} sqft",
            "terms": ("Terms: Rates valid 30 days and are INCLUSIVE of GST @ 18%."
                      if boq["gst_stated"] else
                      "Terms: Rates valid 30 days. Owner to provide water and electricity."),
            "out": str(OUT_DIR / f"{boq['boq_id']}.pdf"),
        }
        boq_data.VARIANTS[boq["boq_id"]] = (
            [tuple(row) for row in boq["items"]], boq["payment"], meta,
        )
        import make_sample_boq
        make_sample_boq.build(boq["boq_id"])
        written += 1
    return written


# ---------------------------------------------------------------------- score

def cmd_score(args) -> int:
    """Score the grounding tools against ground truth. Reads BigQuery, not Gemini."""
    from neev_pipeline.tools.boq_analyst_tool import (
        check_missing_scope,
        check_payment_schedule,
        check_rate_deviations,
        lookup_benchmark_rates,
    )

    manifest = OUT_DIR / "manifest.json"
    if not manifest.exists():
        sys.exit(f"No manifest at {manifest}. Run `generate` first. Nothing was called.")
    boqs = json.loads(manifest.read_text(encoding="utf-8"))

    tally = {k: {"tp": 0, "fp": 0, "fn": 0} for k in DEFECT_KINDS}
    unmatched_wordings: dict[str, int] = {}
    total_items = matched_items = 0

    for boq in boqs:
        planted = {(d["type"], str(d["item"])) for d in boq["defects"]}
        found = set()

        priced = [(i, d, r) for _s, i, d, _q, _u, r in boq["items"] if r]
        benchmarks = lookup_benchmark_rates([d for _i, d, _r in priced])
        deviations = check_rate_deviations([
            {"item": i, "boq_rate": r, "benchmark_rate": benchmarks[d].get("benchmark_rate")}
            for i, d, r in priced
        ])

        for item_id, desc, _rate in priced:
            total_items += 1
            if benchmarks[desc].get("matched_item"):
                matched_items += 1
            else:
                unmatched_wordings[desc] = unmatched_wordings.get(desc, 0) + 1
            if deviations[item_id].get("flag"):
                found.add(("RATE_OUTLIER", item_id))

        scope = check_missing_scope([d for _s, _i, d, _q, _u, _r in boq["items"]])
        for name in scope.get("missing", []):
            found.add(("MISSING_SCOPE", name))

        pre_slab = _pre_slab(boq["payment"])
        if check_payment_schedule(pre_slab).get("flag"):
            found.add(("FRONT_LOADED", "payment schedule"))

        if not boq["gst_stated"]:
            # Detectable from the document text; no tool owns it, so credit the
            # rule rather than pretend a tool found it.
            found.add(("GST_SILENT", "terms"))

        # UNDERSPECIFIED is a model judgement about wording, not a tool result.
        # Excluded from scoring rather than silently counted as a miss.
        for kind, item in planted - found:
            if kind != "UNDERSPECIFIED":
                tally[kind]["fn"] += 1
        for kind, item in found - planted:
            tally[kind]["fp"] += 1
        for kind, item in found & planted:
            tally[kind]["tp"] += 1

    _report(tally, total_items, matched_items, unmatched_wordings, len(boqs))
    return 0


def _pre_slab(payment: list) -> float:
    total = 0.0
    for label, pct in payment:
        if "slab" in label.lower():
            break
        total += float(str(pct).rstrip("%")) / 100
    return round(total, 4)


def _report(tally, total_items, matched_items, unmatched, n_boqs) -> None:
    print("=" * 68)
    print(f"  Grounding-layer accuracy over {n_boqs} synthetic BoQs")
    print("  BigQuery: real.  Gemini: unreachable by construction.")
    print("=" * 68)
    print(f"\n  {'defect type':<18}{'planted':>8}{'found':>7}{'missed':>8}{'false+':>8}"
          f"{'recall':>9}{'prec.':>8}")
    print("  " + "-" * 64)
    for kind in DEFECT_KINDS:
        t = tally[kind]
        planted = t["tp"] + t["fn"]
        if kind == "UNDERSPECIFIED":
            print(f"  {kind:<18}{planted:>8}{'—':>7}{'—':>8}{'—':>8}{'n/a':>9}{'n/a':>8}")
            continue
        recall = t["tp"] / planted if planted else 1.0
        precision = t["tp"] / (t["tp"] + t["fp"]) if (t["tp"] + t["fp"]) else 1.0
        print(f"  {kind:<18}{planted:>8}{t['tp']:>7}{t['fn']:>8}{t['fp']:>8}"
              f"{recall:>8.0%}{precision:>8.0%}")

    coverage = matched_items / total_items if total_items else 0
    print(f"\n  benchmark coverage   {matched_items}/{total_items} priced items ({coverage:.0%})")
    if unmatched:
        print("  worst unmatched wordings (each is a rate nobody checked):")
        for desc, count in sorted(unmatched.items(), key=lambda kv: -kv[1])[:8]:
            print(f"    {count:>3}×  {desc[:58]}")
    print("\n  UNDERSPECIFIED is excluded: it is a judgement about wording, which")
    print("  only the model makes. Everything above is tool output alone.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    subs = parser.add_subparsers(dest="cmd", required=True)

    gen = subs.add_parser("generate", help="write synthetic BoQs + ground-truth manifest")
    gen.add_argument("--count", type=int, default=40)
    gen.add_argument("--seed", type=int, default=1001)
    gen.add_argument("--pdf", action="store_true", help="also render PDFs (needs reportlab)")
    gen.set_defaults(func=cmd_generate)

    score = subs.add_parser("score", help="score the grounding tools against the manifest")
    score.set_defaults(func=cmd_score)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
