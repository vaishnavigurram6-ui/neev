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

def _ways_forward() -> list[SanctionOptionView]:
    """The mockup's three routes, verbatim.

    Built fresh per call rather than shared as a module constant, so no
    response can mutate another's. `saves_label` is a copy field, like a pill's
    label — the figures inside it are the mockup's own words to the reader.

    KNOWN LIMITATION: this copy is loan 1001's. Task 17 (Sanction Check) must
    make the routes loan-specific before any other loan renders this screen.
    """
    return [
        SanctionOptionView(
            title="Negotiate the flagged rates",
            saves_label="≈ ₹1,60,000",
            desc="The four questions from your BoQ review already cover this — RCC rates and the steel grade.",
        ),
        SanctionOptionView(
            title="Phase the finishing scope",
            saves_label="≈ ₹2,40,000",
            desc="Defer the main gate, granite platform and exterior painting to a post-handover phase.",
        ),
        SanctionOptionView(
            title="Top-up before drawdown",
            saves_label="closes the rest",
            desc="A ₹3,00,000 top-up now costs far less than a stalled build at tranche four.",
        ),
    ]


def to_sanction_check(
    loan: models.Loan, revision: models.BoqRevision, estimate: CostEstimate
) -> SanctionCheckView:
    quote = float(revision.boq_total)
    realistic = float(estimate.expected_total_cost)
    sanctioned = float(loan.sanctioned)
    largest = max(quote, realistic, sanctioned)

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
            sub="Quote re-priced + missing scope added back (plaster, waterproofing, GST risk)",
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
            tone="success" if section.delta < 0 else "danger",
        )
        for section in estimate.sections
    ]

    return SanctionCheckView(
        loan_id=loan.id,
        bars=bars,
        shortfall=realistic - sanctioned,
        sections=sections,
        options=_ways_forward(),
    )
