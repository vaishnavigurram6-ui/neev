"""Spec 5.1a acceptance test.

Every fixture must validate against the same Pydantic schemas the live runner
will emit. If a future live response would fail that schema, this test fails
today. It is also what stops the fixtures from drifting into screen-shaped blobs.
"""

import json
from pathlib import Path

import pytest

from app.fixtures.loader import available_loan_ids, load_pipeline_output
from app.schemas.pipeline import PipelineOutput

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"

# Fields whose whole purpose is prose addressed to a human reader. A sentence
# may quote a figure; a data field may not. Everything not named here must carry
# money as a number, so formatINR() stays the single formatter.
PROSE_FIELDS = {
    "owner_view",
    "officer_view",
    "evidence",
    "question",
    "reasons",
    "evidence_notes",
}


@pytest.mark.parametrize("loan_id", ["1001", "1002"])
def test_every_fixture_validates_against_the_pipeline_schema(loan_id):
    output = load_pipeline_output(loan_id)
    assert isinstance(output, PipelineOutput)


def test_both_golden_loans_are_present():
    assert available_loan_ids() == ["1001", "1002"]


@pytest.mark.parametrize(
    "path", sorted(p for p in FIXTURE_DIR.glob("loan_*_pipeline.json"))
)
def test_no_fixture_contains_a_preformatted_money_string(path):
    # Money is stored as numbers and rendered through formatINR(). A rupee sign
    # or Indian-grouped digits in a fixture means a display string leaked into
    # the data layer, which is what makes fixture work throwaway.
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)

    offenders: list[str] = []

    def walk(node, trail):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{trail}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{trail}[{index}]")
        elif isinstance(node, str):
            # Prose fields legitimately quote figures to the reader. Strip any
            # list index so `reasons[0]` is recognised as the `reasons` field.
            field = trail.split(".")[-1].split("[")[0]
            if field in PROSE_FIELDS:
                return
            if "₹" in node:
                offenders.append(trail)

    walk(payload, path.stem)
    assert offenders == [], f"pre-formatted money in {path.name}: {offenders}"


def test_loan_1001_carries_the_frozen_mockup_figures():
    # Transcribed from the mockups (spec 4.4). If any of these change, a screen
    # and the fixture have drifted apart.
    out = load_pipeline_output("1001")
    assert out.boq_findings.boq_total == 3200000
    assert out.boq_findings.payment_pct_before_slab == 0.45
    assert len(out.boq_findings.flags) == 9
    assert out.cost_estimate.expected_total_cost == 3500000
    assert out.cost_estimate.fair_price_for_quoted_scope == 2915000
    assert out.cost_estimate.missing_scope_value == 154000
    assert out.risk_assessment is not None
    assert out.risk_assessment.exposure_ratio == 1.29
    assert out.risk_assessment.verified_value == 1390000
    assert out.risk_assessment.cost_to_complete == 1580000
    assert out.risk_assessment.cost_to_complete_gap == -580000
    assert out.risk_assessment.recommendation == "HOLD"


def test_flag_counts_match_the_boq_review_stat_card():
    # "9 items — 3 rate outliers, 2 missing scope, 4 vague specs"
    flags = load_pipeline_output("1001").boq_findings.flags
    by_type: dict[str, int] = {}
    for flag in flags:
        by_type[flag.type] = by_type.get(flag.type, 0) + 1
    assert by_type["RATE_OUTLIER"] == 3
    assert by_type["MISSING_SCOPE"] == 2
    assert by_type["UNDERSPECIFIED"] == 4


def test_clean_loan_1002_has_no_flags():
    assert load_pipeline_output("1002").boq_findings.flags == []
