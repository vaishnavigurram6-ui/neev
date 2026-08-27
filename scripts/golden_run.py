# golden_run.py — Day-2 §3 wiring & test loop, run programmatically.
#
# Drives the full 5-agent pipeline through ADK's InMemoryRunner for the three
# demo-proof cases and checks the outcome against expectations:
#
#   golden    sample_boq.pdf + loan 1001 + slab photos  -> HOLD, >=4 flags
#   clean     clean_boq.pdf  + loan 1002 + slab photos  -> RELEASE
#   escalate  sample_boq.pdf + loan 1001 + blurry photo -> ESCALATE
#
# Requires GCP creds + BigQuery fixtures loaded (Cloud Shell) — this cannot run
# in the offline sandbox. Usage, from the repo parent directory:
#
#   python3 -m neev.scripts.golden_run --case golden  --photos demo_assets/slab1.jpg demo_assets/slab2.jpg
#   python3 -m neev.scripts.golden_run --case clean   --photos demo_assets/slab1.jpg
#   python3 -m neev.scripts.golden_run --case escalate --photos demo_assets/blurry.jpg
#   python3 -m neev.scripts.golden_run --all --photos ... --blurry demo_assets/blurry.jpg
#
# (Or run from the repo root with PYTHONPATH=..; the import fallback below
#  also lets `python3 scripts/golden_run.py` work from the repo root.)

import argparse
import asyncio
import csv
import mimetypes
import os
import sys

from google.genai import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from buildguard.agent import root_agent  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures")

CASES = {
    "golden": {
        "boq": "sample_boq.pdf", "loan_id": 1001, "claimed_stage": "slab",
        "location": "Kompally, Hyderabad", "area_sqft": 1800,
        "expect_recommendation": "HOLD", "expect_min_flags": 4,
    },
    "clean": {
        "boq": "clean_boq.pdf", "loan_id": 1002, "claimed_stage": "slab",
        "location": "Miyapur, Hyderabad", "area_sqft": 1750,
        "expect_recommendation": "RELEASE", "expect_min_flags": 0,
    },
    "escalate": {
        "boq": "sample_boq.pdf", "loan_id": 1001, "claimed_stage": "slab",
        "location": "Kompally, Hyderabad", "area_sqft": 1800,
        "expect_recommendation": "ESCALATE", "expect_min_flags": 0,
    },
}


def loan_context(loan_id):
    """Latest tranche row for the loan from the draw-schedule fixture."""
    latest = None
    with open(os.path.join(FIXTURES, "draw_schedule.csv")) as f:
        for row in csv.DictReader(f):
            if int(row["loan_id"]) == loan_id and (
                    latest is None or int(row["tranche_no"]) > int(latest["tranche_no"])):
                latest = row
    if latest is None:
        raise SystemExit(f"loan {loan_id} not in draw_schedule.csv")
    return latest


def build_message(case, photos):
    loan = loan_context(case["loan_id"])
    text = (
        f"Tranche review request.\n"
        f"Location: {case['location']}. Built-up area: {case['area_sqft']} sqft.\n"
        f"Sanctioned amount: INR {loan['sanctioned']}. "
        f"Cumulative disbursed: INR {loan['disbursed_cum']}.\n"
        f"Claimed construction stage: {case['claimed_stage']}.\n"
        f"The contractor's BoQ is attached; site photos: {', '.join(photos)}.\n"
        f"Run the full review and give the tranche recommendation."
    )
    parts = [types.Part.from_text(text=text)]
    boq_path = os.path.join(FIXTURES, case["boq"])
    with open(boq_path, "rb") as f:
        parts.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
    for p in photos:
        mime = mimetypes.guess_type(p)[0] or "image/jpeg"
        with open(p, "rb") as f:
            parts.append(types.Part.from_bytes(data=f.read(), mime_type=mime))
    return types.Content(role="user", parts=parts)


async def run_case(name, photos):
    from google.adk.runners import InMemoryRunner  # import here: needs full ADK env

    case = CASES[name]
    runner = InMemoryRunner(agent=root_agent, app_name="neev")
    session = await runner.session_service.create_session(
        app_name="neev", user_id="demo")

    print(f"\n=== case: {name} (loan {case['loan_id']}, {case['boq']}) ===")
    async for event in runner.run_async(user_id="demo", session_id=session.id,
                                        new_message=build_message(case, photos)):
        if event.author and event.is_final_response() and event.content:
            txt = "".join(p.text or "" for p in event.content.parts)[:200]
            print(f"  [{event.author}] {txt.strip()[:160]}")

    session = await runner.session_service.get_session(
        app_name="neev", user_id="demo", session_id=session.id)
    state = session.state

    # ---- evaluate expectations (lenient text checks over output_key state)
    ok = True
    risk = str(state.get("risk_assessment", ""))
    want = case["expect_recommendation"]
    if want not in risk:
        ok = False
        print(f"  FAIL recommendation: wanted {want}, risk_assessment was: {risk[:300]}")
    else:
        print(f"  ok   recommendation: {want}")

    boq = str(state.get("boq_findings", ""))
    nflags = boq.count('"type"')
    if nflags < case["expect_min_flags"]:
        ok = False
        print(f"  FAIL flags: wanted >= {case['expect_min_flags']}, counted {nflags}")
    elif case["expect_min_flags"]:
        print(f"  ok   flags: {nflags} >= {case['expect_min_flags']}")

    explanation = str(state.get("explanation", ""))
    for view in ("owner_view", "officer_view"):
        if view not in explanation:
            ok = False
            print(f"  FAIL explanation missing {view}")

    print(f"  => {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=list(CASES), help="run one case")
    ap.add_argument("--all", action="store_true", help="run all three cases")
    ap.add_argument("--photos", nargs="+", required=True,
                    help="site photo paths (clear slab-stage photos)")
    ap.add_argument("--blurry", help="blurry photo for the escalate case (with --all)")
    args = ap.parse_args()

    results = {}
    if args.all:
        for name in CASES:
            photos = [args.blurry] if (name == "escalate" and args.blurry) else args.photos
            results[name] = asyncio.run(run_case(name, photos))
    elif args.case:
        results[args.case] = asyncio.run(run_case(args.case, args.photos))
    else:
        ap.error("pass --case NAME or --all")

    print("\n==== summary ====")
    for name, ok in results.items():
        print(f"  {name:9s} {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
