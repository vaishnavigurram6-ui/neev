"""Variations to a signed contract, and the owner's reply to each.

Owner-side writes, and the only ones in the build besides the BoQ upload. The
authorization asymmetry is `get_authorized_loan`'s: a lender reads any loan's
change orders, but only the borrower whose session names this loan may reply on
it. A reply is the owner's word in a dispute, so it is never taken from a body
field that any caller could set.

Statuses are `pending` -> `accepted` | `declined` | `countered`. A countered
order stays open, because a counter is an offer and not a settlement.
"""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field, model_validator

from app.api.analysis import analysis_for, latest_revision
from app.api.deps import AuthorizedLoan, CurrentUser, DbSession
from app.db import models
from app.mappers.change_order import to_change_order, to_change_orders
from app.schemas.views import ChangeOrderView, ChangeOrdersView

router = APIRouter(prefix="/api/loans", tags=["change orders"])

ReplyAction = Literal["accept", "decline", "counter"]

STATUS_FOR = {"accept": "accepted", "decline": "declined", "counter": "countered"}


class ReplyRequest(BaseModel):
    action: ReplyAction
    # Only a counter carries a figure. Rupees, never paise: every other money
    # field in this API is a whole-rupee number and a change order the owner
    # countered at 35100.5 would render as a figure nobody typed.
    counter_amount: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _counter_needs_an_amount(self) -> "ReplyRequest":
        if self.action == "counter" and self.counter_amount is None:
            raise ValueError("A counter needs counter_amount — the rate you will agree to.")
        if self.action != "counter" and self.counter_amount is not None:
            raise ValueError("counter_amount belongs to a counter, not to an accept or a decline.")
        return self


class NewChangeOrder(BaseModel):
    """What the owner types when they log a change their contractor has asked for
    verbally. `neevs_read` is deliberately absent: the read is Neev's, and a
    caller that could write it could put words in the product's mouth."""

    title: str = Field(min_length=1, max_length=200)
    signed_desc: str = Field(min_length=1)
    signed_amount: int = Field(ge=0)
    proposed_desc: str = Field(min_length=1)
    proposed_amount: int = Field(ge=0)


def _signed_total(loan: models.Loan) -> float:
    """The contract the owner signed, from its own revision.

    Revision 1 rather than the latest: a later revision is a *renegotiated*
    contract, and pricing changes against it would silently forgive whatever
    the revision itself changed.
    """
    first = loan.revisions[0] if loan.revisions else latest_revision(loan)
    return float(analysis_for(first).boq_findings.boq_total)


def _order_or_404(loan: models.Loan, change_order_id: int) -> models.ChangeOrder:
    order = next((o for o in loan.change_orders if o.id == change_order_id), None)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan {loan.id} has no change order {change_order_id}.",
        )
    return order


@router.get("/{loan_id}/change-orders", response_model=ChangeOrdersView)
def change_orders(loan: AuthorizedLoan, _user: CurrentUser) -> ChangeOrdersView:
    """Every variation on this loan, with the running total underneath."""
    return to_change_orders(loan, _signed_total(loan))


@router.post("/{loan_id}/change-orders", response_model=ChangeOrderView, status_code=201)
def log_change_order(
    body: NewChangeOrder, loan: AuthorizedLoan, db: DbSession, _user: CurrentUser
) -> ChangeOrderView:
    """Log a change the contractor asked for off the record.

    Tone is `neutral` and the read says plainly that the owner logged it: a
    figure Neev never checked must not arrive wearing the same warn/danger
    colours as one it did.
    """
    order = models.ChangeOrder(
        loan_id=loan.id,
        title=body.title,
        signed_desc=body.signed_desc,
        signed_amount=body.signed_amount,
        proposed_desc=body.proposed_desc,
        proposed_amount=body.proposed_amount,
        neevs_read="Logged by you, not yet checked against local rates.",
        status="pending",
        tone="neutral",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return to_change_order(order)


@router.post("/{loan_id}/change-orders/{change_order_id}/reply", response_model=ChangeOrderView)
def reply(
    body: ReplyRequest,
    loan: AuthorizedLoan,
    db: DbSession,
    user: CurrentUser,
    change_order_id: int = Path(ge=1),
) -> ChangeOrderView:
    """Accept, decline or counter one change order.

    A lender may read this loan's variations but never answer them: the reply is
    the borrower's decision about their own contract.
    """
    if user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the borrower can answer a change order.",
        )
    order = _order_or_404(loan, change_order_id)
    if order.status in ("accepted", "declined"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Change order {order.id} was already {order.status}.",
        )

    order.status = STATUS_FOR[body.action]
    order.counter_amount = body.counter_amount
    order.owner_note = body.note
    order.replied_at = datetime.now(timezone.utc).replace(tzinfo=None)
    # An answered order is no longer a warning: it is a decision the owner made.
    order.tone = "success" if body.action == "accept" else "neutral" if body.action == "decline" else "warn"
    db.commit()
    db.refresh(order)
    return to_change_order(order)
