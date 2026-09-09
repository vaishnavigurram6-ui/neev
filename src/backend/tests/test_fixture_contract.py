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


def test_every_loan_on_the_book_has_a_recorded_run():
    """Ten loans, ten captures.

    It used to be two: 1001 and 1002 were the authored golden cases and the
    other eight carried derived figures, so eight of ten loan files told a
    lender "no BoQ has been analysed for this loan yet". The eight were
    recorded on 2026-09-10 from the synthetic bills of quantities in
    fixtures/synthetic/, each matched to its loan so the contract total sits
    within 0.95-1.35x of the sanction. Same pipeline that reads a real upload.
    """
    assert available_loan_ids() == [
        "1001", "1002", "1003", "1004", "1005",
        "1006", "1007", "1008", "1009", "1010",
    ]


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


def test_the_golden_loan_agrees_with_itself():
    """Captured runs are checked for consistency, not against frozen figures.

    This replaced a list of numbers transcribed from the mockups. Those were the
    right assertion while the fixture was authored to match the mockups; the
    fixture is now a recorded real run, so pinning its figures would break on
    every re-capture while proving nothing about correctness. What must hold is
    that the run agrees with itself and with the document it read.
    """
    out = load_pipeline_output("1001")
    findings = out.boq_findings

    # boq_total is the document's stated TOTAL, which is the sum of its lines.
    # The authored fixture said 3,200,000 where sample_boq.pdf prints 2,847,930
    # -- a contradiction only a real run exposed.
    assert findings.boq_total == pytest.approx(
        sum(li.amount for li in findings.line_items), rel=0.01
    )
    assert 0 < findings.payment_pct_before_slab <= 1

    risk = out.risk_assessment
    assert risk is not None
    # verified_value IS the expected cost scaled by how far the build has got.
    assert risk.verified_value == pytest.approx(
        out.cost_estimate.expected_total_cost * risk.pct_complete, rel=0.01
    )


def test_a_hold_is_only_ever_issued_against_an_exposure_over_one():
    """The recommendation and the arithmetic must not disagree on screen."""
    for loan_id in available_loan_ids():
        risk = load_pipeline_output(loan_id).risk_assessment
        if risk is None or risk.exposure_undefined:
            continue
        if risk.recommendation == "HOLD":
            assert risk.exposure_ratio > 1.0, loan_id
        if risk.recommendation == "RELEASE":
            assert risk.exposure_ratio <= 1.0, loan_id


def test_every_rate_outlier_can_say_how_far_off_the_rate_is():
    """A RATE_OUTLIER without deviation_pct is not a usable finding.

    The first captured run omitted it, so every pill degraded from "Rate +22%"
    to a bare "Rate outlier". The analyst prompt now demands it; this is what
    stops that regressing silently.
    """
    for loan_id in available_loan_ids():
        for flag in load_pipeline_output(loan_id).boq_findings.flags:
            if flag.type != "RATE_OUTLIER":
                continue
            assert flag.deviation_pct is not None, f"{loan_id} {flag.item}"
            assert flag.benchmark_rate is not None, f"{loan_id} {flag.item}"
            assert "%" in flag.label, f"{loan_id} {flag.item}: {flag.label!r}"


def test_a_flag_points_at_the_document_not_at_an_invented_code():
    """Flag ids are printed beside the contractor's own line numbering.

    A real run produced SCOPE_WATERPROOFING and GST_TERMS before the prompt
    pinned this down. Either a line number, or a lower-case scope name.
    """
    for loan_id in available_loan_ids():
        for flag in load_pipeline_output(loan_id).boq_findings.flags:
            assert flag.item == flag.item.lower(), f"{loan_id}: {flag.item!r}"
            assert "_" not in flag.item, f"{loan_id}: {flag.item!r}"


def test_the_flagged_loan_is_flagged_and_the_clean_one_is_clean():
    """The two golden loans exist to differ. 1002 having *no* flags at all was
    the old assertion; a real run legitimately reports UNBENCHMARKED for
    fittings nobody holds a rate for. What makes it the clean control is the
    absence of findings against the contractor -- no rate outliers, no missing
    scope.
    """
    flagged = load_pipeline_output("1001").boq_findings.flags
    clean = load_pipeline_output("1002").boq_findings.flags

    def counts(flags):
        out: dict[str, int] = {}
        for flag in flags:
            out[flag.type] = out.get(flag.type, 0) + 1
        return out

    assert counts(flagged).get("RATE_OUTLIER", 0) >= 1
    assert counts(flagged).get("MISSING_SCOPE", 0) >= 1
    assert counts(clean).get("RATE_OUTLIER", 0) == 0
    assert counts(clean).get("MISSING_SCOPE", 0) == 0


def test_every_flag_carries_a_label_a_screen_can_print():
    for loan_id in available_loan_ids():
        for flag in load_pipeline_output(loan_id).boq_findings.flags:
            assert flag.label.strip(), f"{loan_id} {flag.item}"
            assert flag.tone in ("danger", "warn", "success", "neutral")
