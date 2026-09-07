"""Loads the authored, pipeline-shaped fixtures.

The fixture is authored rather than recorded: recording a golden run would itself
spend credits, which the dry run forbids. Numbers are transcribed from the
mockups (spec 4.4); line items, quantities and rates come from
scripts/boq_data.py where the mockups only show a subset.
"""

import csv
import json
from functools import lru_cache
from pathlib import Path

from app.schemas.pipeline import PipelineOutput

_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DRAW_SCHEDULE = _REPO_ROOT / "fixtures" / "draw_schedule.csv"
_PORTFOLIO_ROWS = _DIR / "portfolio_rows.json"


@lru_cache
def load_pipeline_output(loan_id: str) -> PipelineOutput:
    path = _DIR / f"loan_{loan_id}_pipeline.json"
    if not path.exists():
        raise KeyError(f"No authored pipeline fixture for loan {loan_id!r}")
    return PipelineOutput.model_validate_json(path.read_text(encoding="utf-8"))


def available_loan_ids() -> list[str]:
    return sorted(p.stem.split("_")[1] for p in _DIR.glob("loan_*_pipeline.json"))


@lru_cache
def load_analyzing_script() -> dict:
    return json.loads((_DIR / "analyzing_script.json").read_text(encoding="utf-8"))


@lru_cache
def load_loan_facts(loan_id: str) -> dict:
    """The loan's real-world inputs, for the prompt a live capture sends.

    Read from the committed data files rather than the seeded database, because
    neev.db is git-ignored: a fresh clone in Cloud Shell must be able to record
    a run without seeding first. Same two sources the seed itself reads, so the
    captured run and the served screens cannot disagree about the house.

    `stage` is the CLAIMED stage: the milestone the furthest tranche is for, and
    so what the owner is asserting when asking for its release. Deliberately not
    the CSV's `observed_stage` -- for loan 1003 those differ (milestone slab,
    observed plinth, i.e. behind schedule), and telling the visual inspector
    what was seen on site pre-empts the one judgement it exists to make.
    """
    rows = {
        row["loan_id"]: row
        for row in json.loads(_PORTFOLIO_ROWS.read_text(encoding="utf-8"))
    }
    if loan_id not in rows:
        raise KeyError(f"No portfolio row for loan {loan_id!r}")
    row = rows[loan_id]

    with _DRAW_SCHEDULE.open(newline="", encoding="utf-8") as handle:
        tranches = [r for r in csv.DictReader(handle) if r["loan_id"] == loan_id]
    if not tranches:
        raise KeyError(f"No draw schedule for loan {loan_id!r}")
    furthest = max(tranches, key=lambda r: int(r["tranche_no"]))

    return {
        # Every loan in this book is in Hyderabad; the CSV stores the locality
        # alone, and estimate_construction_cost matches on city + location.
        "locality": f"{row['locality']}, Hyderabad",
        "built_up_sqft": row.get("built_up_sqft"),
        "sanctioned": int(furthest["sanctioned"]),
        "disbursed": int(furthest["disbursed_cum"]),
        "stage": furthest["milestone"],
    }
