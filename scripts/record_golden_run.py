#!/usr/bin/env python3
"""Overwrite the authored fixtures with a real captured pipeline run.

┌──────────────────────────────────────────────────────────────────────────────┐
│  DO NOT RUN THIS WHILE THE DRY RUN IS ACTIVE.                                │
│                                                                              │
│  It drives the live five-agent pipeline: Gemini completions, a Gemini vision  │
│  call, and BigQuery lookups. Every one of those bills the project. CLAUDE.md  │
│  carries the rule -- if its dry-run section still says ACTIVE, this script is │
│  off limits, and only the repo owner may lift that.                          │
│                                                                              │
│  It refuses to start unless NEEV_ALLOW_BILLED_CALLS=1 is set explicitly.      │
└──────────────────────────────────────────────────────────────────────────────┘

Why it exists: the fixtures in src/backend/app/fixtures/ were authored by hand,
transcribed from the mockups, precisely because recording a real run would have
spent credits. They are shaped like the pipeline's real output (spec §5.1a), and
a contract test proves it. So when credits are available, capturing a real run is
a swap, not a migration -- the schemas do not change and no screen is touched.

    export GOOGLE_API_KEY=...            # from .env.disabled-backup
    export GOOGLE_CLOUD_PROJECT=buildguard-ai-2026
    export NEEV_ALLOW_BILLED_CALLS=1
    python3 scripts/record_golden_run.py --loan 1001 --boq fixtures/sample_boq.pdf

Photos are optional. Without them the pipeline has nothing to inspect, so
`inspection_result` is legitimately absent and PipelineOutput allows that:

    python3 scripts/record_golden_run.py --loan 1001 --boq fixtures/sample_boq.pdf \
        --photos demo_assets/slab1.jpg demo_assets/slab2.jpg

THE RUN IS SAVED BEFORE IT IS PARSED. Raw session state lands in .golden_runs/
first, so a validation failure costs nothing but a re-parse. Fix the parse layer
and replay it for free -- no second billed run:

    python3 scripts/record_golden_run.py --loan 1001 --from-raw .golden_runs/1001-<ts>.json

Then re-run the contract test, which is the whole point:

    cd src/backend && .venv/bin/python -m pytest tests/test_fixture_contract.py -q

If the captured run fails that test, the live pipeline is not emitting the shape
the screens read -- fix the pipeline or the parse layer, never the test.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "src" / "backend" / "app" / "fixtures"
RAW_DIR = REPO_ROOT / ".golden_runs"

sys.path.insert(0, str(REPO_ROOT / "src" / "agents"))
sys.path.insert(0, str(REPO_ROOT / "src" / "backend"))


def _refuse_unless_explicitly_permitted() -> None:
    if os.environ.get("NEEV_ALLOW_BILLED_CALLS") != "1":
        sys.exit(
            "Refusing to run: this script makes billed Gemini and BigQuery calls.\n"
            "Set NEEV_ALLOW_BILLED_CALLS=1 only if the repo owner has lifted the dry\n"
            "run in CLAUDE.md. Nothing was called."
        )
    if not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("GOOGLE_API_KEY is not set. Nothing was called.")


async def capture(loan_id: str, boq: Path, photos: list[Path]) -> dict:
    """Drive the live pipeline and return its raw session state, unparsed.

    Deliberately does no validation. Parsing is where a run gets thrown away on
    a technicality, and this is the only part that costs money -- so it returns
    whatever the model said and lets the caller save it before judging it.
    """
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    from neev_pipeline.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="neev")
    session = await runner.session_service.create_session(
        app_name="neev", user_id="recorder"
    )

    # Per loan, from the committed data files. Hardcoding 1001's facts here
    # meant capturing 1002 ran the real pipeline against the wrong house.
    from app.fixtures.loader import load_loan_facts

    facts = load_loan_facts(loan_id)
    stage_claim = (
        f"Claimed construction stage: {facts['stage']}. "
        if photos
        else "No site photos supplied; do not assess the construction stage. "
    )
    parts = [
        types.Part.from_text(
            text=(
                f"Tranche review request for loan {loan_id}. "
                f"Location: {facts['locality']}. "
                f"Built-up area: {facts['built_up_sqft']} sqft. "
                f"Sanctioned amount: INR {facts['sanctioned']}. "
                f"Cumulative disbursed: INR {facts['disbursed']}. "
                f"{stage_claim}Run the full review."
            )
        ),
        types.Part.from_bytes(data=boq.read_bytes(), mime_type="application/pdf"),
    ]
    for photo in photos:
        parts.append(
            types.Part.from_bytes(data=photo.read_bytes(), mime_type="image/jpeg")
        )

    async for event in runner.run_async(
        user_id="recorder",
        session_id=session.id,
        new_message=types.Content(role="user", parts=parts),
    ):
        if event.author and event.is_final_response():
            print(f"  [{event.author}] responded")

    state = (
        await runner.session_service.get_session(
            app_name="neev", user_id="recorder", session_id=session.id
        )
    ).state
    # Session state can hold non-serialisable values alongside the output keys.
    # Keep only what is JSON-round-trippable, so saving cannot fail after the
    # money is spent.
    return {k: v for k, v in state.items() if _serialisable(v)}


def _serialisable(value: object) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True


def _save_raw(loan_id: str, state: dict) -> Path:
    RAW_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RAW_DIR / f"{loan_id}-{stamp}.json"
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _write_fixture(loan_id: str, state: dict, out: Path | None) -> int:
    """Parse a raw capture into the loan's fixture. Returns a process exit code."""
    from app.services.pipeline_parse import parse_state

    target = out or FIXTURE_DIR / f"loan_{loan_id}_pipeline.json"
    base = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}

    result = parse_state(state, base=base)

    for key, message in result.errors.items():
        print(f"  FAILED {key}: {message.splitlines()[0]}", file=sys.stderr)

    if result.output is None:
        print(
            "\nNothing written: the capture does not satisfy PipelineOutput.\n"
            "The raw run is saved, so fix app/services/pipeline_parse.py (or the\n"
            "agent prompts) and replay it with --from-raw. No new billed calls.",
            file=sys.stderr,
        )
        return 1

    target.write_text(
        json.dumps(result.parsed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {target}")
    kept = sorted(set(base) & set(result.parsed) - set(result.output.model_dump()))
    if kept:
        print(f"  authored values preserved: {', '.join(kept)}")
    print(
        "Now run: cd src/backend && "
        ".venv/bin/python -m pytest tests/test_fixture_contract.py -q"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--loan", default="1001")
    parser.add_argument("--boq", type=Path, help="Required unless --from-raw is given.")
    parser.add_argument(
        "--photos",
        type=Path,
        nargs="*",
        default=[],
        help="Optional. Without photos there is no inspection_result, which is valid.",
    )
    parser.add_argument(
        "--from-raw",
        type=Path,
        default=None,
        help="Re-parse a saved capture from .golden_runs/. Makes no billed calls.",
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="Defaults to the loan's fixture file."
    )
    args = parser.parse_args()

    if args.from_raw:
        # The whole point of the flag: iterate on the parse layer for free.
        state = json.loads(args.from_raw.read_text(encoding="utf-8"))
        print(f"Re-parsing {args.from_raw} — no billed calls.")
        sys.exit(_write_fixture(args.loan, state, args.out))

    if args.boq is None:
        parser.error("--boq is required unless --from-raw is given")

    from app.fixtures.loader import load_loan_facts

    # Data checks first, credentials second: a loan that cannot be captured
    # should say so without the operator having to export anything.
    try:
        facts = load_loan_facts(args.loan)
    except KeyError as exc:
        sys.exit(f"{exc.args[0]} Nothing was called.")
    # estimate_construction_cost divides by plot_area_sqft; without it the cost
    # agent returns nonsense and the run is wasted. Only 1001 and 1002 carry one.
    if not facts["built_up_sqft"]:
        sys.exit(
            f"Loan {args.loan} has no built_up_sqft in portfolio_rows.json.\n"
            "estimate_construction_cost needs it, so the capture would produce a\n"
            "meaningless cost estimate. Add it there first. Nothing was called."
        )

    _refuse_unless_explicitly_permitted()

    print(f"Recording a LIVE run for loan {args.loan}. This will bill the project.")
    print(
        f"  {facts['locality']} · {facts['built_up_sqft']} sqft · "
        f"sanctioned INR {facts['sanctioned']:,} · drawn INR {facts['disbursed']:,} · "
        f"claiming {facts['stage']}"
    )
    if not args.photos:
        print("  no photos: inspection_result will be absent, which is valid")
    state = asyncio.run(capture(args.loan, args.boq, list(args.photos)))

    raw_path = _save_raw(args.loan, state)
    print(f"Raw session state saved to {raw_path}")
    print(f"  captured keys: {', '.join(sorted(state)) or '(none)'}")

    sys.exit(_write_fixture(args.loan, state, args.out))


if __name__ == "__main__":
    main()
