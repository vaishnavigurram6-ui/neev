"""The schemas are the seam. These tests pin two things the live pipeline will
depend on: that infinite exposure serialises as JSON-legal null, and that the
event union discriminates on `type`."""

import json

from pydantic import TypeAdapter

from app.schemas.events import PipelineEvent
from app.schemas.pipeline import BoqFindings, Flag, LineItem, RiskAssessment


def test_infinite_exposure_serialises_as_null_not_Infinity():
    # assess_tranche returns float('inf') when expected_total_cost is 0 — a
    # passing test at tests/test_offline.py exercises exactly this. Infinity is
    # not valid JSON, so the schema must carry it as null plus an explicit flag.
    risk = RiskAssessment(
        exposure_ratio=None,
        exposure_undefined=True,
        recommendation="ESCALATE",
        pct_complete=0.0,
        verified_value=0.0,
        cost_to_complete_gap=0.0,
        reasons=["No verified value in place."],
    )
    payload = json.loads(risk.model_dump_json())
    assert payload["exposure_ratio"] is None
    assert payload["exposure_undefined"] is True
    assert "Infinity" not in json.dumps(payload)


def test_boq_findings_round_trips():
    findings = BoqFindings(
        line_items=[
            LineItem(
                id="3.1",
                section="3. RCC WORK",
                desc="RCC M25 for columns incl. shuttering & curing",
                qty=12.0,
                unit="cum",
                rate=9800,
                amount=117600,
            )
        ],
        flags=[
            Flag(
                item="3.1",
                type="RATE_OUTLIER",
                evidence="Benchmark 8033/cum — about 21200 excess on this line.",
                question="RCC M25 is priced at 9800/cum against a 8033 local benchmark. What is the basis?",
                tone="danger",
                label="Rate +22%",
                benchmark_rate=8033,
                deviation_pct=22.0,
            )
        ],
        boq_total=3200000,
        payment_pct_before_slab=0.45,
    )
    assert BoqFindings.model_validate_json(findings.model_dump_json()) == findings


def test_event_union_discriminates_on_type():
    adapter = TypeAdapter(PipelineEvent)
    phase = adapter.validate_python(
        {"type": "phase", "index": 2, "status": "running", "name": "Looking for missing scope"}
    )
    assert phase.name == "Looking for missing scope"
    done = adapter.validate_python({"type": "done", "redirect": "/owner/loans/1001/boq"})
    assert done.redirect.endswith("/boq")
