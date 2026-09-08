"""One tranche, and the decision an officer takes on it.

The decision write is the only place this build mutates a credit outcome, so it
carries the whole evidence trail with it: the designs promise the officer that
what they saw is what goes into the loan file, and a decision row holding only
"HOLD" would not honour that.
"""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select
from uuid import uuid4
from pydantic import BaseModel, Field

from app.api.deps import AuthorizedLoan, BankOfficer, BankReader, CurrentTranche, DbSession
from app.db import models
from app.mappers.tranche import to_tranche_decision
from app.schemas.views import TrancheDecisionView

router = APIRouter(prefix="/api/loans", tags=["tranches"])

DecisionAction = Literal["RELEASE", "HOLD", "ESCALATE"]


class DecisionRequest(BaseModel):
    action: DecisionAction
    note: str | None = Field(default=None, max_length=2000)
    # No `decided_by`: who decided is taken from the session, never from the
    # request body. An audit trail a caller can sign with any name it likes is
    # not an audit trail.


class DecisionResponse(BaseModel):
    loan_id: str
    tranche: int
    action: DecisionAction
    decided_at: datetime


@router.get("/{loan_id}/tranches/{tranche_number}", response_model=TrancheDecisionView)
def tranche_decision(
    loan: AuthorizedLoan, tranche: CurrentTranche, _reader: BankReader = None
) -> TrancheDecisionView:
    """The officer's view of one tranche. Bank-only: it carries the officer's
    narrative alongside the borrower's."""
    return to_tranche_decision(loan, tranche)


@router.post("/{loan_id}/tranches/{tranche_number}/decision", response_model=DecisionResponse)
def decide(
    body: DecisionRequest,
    loan: AuthorizedLoan,
    tranche: CurrentTranche,
    db: DbSession,
    officer: BankOfficer,
    idempotency_key: str | None = Header(default=None, max_length=100),
) -> DecisionResponse:
    """Append an audit event and update the latest-state projection atomically.

    Clients can deduplicate retries using Idempotency-Key. Reusing a key with a
    different payload is a conflict; an unkeyed submission is a new decision.
    """
    key = f"{loan.id}:{tranche.number}:{idempotency_key or uuid4().hex}"
    prior = db.scalar(select(models.DecisionEvent).where(models.DecisionEvent.idempotency_key == key))
    if prior:
        if (prior.action, prior.note, prior.decided_by) != (body.action, body.note, officer.name):
            raise HTTPException(409, "Idempotency key was already used for a different decision.")
        return DecisionResponse(loan_id=loan.id, tranche=tranche.number,
                                action=prior.action, decided_at=prior.decided_at)
    decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    snapshot = to_tranche_decision(loan, tranche).model_dump_json()

    decision = tranche.decision
    # Preserve the pre-migration decision before replacing its projection.
    if decision and not db.scalar(select(models.DecisionEvent.id).where(
        models.DecisionEvent.tranche_id == tranche.id
    ).limit(1)):
        db.add(models.DecisionEvent(tranche_id=tranche.id,
            idempotency_key=f"legacy:{tranche.id}", action=decision.action,
            note=decision.note, decided_by=decision.decided_by,
            decided_at=decision.decided_at, evidence_snapshot=decision.evidence_snapshot or "{}"))
    if decision is None:
        decision = models.Decision(tranche_id=tranche.id)
        db.add(decision)

    decision.action = body.action
    decision.note = body.note
    decision.decided_by = officer.name
    decision.decided_at = decided_at
    # The whole view the officer was looking at, as JSON. This is what makes the
    # trail auditable later: the figures are frozen at decision time, so a
    # re-run of the pipeline cannot retroactively change what was decided on.
    decision.evidence_snapshot = snapshot
    db.add(models.DecisionEvent(tranche_id=tranche.id, idempotency_key=key,
        action=body.action, note=body.note, decided_by=officer.name,
        decided_at=decided_at, evidence_snapshot=snapshot))

    # Deliberately does NOT move `tranche.status`. Deciding to release is not
    # the same event as disbursing: flipping the status to "paid" while
    # `Loan.disbursed` stayed put would leave the portfolio's exposure figures
    # disagreeing with the tranche's own. Disbursement is a separate operation
    # this phase does not model.
    db.commit()

    return DecisionResponse(
        loan_id=loan.id, tranche=tranche.number, action=body.action, decided_at=decided_at
    )
