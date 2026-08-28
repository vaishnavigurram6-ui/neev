"""Contractor Scorecard.

The one screen whose subject is the builder rather than the borrower. Rows are
ordered worst tier first, because the screen exists to surface the risky
builders — an alphabetical list would bury them.

Rates and shares cross the API as fractions; the frontend's formatters turn
0.31 into "31%". Nothing here formats.
"""

from app.db import models
from app.schemas.views import ContractorRowView, ContractorScorecardView

TIER_ORDER = {"WATCH": 0, "REVIEW": 1, "RELIABLE": 2}
TIER_TONE = {"WATCH": "danger", "REVIEW": "warn", "RELIABLE": "success"}


def to_contractor_scorecard(contractors: list[models.Contractor]) -> ContractorScorecardView:
    ordered = sorted(
        contractors,
        # An unrecognised tier sorts to the end but ahead of nothing — it is
        # never treated as reliable.
        key=lambda c: (TIER_ORDER.get(c.tier, len(TIER_ORDER)), c.name),
    )
    return ContractorScorecardView(
        rows=[
            ContractorRowView(
                id=contractor.id,
                name=contractor.name,
                meta=_meta(contractor),
                sites=contractor.sites,
                flags_per_boq=contractor.flags_per_boq,
                underspecified_share=contractor.underspecified_share,
                overrun_pct=contractor.overrun_pct,
                sites_gone_quiet=contractor.sites_gone_quiet,
                tier=contractor.tier,
                # An unknown tier reads amber, never green: a tier the screen
                # does not understand is not evidence of a reliable builder.
                tone=TIER_TONE.get(contractor.tier, "warn"),  # type: ignore[arg-type]
            )
            for contractor in ordered
        ]
    )


def _meta(contractor: models.Contractor) -> str:
    """"4 loans · Kompally, Medchal" — the mockup's sub-line, from real rows.

    The prototype also carries "since 2024"; there is no onboarding date in the
    data model, so it is omitted rather than invented.
    """
    localities: list[str] = []
    for loan in contractor.loans:
        if loan.locality not in localities:
            localities.append(loan.locality)
    count = len(contractor.loans)
    noun = "loan" if count == 1 else "loans"
    if not localities:
        return f"{count} {noun}"
    return f"{count} {noun} · {', '.join(localities)}"
