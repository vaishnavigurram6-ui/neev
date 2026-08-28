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

Usage, once the owner has lifted the dry run:

    export GOOGLE_API_KEY=...            # from .env.disabled-backup
    export GOOGLE_CLOUD_PROJECT=buildguard-ai-2026
    export NEEV_ALLOW_BILLED_CALLS=1
    python3 scripts/record_golden_run.py --loan 1001 --boq fixtures/sample_boq.pdf \
        --photos demo_assets/slab1.jpg demo_assets/slab2.jpg

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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "src" / "backend" / "app" / "fixtures"


def _refuse_unless_explicitly_permitted() -> None:
    if os.environ.get("NEEV_ALLOW_BILLED_CALLS") != "1":
        sys.exit(
            "Refusing to run: this script makes billed Gemini and BigQuery calls.\n"
            "Set NEEV_ALLOW_BILLED_CALLS=1 only if the repo owner has lifted the dry\n"
            "run in CLAUDE.md. Nothing was called."
        )
    if not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("GOOGLE_API_KEY is not set. Nothing was called.")


async def record(loan_id: str, boq: Path, photos: list[Path]) -> dict:
    """Drive the live pipeline and return its five output_key values, parsed.

    The values arrive in session state as raw model TEXT, not dicts -- which is
    why this needs a parse-and-validate step and why the plan deferred it. Each
    is validated against the same Pydantic model the fixtures satisfy, so a
    malformed response fails here rather than three screens downstream.
    """
    sys.path.insert(0, str(REPO_ROOT / "src" / "agents"))
    sys.path.insert(0, str(REPO_ROOT / "src" / "backend"))

    from google.adk.runners import InMemoryRunner
    from google.genai import types
    from neev_pipeline.agent import root_agent

    from app.schemas.pipeline import (
        BoqFindings,
        CostEstimate,
        Explanation,
        InspectionResult,
        RiskAssessment,
    )

    runner = InMemoryRunner(agent=root_agent, app_name="neev")
    session = await runner.session_service.create_session(app_name="neev", user_id="recorder")

    parts = [
        types.Part.from_text(
            text=(
                f"Tranche review request for loan {loan_id}. "
                "Location: Kompally, Hyderabad. Built-up area: 1800 sqft. "
                "Sanctioned amount: INR 2800000. Cumulative disbursed: INR 1800000. "
                "Claimed construction stage: slab. Run the full review."
            )
        ),
        types.Part.from_bytes(data=boq.read_bytes(), mime_type="application/pdf"),
    ]
    for photo in photos:
        parts.append(types.Part.from_bytes(data=photo.read_bytes(), mime_type="image/jpeg"))

    async for event in runner.run_async(
        user_id="recorder", session_id=session.id, new_message=types.Content(role="user", parts=parts)
    ):
        if event.author and event.is_final_response():
            print(f"  [{event.author}] responded")

    state = (
        await runner.session_service.get_session(
            app_name="neev", user_id="recorder", session_id=session.id
        )
    ).state

    models = {
        "boq_findings": BoqFindings,
        "cost_estimate": CostEstimate,
        "inspection_result": InspectionResult,
        "risk_assessment": RiskAssessment,
        "explanation": Explanation,
    }

    out: dict = {}
    for key, model in models.items():
        raw = state.get(key)
        if raw is None:
            print(f"  WARNING: {key} is absent from session state", file=sys.stderr)
            continue
        out[key] = model.model_validate(_as_json(raw)).model_dump(mode="json")
    return out


def _as_json(raw) -> dict:
    """Model output is text, often fenced. Extract the JSON object."""
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.lower().startswith("json") else text
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in: {text[:200]}")
    return json.loads(text[start : end + 1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--loan", default="1001")
    parser.add_argument("--boq", type=Path, required=True)
    parser.add_argument("--photos", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--out", type=Path, default=None, help="Defaults to the loan's fixture file."
    )
    args = parser.parse_args()

    _refuse_unless_explicitly_permitted()

    print(f"Recording a LIVE run for loan {args.loan}. This will bill the project.")
    captured = asyncio.run(record(args.loan, args.boq, args.photos))

    target = args.out or FIXTURE_DIR / f"loan_{args.loan}_pipeline.json"
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    # payment_schedule has no output_key -- it is read from the document, not the
    # pipeline -- so the authored value is preserved rather than dropped.
    merged = {**existing, **captured}
    target.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {target}")
    print("Now run: cd src/backend && .venv/bin/python -m pytest tests/test_fixture_contract.py -q")


if __name__ == "__main__":
    main()
