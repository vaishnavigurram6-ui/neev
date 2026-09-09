"""Change orders, priced against the BoQ the owner signed.

The screen's whole argument is one comparison — what the contract says versus
what is now proposed — so the delta is computed here rather than on the screen:
one subtraction, one place, and the running total at the bottom of the page can
never disagree with the rows above it.

A countered order is counted at the counter, not at the proposal. Showing an
owner a total that includes a figure they have refused would be the one number
on the page they cannot act on.
"""

from app.db import models
from app.schemas.views import ChangeOrderView, ChangeOrdersView

OPEN_STATUSES = {"pending", "countered"}


def _effective(order: models.ChangeOrder) -> float:
    """What this order costs if it stands as it currently is."""
    if order.status == "declined":
        return float(order.signed_amount)
    if order.counter_amount is not None:
        return float(order.counter_amount)
    return float(order.proposed_amount)


def to_change_order(order: models.ChangeOrder) -> ChangeOrderView:
    return ChangeOrderView(
        id=order.id,
        title=order.title,
        signed_desc=order.signed_desc,
        signed_amount=float(order.signed_amount),
        proposed_desc=order.proposed_desc,
        proposed_amount=float(order.proposed_amount),
        delta=float(order.proposed_amount) - float(order.signed_amount),
        neevs_read=order.neevs_read,
        status=order.status,
        tone=order.tone,  # type: ignore[arg-type]
        counter_amount=None if order.counter_amount is None else float(order.counter_amount),
        owner_note=order.owner_note,
        replied_at=order.replied_at,
        open=order.status in OPEN_STATUSES,
    )


def to_change_orders(loan: models.Loan, signed_total: float) -> ChangeOrdersView:
    orders = sorted(loan.change_orders, key=lambda order: order.id)
    accepted = [o for o in orders if o.status == "accepted"]
    pending = [o for o in orders if o.status in OPEN_STATUSES]

    def delta(order: models.ChangeOrder) -> float:
        return _effective(order) - float(order.signed_amount)

    accepted_total = sum(delta(o) for o in accepted)
    pending_total = sum(delta(o) for o in pending)
    if_accepted = signed_total + accepted_total + pending_total

    return ChangeOrdersView(
        loan_id=loan.id,
        signed_total=signed_total,
        orders=[to_change_order(o) for o in orders],
        accepted_total=accepted_total,
        pending_total=pending_total,
        if_accepted_total=if_accepted,
        sanctioned=float(loan.sanctioned),
        over_sanction=if_accepted - float(loan.sanctioned),
    )
