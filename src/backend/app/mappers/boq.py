"""BoQ Review's view model.

Stat-card copy is the mockup's, verbatim. Group order is the mockup's, held in
GROUP_ORDER rather than derived, because the design's order is editorial: the
missing-scope group sits third even though it has no priced line items.
"""

from app.db import models
from app.fixtures.loader import load_pipeline_output
from app.schemas.views import (
    BoqReviewView,
    FlagGroupView,
    FlagRowView,
    PaymentStageView,
    QuestionView,
    StatCardView,
)

GROUP_ORDER = [
    "FOUNDATION & RCC",
    "STEEL",
    "PLASTERING — EXPECTED BUT ABSENT",
    "FLOORING & ELECTRICAL",
    "OTHER",
]


def to_boq_review(loan: models.Loan, revision: models.BoqRevision) -> BoqReviewView:
    output = load_pipeline_output(loan.id)
    estimate = output.cost_estimate

    rate_outliers = sum(1 for f in revision.flags if f.type == "RATE_OUTLIER")
    missing = sum(1 for f in revision.flags if f.type == "MISSING_SCOPE")
    vague = sum(1 for f in revision.flags if f.type == "UNDERSPECIFIED")
    amount_before_slab = revision.boq_total * revision.payment_pct_before_slab

    cards = [
        StatCardView(
            label="QUOTED vs FAIR PRICE",
            value=revision.boq_total,
            value_kind="money",
            sub=(
                f"{loan.locality} rates price this scope at "
                f"{_money(estimate.fair_price_for_quoted_scope)}"
            ),
            tone="neutral",
        ),
        StatCardView(
            label="FLAGS RAISED",
            value=len(revision.flags),
            value_kind="count",
            sub=f"{rate_outliers} rate outliers · {missing} missing scope · {vague} vague specs",
            tone="danger" if revision.flags else "success",
        ),
        StatCardView(
            label="MISSING SCOPE",
            value=estimate.missing_scope_value or 0,
            value_kind="money",
            sub="External plaster and terrace waterproofing absent",
            tone="danger" if missing else "success",
        ),
        StatCardView(
            label="DUE BEFORE SLAB",
            value=revision.payment_pct_before_slab,
            value_kind="pct",
            sub=f"{_money(amount_before_slab)} before meaningful structure exists",
            tone="warn" if revision.payment_pct_before_slab > 0.30 else "success",
        ),
    ]

    flagged = _group(revision.flags)
    return BoqReviewView(
        loan_id=loan.id,
        borrower=loan.borrower_name,
        contractor=loan.contractor.name if loan.contractor else None,
        received_on=revision.received_on,
        item_count=revision.item_count,
        rev=revision.rev,
        cards=cards,
        groups=flagged,
        all_groups=flagged,  # "All" adds unflagged rows once a full BoQ is stored
        questions=[
            QuestionView(number=q.number, text=q.text, status=q.status)
            for q in sorted(loan.questions, key=lambda q: q.number)
        ],
        payment_schedule=[
            PaymentStageView(label=s.label, pct=s.pct, before_slab=s.before_slab)
            for s in output.payment_schedule
        ],
        pct_before_slab=revision.payment_pct_before_slab,
        amount_before_slab=amount_before_slab,
        gst_stated=not any(f.type == "GST_SILENT" for f in revision.flags),
    )


def _group(flags: list[models.Flag]) -> list[FlagGroupView]:
    buckets: dict[str, list[FlagRowView]] = {}
    for flag in flags:
        line = next(
            (li for li in flag.revision.line_items if li.item_id == flag.item), None
        )
        buckets.setdefault(flag.group_name or "OTHER", []).append(
            FlagRowView(
                item=flag.item,
                desc=line.desc if line else _missing_scope_desc(flag),
                qty=line.qty if line else None,
                unit=line.unit if line else None,
                rate=line.rate if line else None,
                amount=line.amount if line else None,
                expected_qty=flag.expected_qty,
                expected_unit=flag.expected_unit,
                expected_amount=flag.expected_amount,
                note=flag.evidence,
                label=flag.label,
                tone=flag.tone,  # type: ignore[arg-type]
            )
        )
    return [
        FlagGroupView(name=name, items=buckets[name])
        for name in GROUP_ORDER
        if name in buckets
    ]


def _missing_scope_desc(flag: models.Flag) -> str:
    # The question names the absent scope; take the leading clause as the label.
    return flag.question.split(" is absent")[0]


def _money(value: float | None) -> str:
    """Indian grouping, for prose inside a `sub` line only.

    The `value` fields stay numeric; this is used solely where a sentence quotes
    a figure to the reader, which the fixture-contract test explicitly allows.
    """
    if value is None:
        return "—"
    rupees = int(round(value))
    sign = "-" if rupees < 0 else ""
    digits = str(abs(rupees))
    if len(digits) > 3:
        digits = f"{_indian_group(digits[:-3])},{digits[-3:]}"
    return f"{sign}₹{digits}"


def _indian_group(head: str) -> str:
    """Group all but the last three digits in twos: '3200' -> '32,00'."""
    out = ""
    while len(head) > 2:
        out = "," + head[-2:] + out
        head = head[:-2]
    return head + out
