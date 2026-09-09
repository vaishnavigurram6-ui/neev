"""Stores a completed pipeline run as a BoqRevision.

Why this exists: FixtureRunner produced events and touched no database, so a
finished analysis left the loan at whatever revision the seed gave it — and the
eight loans with no seeded revision redirected to a BoQ page that 404'd. The
runner is what produces the output, so the runner's driver is what must store it.

The stored `raw_output` is the whole PipelineOutput, which is what
`app.api.analysis.pipeline_output_for` reads first. That keeps the seam intact:
a live run writes the same column and every screen serves live figures with no
change anywhere else.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.pipeline import (
    OBSERVABLE_STAGES,
    InspectionResult,
    PipelineOutput,
    RiskAssessment,
)
from app.services.runner import BoqAnalysisRequest

# Which BoQ Review group each flag belongs under.
#
# This was a hand-written map from item id to work section ("2.3" -> "FOUNDATION
# & RCC"), transcribed from the mockup's editorial grouping. That worked for the
# nine authored flags and broke on the first real run: 31 flags arrived with ids
# like 8.1, 10.4, 12.2 and every one fell into "OTHER".
#
# Grouping by finding type instead needs nothing the document has to supply, and
# it does something the section grouping could not -- it keeps "we could not
# check this rate" visually apart from "this rate looks wrong". Twelve
# UNBENCHMARKED fittings sitting among three real outliers made the outliers
# harder to see, not easier.
#
# (LineItem.section exists but a captured run leaves it null, because the
# analyst prompt asks for {id, desc, qty, unit, rate, amount} and nothing more.
# It is now requested, so a future capture could group by the document's own
# sections if that reads better.)
FLAG_GROUPS_BY_TYPE = {
    "RATE_OUTLIER": "RATES ABOVE BENCHMARK",
    "UNDERSPECIFIED": "SPECIFICATIONS TOO VAGUE TO PRICE",
    "MISSING_SCOPE": "EXPECTED BUT ABSENT",
    "STEEL_RATIO": "QUANTITIES THAT DO NOT ADD UP",
    "FRONT_LOADED": "PAYMENT TERMS",
    "GST_SILENT": "PAYMENT TERMS",
    # Deliberately last and plainly worded: these are not findings against the
    # contractor, they are gaps in our own benchmark table.
    "UNBENCHMARKED": "NO BENCHMARK TO COMPARE AGAINST",
}
UNGROUPED = "OTHER"


def apply_inspection(
    loan: models.Loan,
    tranche: models.Tranche,
    inspection: InspectionResult | None,
    risk: RiskAssessment | None,
) -> None:
    """Write what the photographs showed, and what it means for this draw.

    Shared by a full BoQ analysis and a reported milestone, which is the point:
    both paths run the same two agents over the same photographs, so a milestone
    must not be able to disagree with a full run about the observed stage or the
    exposure it implies.

    A missing inspection or risk assessment is not treated as a pass. No
    observation means human review and ESCALATE — the same conclusion a reader
    would reach from an empty evidence grid, and the opposite of what defaulting
    to RELEASE would say.
    """
    # "An inspection exists" is not the same as "a stage was seen". Loan 1005's
    # run returned an inspection whose stage was `not_assessed`, which parsed
    # cleanly and still measured nothing, so the gap came back as the price of
    # the whole house again.
    observed = inspection is not None and inspection.stage in OBSERVABLE_STAGES
    measured = risk is not None and observed

    tranche.needs_human_review = inspection.needs_human_review if inspection else True
    tranche.confidence = inspection.confidence if inspection else None
    tranche.observed_stage = inspection.stage if observed else None
    tranche.recommendation = risk.recommendation if risk else "ESCALATE"
    tranche.verified_value = int(risk.verified_value) if risk else None
    tranche.exposure_ratio = risk.exposure_ratio if risk else None
    tranche.exposure_undefined = risk.exposure_undefined if risk else True
    # Cost to complete is only a measurement when something was measured. The
    # risk tool derives it from the observed stage, so with no inspection it
    # assumes nothing is built and returns the price of the whole house: loan
    # 1007, fully drawn at Rs 25,00,000, came back needing Rs 35,95,327 more
    # than it had left. That is an artefact of the missing photographs, not a
    # shortfall, and a lender reading it as one would be reading a number
    # nobody measured. `enforce_evidence_gate` already distrusts a
    # recommendation made without an inspection; these two figures earn the
    # same treatment.
    tranche.cost_to_complete = (
        int(risk.cost_to_complete)
        if measured and risk.cost_to_complete is not None
        else None
    )
    tranche.cost_to_complete_gap = (
        int(risk.cost_to_complete_gap)
        if measured and risk.cost_to_complete_gap is not None
        else None
    )

    loan.exposure_ratio = tranche.exposure_ratio
    loan.exposure_undefined = tranche.exposure_undefined
    loan.cost_to_complete_gap = tranche.cost_to_complete_gap
    loan.recommendation = tranche.recommendation
    # None rather than the literal "not_assessed": this is display text on the
    # hotlist, and a lender reading "not_assessed" in a column headed "seen on
    # site" learns less than they do from an empty cell.
    loan.seen_on_site = tranche.observed_stage
    loan.behind_schedule = not inspection.matches_claim if inspection else True


def store_revision(
    db: Session,
    loan_id: str,
    output: PipelineOutput,
    *,
    source_filename: str | None = None,
    mode: str = "fixture",
    request: BoqAnalysisRequest | None = None,
) -> models.BoqRevision:
    """Append a new revision for `loan_id` carrying `output`.

    Idempotent per call, not per output: each completed run is a new revision,
    which is what the Rev 1 / Rev 2 routes expect.
    """
    findings = output.boq_findings
    loan = db.get(models.Loan, loan_id)
    if loan is None:
        raise ValueError("Analysis loan does not exist.")

    next_rev = (
        db.scalar(
            select(func.coalesce(func.max(models.BoqRevision.rev), 0)).where(
                models.BoqRevision.loan_id == loan_id
            )
        )
        or 0
    ) + 1

    revision = models.BoqRevision(
        loan_id=loan_id,
        rev=next_rev,
        received_on=date.today(),
        source_filename=source_filename,
        boq_total=int(findings.boq_total),
        payment_pct_before_slab=findings.payment_pct_before_slab,
        item_count=len(findings.line_items),
        pipeline_mode=mode,
        raw_output=output.model_dump_json(),
        source_artifact=request.artifact_path if request else None,
    )
    db.add(revision)
    db.flush()

    for item in findings.line_items:
        db.add(
            models.LineItem(
                revision_id=revision.id,
                item_id=item.id,
                section=item.section,
                desc=item.desc,
                qty=item.qty,
                unit=item.unit,
                rate=item.rate,
                amount=item.amount,
            )
        )

    for flag in findings.flags:
        db.add(
            models.Flag(
                revision_id=revision.id,
                item=flag.item,
                type=flag.type,
                label=flag.label,
                tone=flag.tone,
                group_name=FLAG_GROUPS_BY_TYPE.get(flag.type, UNGROUPED),
                evidence=flag.evidence,
                question=flag.question,
                benchmark_rate=flag.benchmark_rate,
                deviation_pct=flag.deviation_pct,
                expected_qty=flag.expected_qty,
                expected_unit=flag.expected_unit,
                expected_amount=flag.expected_amount,
            )
        )

    questions = list(dict.fromkeys(f.question for f in findings.flags if f.question.strip()))
    for number, text in enumerate(questions, 1):
        db.add(models.Question(loan_id=loan_id, revision_id=revision.id,
                              number=number, text=text, status="draft"))

    # A result updates only the tranche named by its request. Never infer which
    # draw was assessed from an unrelated latest revision or the highest number.
    tranche = next((t for t in loan.tranches
                    if request and t.number == request.tranche_number), None)
    if tranche is not None:
        tranche.assessment_revision_id = revision.id
        tranche.owner_view = output.explanation.owner_view
        tranche.officer_view = output.explanation.officer_view
        apply_inspection(loan, tranche, output.inspection_result, output.risk_assessment)

    db.commit()
    db.refresh(revision)
    return revision
