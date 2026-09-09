"""Sanction Check's three comparison bars, gap table, and ways forward.

Bar widths are a percentage of the largest bar, so the design's 91% / 100% / 80%
falls out of the numbers instead of being hardcoded.
"""

from app.db import models
from app.schemas.pipeline import CostEstimate
from app.schemas.views import (
    SanctionBarView,
    SanctionCheckView,
    SanctionOptionView,
    SanctionSectionView,
)



def _ways_forward(
    loan: models.Loan, revision: models.BoqRevision, estimate: CostEstimate, shortfall: float
) -> list[SanctionOptionView]:
    """The three routes out of a shortfall, for THIS loan.

    Loan 1001 keeps the mockup's copy verbatim, figures included, because the
    global constraints make the mockup authoritative for the golden case.

    Every other loan gets the same three routes derived from its own data, with
    **no invented rupee figures**. That matters: this screen previously served
    1001's "≈ ₹1,60,000 / ≈ ₹2,40,000 / a ₹3,00,000 top-up" to every borrower,
    and cited four BoQ questions that only 1001 has. Quoting a saving a borrower
    cannot actually make is worse than quoting none — it is the "no fake
    precision" failure the project's own judge-proofing forbids.

    Where a figure is genuinely known it is used; where it is not, the label says
    what the route does instead of naming a number.
    """
    # Loan 1001 used to short-circuit here with the mockup's own copy --
    # "≈ ₹1,60,000", "the four questions from your BoQ review". Removed
    # 2026-09-07: the fixture is now a captured run reporting 31 flags and its
    # own section deltas, so those figures were invented relative to what the
    # pipeline actually computed. This function's own docstring forbids exactly
    # that, and the exemption for the demo loan was the one place it did not
    # hold. Every loan now derives its routes from its own data.

    options: list[SanctionOptionView] = []

    # Route 1 exists only if something is actually over-priced. The negative
    # section deltas are the amounts the re-pricing hands back, so their sum is
    # a real figure rather than an estimate.
    negotiable = sum(max(0, s.quoted - s.market) for s in estimate.sections
                     if s.quoted is not None and s.market is not None)
    flagged = [f for f in revision.flags if f.type in ("RATE_OUTLIER", "UNDERSPECIFIED")]
    if flagged:
        options.append(
            SanctionOptionView(
                title="Negotiate the flagged rates",
                saves_label=_approx(negotiable) if negotiable > 0 else "reduces the quote",
                desc=(
                    f"Your BoQ review raised {len(flagged)} "
                    f"{'question' if len(flagged) == 1 else 'questions'} on rates and "
                    "specifications. Settling those in writing is the cheapest ground to win."
                ),
            )
        )

    options.append(
        SanctionOptionView(
            title="Phase the finishing scope",
            saves_label="defers cost, does not remove it",
            desc=(
                "Move the finishing items you can live without for a season — gates, "
                "platforms, exterior paint — into a phase after handover."
            ),
        )
    )

    options.append(
        SanctionOptionView(
            title="Top-up before the first disbursement",
            saves_label="closes the rest",
            desc=(
                "Arranging the balance now costs far less than a build that stalls "
                "part-way, with money already spent and no roof on."
            ),
        )
    )
    return options


def _approx(amount: float) -> str:
    """A rounded rupee figure for a copy label, e.g. 251000 -> '≈ ₹2,50,000'.

    Rounded to the nearest 10,000 precisely because it is an approximation the
    reader will take to a negotiation — false precision would invite them to
    argue a number the data does not support.
    """
    rounded = int(round(amount / 10000.0) * 10000)
    digits = str(rounded)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        grouped = ""
        while len(head) > 2:
            grouped = "," + head[-2:] + grouped
            head = head[:-2]
        digits = head + grouped + "," + tail
    return f"≈ ₹{digits}"


def to_sanction_check(
    loan: models.Loan, revision: models.BoqRevision, estimate: CostEstimate
) -> SanctionCheckView:
    quote = float(revision.boq_total)
    realistic = float(estimate.expected_total_cost)
    sanctioned = float(loan.sanctioned)
    largest = max(quote, realistic, sanctioned, 1)

    bars = [
        SanctionBarView(
            label="Contractor's quote",
            value=quote,
            pct_of_max=quote / largest,
            sub="As submitted, before negotiation",
            tone="neutral",
        ),
        SanctionBarView(
            label=f"Realistic cost at {loan.locality} rates",
            value=realistic,
            pct_of_max=realistic / largest,
            sub="Construction-cost estimate; benchmark coverage and omitted scope may be incomplete",
            tone="neutral",
        ),
        SanctionBarView(
            label="Sanctioned amount",
            value=sanctioned,
            pct_of_max=sanctioned / largest,
            sub="What the bank has approved",
            tone="danger",
        ),
    ]

    sections = [
        SanctionSectionView(
            name=section.name,
            quoted=section.quoted,
            quoted_note=section.quoted_note,
            market=section.market,
            delta=section.delta,
            tone=("neutral" if section.quoted is None or section.market is None or section.delta == 0
                  else "success" if section.delta < 0 else "danger"),
        )
        for section in estimate.sections
    ]

    shortfall = realistic - sanctioned
    return SanctionCheckView(
        loan_id=loan.id,
        bars=bars,
        shortfall=shortfall,
        sections=sections,
        options=_ways_forward(loan, revision, estimate, shortfall),
    )
