"""BoQ Review's view model.

Stat-card copy is the mockup's, verbatim. Group order is the mockup's, held in
GROUP_ORDER rather than derived, because the design's order is editorial: the
missing-scope group sits third even though it has no priced line items.
"""

from app.db import models
from app.schemas.pipeline import CostEstimate, PaymentStage
from app.schemas.views import (
    BoqReviewView,
    FlagGroupView,
    FlagRowView,
    PaymentStageView,
    QuestionView,
    StatCardView,
)

# Reading order for the BoQ Review groups. Kept explicit rather than derived,
# because the order is editorial: what the contractor over-priced comes first,
# and what we simply could not check comes last so it never crowds a real
# finding. Names must match app/services/persistence.py::FLAG_GROUPS_BY_TYPE.
#
# Was the mockup's work-section order (FOUNDATION & RCC, STEEL, ...). Replaced
# 2026-09-07 when captured runs began arriving with 31 flags spread across item
# ids no hand-written section map could cover -- every one landed in "OTHER".
GROUP_ORDER = [
    "RATES ABOVE BENCHMARK",
    "QUANTITIES THAT DO NOT ADD UP",
    "SPECIFICATIONS TOO VAGUE TO PRICE",
    "EXPECTED BUT ABSENT",
    "PAYMENT TERMS",
    "NO BENCHMARK TO COMPARE AGAINST",
]


def to_boq_review(
    loan: models.Loan,
    revision: models.BoqRevision,
    estimate: CostEstimate,
    payment_schedule: list[PaymentStage],
) -> BoqReviewView:
    """Pure: every input is passed in, nothing is read from disk.

    The mapper deliberately does NOT load the fixture itself. Doing so would
    bypass the PipelineRunner seam (spec §5.1a) — in live mode it would serve
    the authored figures for whichever loan id it was handed, regardless of what
    the pipeline actually produced. Sourcing `estimate` and `payment_schedule`
    is the caller's job, because the caller is where mode is already resolved.
    """
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
        boq_total=float(revision.boq_total),
        payment_schedule=[
            PaymentStageView(label=s.label, pct=s.pct, before_slab=s.before_slab)
            for s in payment_schedule
        ],
        pct_before_slab=revision.payment_pct_before_slab,
        amount_before_slab=amount_before_slab,
        gst_stated=_gst_stated(estimate),
    )


def _gst_stated(estimate) -> bool:
    """Whether the quote priced GST at all.

    Derived from the cost estimate, not from a GST_SILENT flag: loan 1001's
    flag list is frozen at the mockup's nine and contains no GST flag, yet its
    Sanction Check adds an unpriced "GST provision" section. Reading the flag
    would make the two screens contradict each other on the flagship loan.
    """
    return not any(
        "GST" in section.name.upper() and section.quoted is None
        for section in estimate.sections
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
    # GROUP_ORDER is the mockup's editorial order, not an allow-list. Any group
    # it does not name -- a live run inventing a new BoQ section -- is appended
    # rather than dropped. Filtering here silently lost rows while the FLAGS
    # RAISED card went on counting every flag, so the table header and the card
    # disagreed with no way to tell from the screen which was wrong.
    known = [
        FlagGroupView(name=name, items=buckets[name]) for name in GROUP_ORDER if name in buckets
    ]
    unknown = [
        FlagGroupView(name=name, items=items)
        for name, items in buckets.items()
        if name not in GROUP_ORDER
    ]
    return known + unknown


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
