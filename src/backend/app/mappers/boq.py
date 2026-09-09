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
]

# An UNBENCHMARKED flag is not a finding against the contractor — it says our
# benchmark table had nothing to compare that line against. A captured run
# raises one per unpriceable line, so on loan 1001 twelve of twenty-six "flags"
# were gaps in our own data, listed in the same table as three real rate
# outliers and counted in the same FLAGS RAISED figure. That reads as an alarm
# nobody can act on, so the rows are withheld and the count says how many.
#
# Withheld, not deleted: `unbenchmarked_count` is on the view model and the
# screen states it in one line. A report that quietly narrowed its own coverage
# would be claiming more than it checked.
WITHHELD_FLAG_TYPES = frozenset({"UNBENCHMARKED"})

# Which questions earn a place in "Send before you sign", most material first.
# A captured run writes one question per flag, and a list of twenty-six is a
# list nobody sends: the WhatsApp message is the deliverable, and it has to be
# short enough to be read on a phone by a contractor who did not ask for it.
QUESTION_PRIORITY = {
    "RATE_OUTLIER": 0,       # money already on the table
    "MISSING_SCOPE": 1,      # money not yet on the table
    "FRONT_LOADED": 2,       # when the money leaves
    "GST_SILENT": 2,
    "STEEL_RATIO": 3,
    "UNDERSPECIFIED": 4,     # what you get for the money
}
QUESTIONS_SHOWN = 8


def _visible(flags: list[models.Flag]) -> list[models.Flag]:
    return [f for f in flags if f.type not in WITHHELD_FLAG_TYPES]


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
    findings = _visible(revision.flags)
    unbenchmarked = len(revision.flags) - len(findings)
    rate_outliers = sum(1 for f in findings if f.type == "RATE_OUTLIER")
    missing = sum(1 for f in findings if f.type == "MISSING_SCOPE")
    vague = sum(1 for f in findings if f.type == "UNDERSPECIFIED")
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
            # Findings only. The card and the table below it count the same
            # rows, which is the property `_group` already exists to protect.
            value=len(findings),
            value_kind="count",
            sub=f"{rate_outliers} rate outliers · {missing} missing scope · {vague} vague specs",
            tone="danger" if findings else "success",
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

    flagged = _group(findings)
    questions, withheld = _questions(revision, findings)
    return BoqReviewView(
        loan_id=loan.id,
        borrower=loan.borrower_name,
        contractor=loan.contractor.name if loan.contractor else None,
        received_on=revision.received_on,
        item_count=revision.item_count,
        rev=revision.rev,
        cards=cards,
        groups=flagged,
        all_groups=_all_items(revision),
        questions=questions,
        questions_withheld=withheld,
        unbenchmarked_count=unbenchmarked,
        boq_total=float(revision.boq_total),
        payment_schedule=[
            PaymentStageView(label=s.label, pct=s.pct, before_slab=s.before_slab)
            for s in payment_schedule
        ],
        pct_before_slab=revision.payment_pct_before_slab,
        amount_before_slab=amount_before_slab,
        gst_stated=_gst_stated(estimate),
    )


def visible_questions(revision: models.BoqRevision) -> list[models.Question]:
    """The stored question rows the BoQ Review panel shows, in its order.

    Exported for `POST /questions/send`, which must stamp exactly the questions
    the owner was looking at — the same ranking and the same cap.
    """
    return _rank(revision, _visible(revision.flags))[0]


def _questions(
    revision: models.BoqRevision, findings: list[models.Flag]
) -> tuple[list[QuestionView], int]:
    """The panel's questions, renumbered 1..n, and how many were held back."""
    shown, withheld = _rank(revision, findings)
    return (
        [QuestionView(number=n, text=q.text, status=q.status) for n, q in enumerate(shown, 1)],
        withheld,
    )


def _rank(
    revision: models.BoqRevision, findings: list[models.Flag]
) -> tuple[list[models.Question], int]:
    """The questions worth sending, most material first, capped.

    Questions are stored as their own rows (they are editable and sendable), and
    a stored question carries no flag type — so the flag it came from is found
    by its text, which `persistence.py` copies verbatim from `Flag.question`.
    Matching that way means a question keeps its place in the order even after a
    re-run renumbers everything.

    A question whose only flag was withheld goes with it: asking the contractor
    to specify a line we could not price is a fair question, but it is not one
    of the eight that change the price.
    """
    priority_by_text: dict[str, int] = {}
    for flag in findings:
        text = (flag.question or "").strip()
        if not text:
            continue
        rank = QUESTION_PRIORITY.get(flag.type, len(QUESTION_PRIORITY))
        priority_by_text[text] = min(priority_by_text.get(text, rank), rank)

    stored = sorted(revision.questions, key=lambda q: q.number)
    # A revision with flags but no matching question text (a hand-authored seed,
    # or a re-worded question) keeps its list rather than showing an empty
    # panel: no match at all means there is nothing to rank by.
    keep = [q for q in stored if q.text.strip() in priority_by_text]
    if not keep:
        keep = stored

    ordered = sorted(
        keep,
        key=lambda q: (priority_by_text.get(q.text.strip(), len(QUESTION_PRIORITY)), q.number),
    )
    return ordered[:QUESTIONS_SHOWN], len(ordered) - QUESTIONS_SHOWN if len(ordered) > QUESTIONS_SHOWN else 0


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


def _all_items(revision: models.BoqRevision) -> list[FlagGroupView]:
    """One row per actual document item, with only the red flags marked.

    This is the whole document, read the way an owner reads their own contract:
    forty lines, and the ones that are actually wrong standing out. Only a
    `danger` flag earns a label here — a rate above benchmark, scope that is
    absent. A "Vague spec", a "No benchmark" and the old "Not assessed"
    fallback all put a pill on nearly every row, which left nothing standing
    out and read as if the whole contract were suspect.

    The quieter findings are not lost: they are in the flagged table, which is
    the view that exists to list them.
    """
    buckets: dict[str, list[FlagRowView]] = {}
    for item in revision.line_items:
        red = [f for f in revision.flags if f.item == item.item_id and f.tone == "danger"]
        buckets.setdefault(item.section or "DOCUMENT ITEMS", []).append(FlagRowView(
            item=item.item_id, desc=item.desc, qty=item.qty, unit=item.unit,
            rate=item.rate, amount=item.amount,
            label=" · ".join(dict.fromkeys(f.label for f in red)),
            tone="danger" if red else "neutral",
            # No claim either way on a quiet row: this view is the document, not
            # a verification report.
            note="\n".join(f.evidence for f in red),
        ))
    return [FlagGroupView(name=name, items=items) for name, items in buckets.items()]


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
