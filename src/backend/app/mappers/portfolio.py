"""Portfolio Hotlist.

Row order is exposure-descending, computed from the exposure each row shows.

It used to be preserved from `Loan.hotlist_rank`, which the seed assigns from
the order of portfolio_rows.json — the design's own order, authored against the
authored exposures. That held until the loans were re-analysed: recorded runs
replaced those exposures and left 1003 at the top of a table headed "ranked by
disbursement exposure" with 0.87 and ON TRACK, above 1004 at 1.71 and ESCALATE.
A ranking that contradicts its own column is worse than a ranking nobody chose.

Computing it also keeps it true after a live run. A borrower who reports a
milestone in production changes their own exposure, and the book should reorder;
a seed-time rank could not.

A loan with no exposure sorts last rather than first. `None` is not a bad
ratio — it means no photograph was assessed, so nothing was measured — and
`hotlist_rank` breaks ties so the order stays stable between requests.

Every row gets its own drill-in href. The prototype gives only loan 1001 a real
link and points the other nine at "#" (spec 7.4).
"""

from app.db import models
from app.schemas.views import PortfolioRowView, PortfolioView, StatCardView

# Every RiskAssessment.recommendation value has an entry, ESCALATE included.
# An unrecognised value shows itself and reads amber — never green, because a
# recommendation the table does not understand is not evidence of "on track".
ACTION_LABEL = {
    "HOLD": "HOLD",
    "INSPECT": "INSPECT",
    "ESCALATE": "ESCALATE",
    "RELEASE": "ON TRACK",
}
ACTION_TONE = {
    "HOLD": "danger",
    "INSPECT": "warn",
    "ESCALATE": "danger",
    "RELEASE": "success",
}


def to_portfolio(loans: list[models.Loan]) -> PortfolioView:
    ordered = sorted(
        loans,
        key=lambda loan: (
            loan.exposure_ratio is None,
            -(loan.exposure_ratio or 0.0),
            loan.hotlist_rank,
        ),
    )

    hold = [loan for loan in ordered if loan.recommendation in {"HOLD", "ESCALATE", "INSPECT"}]
    capital_at_risk = -sum(
        loan.cost_to_complete_gap
        for loan in ordered
        if loan.cost_to_complete_gap and loan.cost_to_complete_gap < 0
    )

    cards = [
        StatCardView(
            label="ACTIVE CONSTRUCTION LOANS",
            value=len(ordered),
            value_kind="count",
            sub=f"{_compact(sum(loan.sanctioned for loan in ordered))} sanctioned across the book",
            tone="neutral",
        ),
        StatCardView(
            label="NEEDS ACTION",
            value=len(hold),
            value_kind="count",
            sub="Hold, escalation or inspection required",
            tone="danger",
        ),
        StatCardView(
            label="COMPLETION FUNDING SHORTFALL",
            value=capital_at_risk,
            value_kind="money",
            sub="Sum of negative cost-to-complete gaps; not over-disbursement",
            tone="danger",
        ),
        StatCardView(
            label="SITE VISITS SAVED",
            value="Not measured",
            value_kind="text",
            sub="No visit-savings audit has been recorded",
            tone="neutral",
        ),
    ]

    rows = [
        PortfolioRowView(
            loan_id=loan.id,
            borrower=loan.borrower_name,
            locality=loan.locality,
            paid_up_to=loan.paid_up_to or "—",
            seen_on_site=loan.seen_on_site or "—",
            behind_schedule=loan.behind_schedule,
            disbursed=float(loan.disbursed),
            exposure=loan.exposure_ratio,
            gap=(
                float(loan.cost_to_complete_gap)
                if loan.cost_to_complete_gap is not None
                else None
            ),
            gap_note=None if loan.cost_to_complete_gap is not None else "closed",
            action_label=_action_label(loan.recommendation),
            tone=_action_tone(loan.recommendation),  # type: ignore[arg-type]
            # The borrower's file, not a bare decision card. An officer who
            # lands straight on a tranche has no borrower, no contractor, no
            # site photographs and no history in front of them -- and the
            # decision they are being asked for is about all of that. The
            # pending draw is one click on from there.
            href=f"/bank/loans/{loan.id}",
            tranche=_assessed_tranche(loan),
        )
        for loan in ordered
    ]

    return PortfolioView(cards=cards, rows=rows)


def _action_label(recommendation: str | None) -> str:
    key = recommendation or "RELEASE"
    return ACTION_LABEL.get(key, key)


def _action_tone(recommendation: str | None) -> str:
    return ACTION_TONE.get(recommendation or "RELEASE", "warn")


def _assessed_tranche(loan: models.Loan) -> int:
    """The draw whose assessment this row is quoting.

    The row's exposure, gap and action all come from one tranche, and it has to
    be the one the row points at or a lender opens a screen that contradicts the
    line they clicked. That was live for loan 1004: the recorded run wrote
    ESCALATE onto T3 while this returned T4 — drawn, unassessed, and so
    reporting INSPECT to somebody who had just read ESCALATE.

    So: the furthest drawn tranche that actually carries a recommendation, and
    the furthest drawn one otherwise. A loan with nothing drawn has nothing
    assessed and answers T1, which is where its story starts.
    """
    drawn = [t for t in loan.tranches if t.status in ("paid", "on_hold")]
    assessed = [t for t in drawn if t.recommendation]
    return max((t.number for t in (assessed or drawn)), default=1)


def _compact(rupees: int) -> str:
    if rupees >= 1_00_00_000:
        return f"₹{rupees / 1_00_00_000:.2f} cr"
    return f"₹{rupees / 1_00_000:.2f} L"
