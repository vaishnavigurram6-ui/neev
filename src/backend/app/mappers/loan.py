"""The loan's own summary, and the owner's Build Progress screen.

Both are added by Task 12, whose route table named `LoanSummaryView` and
`BuildProgressView` without Task 10 ever defining them.

Owner-facing milestone names are the Build Progress mockup's, verbatim — the
database stores the pipeline's slugs (`brickwork_roof`), and the reader is shown
"Brickwork & roof". Never the other way round.
"""

from app.db import models
from app.schemas.views import (
    BuildProgressView,
    LoanSummaryView,
    ProgressTrancheView,
    StandingRowView,
)

# Neev 3 Build Progress.dc.html, the "Payments so far" ladder.
MILESTONE_NAME = {
    "foundation": "Foundation",
    "plinth": "Plinth",
    "slab": "Roof slab",
    "brickwork_roof": "Brickwork & roof",
    "finishing": "Finishing & handover",
}

STATUS_LABEL = {"paid": "Paid", "on_hold": "On hold", "upcoming": "Upcoming"}
STATUS_TONE = {"paid": "success", "on_hold": "danger", "upcoming": "neutral"}
STATUS_STATE = {"paid": "done", "on_hold": "current", "upcoming": "todo"}

# "What to do this week", from the mockup verbatim. Loan 1001's, like the
# Sanction Check's ways forward: the copy is written to a borrower who has just
# been shown nine flags, and generalising it would make it say nothing.
NEXT_STEPS = [
    "Send the 4 written questions from your contract review — they cover the "
    "over-priced RCC and the missing waterproofing.",
    "Pick one of the three re-scope options and agree it with your contractor.",
    "Add this month's photos so the next verification is instant.",
]


def to_loan_summary(loan: models.Loan) -> LoanSummaryView:
    latest = loan.revisions[-1] if loan.revisions else None
    settled = [t for t in loan.tranches if t.status in ("paid", "on_hold")]
    current = max(settled, key=lambda t: t.number, default=None)
    return LoanSummaryView(
        loan_id=loan.id,
        borrower=loan.borrower_name,
        locality=loan.locality,
        plot_label=loan.plot_label,
        built_up_sqft=loan.built_up_sqft,
        sanctioned=float(loan.sanctioned),
        disbursed=float(loan.disbursed),
        contractor=loan.contractor.name if loan.contractor else None,
        latest_rev=latest.rev if latest else None,
        recommendation=loan.recommendation,
        exposure=loan.exposure_ratio,
        gap=(
            float(loan.cost_to_complete_gap)
            if loan.cost_to_complete_gap is not None
            else None
        ),
        current_stage=current.observed_stage if current else None,
        tranche_count=len(loan.tranches),
    )


def to_build_progress(loan: models.Loan) -> BuildProgressView:
    tranches = sorted(loan.tranches, key=lambda t: t.number)

    ladder: list[ProgressTrancheView] = []
    previous_cum = 0
    for tranche in tranches:
        status = tranche.status if tranche.status in STATUS_LABEL else "upcoming"
        ladder.append(
            ProgressTrancheView(
                number=tranche.number,
                name=MILESTONE_NAME.get(tranche.milestone, tranche.milestone),
                sub=_sub(tranche),
                amount=float(tranche.disbursed_cum - previous_cum),
                status_label=STATUS_LABEL[status],
                tone=STATUS_TONE[status],  # type: ignore[arg-type]
                state=STATUS_STATE[status],  # type: ignore[arg-type]
            )
        )
        previous_cum = tranche.disbursed_cum

    # The tranche under review carries the risk figures; before any tranche has
    # been assessed there is nothing to stand on and the panel says so.
    assessed = next(
        (t for t in reversed(tranches) if t.verified_value is not None), None
    )
    latest_settled = max(
        (t for t in tranches if t.status in ("paid", "on_hold")),
        key=lambda t: t.number,
        default=None,
    )

    standing = [
        StandingRowView(label="Paid to your contractor", value=float(loan.disbursed)),
        StandingRowView(
            label="Work standing on site",
            value=float(assessed.verified_value) if assessed else 0.0,
            tone="danger" if _behind(loan, assessed) else "neutral",
        ),
        StandingRowView(
            label="Left in your sanction", value=float(loan.sanctioned - loan.disbursed)
        ),
        StandingRowView(
            label="Needed to finish",
            value=(
                float(assessed.cost_to_complete)
                if assessed is not None and assessed.cost_to_complete is not None
                else 0.0
            ),
            tone="danger" if _short(loan, assessed) else "neutral",
        ),
    ]

    return BuildProgressView(
        loan_id=loan.id,
        borrower=loan.borrower_name,
        locality=loan.locality,
        plot_label=loan.plot_label,
        sanctioned=float(loan.sanctioned),
        disbursed=float(loan.disbursed),
        current_stage=latest_settled.observed_stage if latest_settled else None,
        last_verified_on=latest_settled.inspection_date if latest_settled else None,
        paused=any(t.status == "on_hold" for t in tranches),
        tranches=ladder,
        standing=standing,
        steps=list(NEXT_STEPS),
        shortfall=(
            float(assessed.cost_to_complete_gap)
            if assessed and assessed.cost_to_complete_gap is not None
            else None
        ),
    )


def _sub(tranche: models.Tranche) -> str:
    """One plain sentence per row, in the owner's voice."""
    # Built by hand rather than with "%-d", which is not portable strftime.
    date_ = tranche.inspection_date
    when = f"{date_.day} {date_:%b %Y}" if date_ else None
    if tranche.status == "paid":
        return f"Verified & released {when}" if when else "Verified & released"
    if tranche.status == "on_hold":
        return "Paused pending re-scope — see your options"
    return "Upcoming"


def _behind(loan: models.Loan, assessed: models.Tranche | None) -> bool:
    return bool(assessed and assessed.verified_value is not None and assessed.verified_value < loan.disbursed)


def _short(loan: models.Loan, assessed: models.Tranche | None) -> bool:
    gap = assessed.cost_to_complete_gap if assessed else None
    return gap is not None and gap < 0
