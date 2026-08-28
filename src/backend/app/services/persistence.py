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
from app.schemas.pipeline import PipelineOutput

# Which BoQ Review group each flagged item belongs under. Mirrors the seed's
# map; both derive from the mockup's editorial grouping.
FLAG_GROUPS = {
    "2.3": "FOUNDATION & RCC",
    "3.1": "FOUNDATION & RCC",
    "3.2": "FOUNDATION & RCC",
    "4.2": "STEEL",
    "7.1": "FLOORING & ELECTRICAL",
    "9.1": "FLOORING & ELECTRICAL",
    "9.2": "FLOORING & ELECTRICAL",
}
MISSING_SCOPE_GROUP = "PLASTERING — EXPECTED BUT ABSENT"


def store_revision(
    db: Session,
    loan_id: str,
    output: PipelineOutput,
    *,
    source_filename: str | None = None,
    mode: str = "fixture",
) -> models.BoqRevision:
    """Append a new revision for `loan_id` carrying `output`.

    Idempotent per call, not per output: each completed run is a new revision,
    which is what the Rev 1 / Rev 2 routes expect.
    """
    findings = output.boq_findings

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
                group_name=(
                    MISSING_SCOPE_GROUP
                    if flag.type == "MISSING_SCOPE"
                    else FLAG_GROUPS.get(flag.item, "OTHER")
                ),
                evidence=flag.evidence,
                question=flag.question,
                benchmark_rate=flag.benchmark_rate,
                deviation_pct=flag.deviation_pct,
                expected_qty=flag.expected_qty,
                expected_unit=flag.expected_unit,
                expected_amount=flag.expected_amount,
            )
        )

    db.commit()
    db.refresh(revision)
    return revision
