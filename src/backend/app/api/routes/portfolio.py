"""Portfolio Hotlist.

`filter` is a query param, not a body field or server state, so a credit officer
can send a colleague the exact view they were looking at.

The filter narrows rows only. The four cards describe the whole book — "10 active
construction loans" is a fact about the portfolio, not about the current tab —
and recomputing them per filter would make the header change meaning as the
reader clicked around.
"""

from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.db import models
from app.mappers.portfolio import to_portfolio
from app.schemas.views import PortfolioView

router = APIRouter(prefix="/api", tags=["portfolio"])

PortfolioFilter = Literal["all", "needs_action", "on_track"]

# "Needs action" is the union of the two recommendations that stop a release.
NEEDS_ACTION = {"HOLD", "INSPECT", "ESCALATE"}


@router.get("/portfolio", response_model=PortfolioView)
def portfolio(
    db: DbSession,
    # Named `filter` because that is the query string the URL-state rule fixes;
    # shadowing the builtin inside one function signature is the lesser evil.
    filter: PortfolioFilter = Query(  # noqa: A002
        default="all", description="Which rows to return."
    ),
) -> PortfolioView:
    loans = list(db.scalars(select(models.Loan)))
    view = to_portfolio(loans)
    if filter == "all":
        return view

    # Filter on the recommendation, never on the row's display label: the label
    # is copy ("ON TRACK" for a RELEASE) and would break when the wording did.
    needs_action = {
        loan.id for loan in loans if (loan.recommendation or "RELEASE") in NEEDS_ACTION
    }
    wanted = filter == "needs_action"
    view.rows = [row for row in view.rows if (row.loan_id in needs_action) is wanted]
    return view
