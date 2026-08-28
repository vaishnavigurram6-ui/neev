"""One tranche, and the decision an officer takes on it.

The decision write is the only place this build mutates a credit outcome, so it
carries the whole evidence trail with it: the designs promise the officer that
what they saw is what goes into the loan file, and a decision row holding only
"HOLD" would not honour that.
"""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import AuthorizedLoan, CurrentTranche, DbSession
from app.db import models
from app.mappers.tranche import to_tranche_decision
from app.schemas.views import TrancheDecisionView

router = APIRouter(prefix="/api/loans", tags=["tranches"])

DecisionAction = Literal["RELEASE", "HOLD", "ESCALATE"]


class DecisionRequest(BaseModel):
    action: DecisionAction
    note: str | None = Field(default=None, max_length=2000)
    decided_by: str = "credit officer"


class DecisionResponse(BaseModel):
    loan_id: str
    tranche: int
    action: DecisionAction
    decided_at: datetime


@router.get("/{loan_id}/tranches/{tranche_number}", response_model=TrancheDecisionView)
def tranche_decision(loan: AuthorizedLoan, tranche: CurrentTranche) -> TrancheDecisionView:
    return to_tranche_decision(loan, tranche)


@router.post("/{loan_id}/tranches/{tranche_number}/decision", response_model=DecisionResponse)
def decide(
    body: DecisionRequest,
    loan: AuthorizedLoan,
    tranche: CurrentTranche,
    db: DbSession,
) -> DecisionResponse:
    """Idempotent per tranche: a second POST updates the one row.

    A double-clicked "Hold" must leave one entry in the loan file, and an
    officer who changes their mind must leave one entry too — the latest one,
    with a fresh evidence snapshot, not an append-only argument with itself.
    """
    decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    snapshot = to_tranche_decision(loan, tranche).model_dump_json()

    decision = tranche.decision
    if decision is None:
        decision = models.Decision(tranche_id=tranche.id)
        db.add(decision)

    decision.action = body.action
    decision.note = body.note
    decision.decided_by = body.decided_by
    decision.decided_at = decided_at
    # The whole view the officer was looking at, as JSON. This is what makes the
    # trail auditable later: the figures are frozen at decision time, so a
    # re-run of the pipeline cannot retroactively change what was decided on.
    decision.evidence_snapshot = snapshot

    # Deliberately does NOT move `tranche.status`. Deciding to release is not
    # the same event as disbursing: flipping the status to "paid" while
    # `Loan.disbursed` stayed put would leave the portfolio's exposure figures
    # disagreeing with the tranche's own. Disbursement is a separate operation
    # this phase does not model.
    db.commit()

    return DecisionResponse(
        loan_id=loan.id, tranche=tranche.number, action=body.action, decided_at=decided_at
    )
