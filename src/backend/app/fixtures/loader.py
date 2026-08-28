"""Loads the authored, pipeline-shaped fixtures.

The fixture is authored rather than recorded: recording a golden run would itself
spend credits, which the dry run forbids. Numbers are transcribed from the
mockups (spec 4.4); line items, quantities and rates come from
scripts/boq_data.py where the mockups only show a subset.
"""

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.pipeline import PipelineOutput

_DIR = Path(__file__).resolve().parent


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
