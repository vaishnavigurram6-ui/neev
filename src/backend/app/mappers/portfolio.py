"""Portfolio Hotlist.

Row order is the design's exposure-descending order, preserved via
Loan.hotlist_rank rather than recomputed — the SQL orders by gap ascending and
would produce a different table (spec 4.5).

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
    ordered = sorted(loans, key=lambda loan: loan.hotlist_rank)

    hold = [loan for loan in ordered if loan.recommendation == "HOLD"]
    capital_at_risk = -sum(
        loan.cost_to_complete_gap
        for loan in hold
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
            sub="Paid ahead of verified progress",
            tone="danger",
        ),
        StatCardView(
            label="CAPITAL AT RISK",
            value=capital_at_risk,
            value_kind="money",
            sub=f"Disbursed beyond value in place, {len(hold)} loans",
            tone="danger",
        ),
        StatCardView(
            label="SITE VISITS SAVED",
            value="22 of 34",
            value_kind="text",
            sub="Fast-tracked where photos, BoQ and draws agree",
            tone="success",
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
            href=f"/bank/loans/{loan.id}/tranches/{_latest_tranche(loan)}",
        )
        for loan in ordered
    ]

    return PortfolioView(cards=cards, rows=rows)


def _action_label(recommendation: str | None) -> str:
    key = recommendation or "RELEASE"
    return ACTION_LABEL.get(key, key)


def _action_tone(recommendation: str | None) -> str:
    return ACTION_TONE.get(recommendation or "RELEASE", "warn")


def _latest_tranche(loan: models.Loan) -> int:
    paid_or_held = [t for t in loan.tranches if t.status in ("paid", "on_hold")]
    return max((t.number for t in paid_or_held), default=1)


def _compact(rupees: int) -> str:
    if rupees >= 1_00_00_000:
        return f"₹{rupees / 1_00_00_000:.2f} cr"
    return f"₹{rupees / 1_00_000:.2f} L"
