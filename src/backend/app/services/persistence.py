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

    db.commit()
    db.refresh(revision)
    return revision
