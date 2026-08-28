"""The loan itself, the four questions, and the owner's build progress.

None of these is screen-shaped: `GET /api/loans/{id}` is the loan, not a header;
`/progress` is the payment ladder and the standing figures, which the Build
Progress screen renders and the Update Progress screen reads for its stage list.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import AuthorizedLoan, DbSession
from app.db import models
from app.mappers.loan import to_build_progress, to_loan_summary
from app.schemas.views import BuildProgressView, LoanSummaryView

router = APIRouter(prefix="/api/loans", tags=["loans"])

# Photos a borrower uploads are stored by reference, not by blob: the demo keeps
# the bytes out of SQLite, and a real deployment swaps this for object storage.
UPLOAD_SLOT_PREFIX = "upload"


class QuestionsSentResponse(BaseModel):
    sent: int


class MilestoneResponse(BaseModel):
    tranche: int
    photos: int


@router.get("/{loan_id}", response_model=LoanSummaryView)
def loan_summary(loan: AuthorizedLoan) -> LoanSummaryView:
    return to_loan_summary(loan)


@router.post("/{loan_id}/questions/send", response_model=QuestionsSentResponse)
def send_questions(loan: AuthorizedLoan, db: DbSession) -> QuestionsSentResponse:
    """Marks the drafted questions sent.

    Idempotent: a second click does not re-stamp `sent_at` on a question already
    sent, and the count returned is how many questions are now with the
    contractor — the number the screen says it sent, both times.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for question in loan.questions:
        if question.status == "draft":
            question.status = "sent"
            question.sent_at = now
    db.commit()
    return QuestionsSentResponse(
        sent=sum(1 for q in loan.questions if q.status in ("sent", "replied"))
    )


@router.get("/{loan_id}/progress", response_model=BuildProgressView)
def build_progress(loan: AuthorizedLoan) -> BuildProgressView:
    return to_build_progress(loan)


@router.post("/{loan_id}/milestones", response_model=MilestoneResponse)
async def report_milestone(
    loan: AuthorizedLoan,
    db: DbSession,
    photos: list[UploadFile],
    stage: str | None = Form(default=None),
    note: str | None = Form(default=None),
) -> MilestoneResponse:
    """A borrower reporting progress: a stage, some photos, an optional note.

    The photos attach to the tranche currently under review, which is the one
    whose release they are evidence for.

    Every field this endpoint cannot actually establish is left null: the
    geotag, timestamp and same-angle flags, which the visual inspector fills in
    live mode, and `taken_at` — upload time is not capture time, and writing it
    into an evidence trail as though it were would be the one lie a verification
    record cannot afford.
    """
    uploaded = [photo for photo in photos if photo.filename]
    if not uploaded:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reporting a milestone needs at least one photo.",
        )

    tranche = _current_tranche(loan)
    for photo in uploaded:
        db.add(
            models.Photo(
                tranche_id=tranche.id,
                # A random suffix rather than a running count: `slot_key` has no
                # unique constraint, and a count-derived index repeats itself
                # after a photo row is deleted or when two reports interleave,
                # which hands any slot-keyed list duplicate keys.
                slot_key=f"{loan.id}-t{tranche.number}-{UPLOAD_SLOT_PREFIX}-{uuid4().hex[:8]}",
                caption=note or photo.filename,
                # No blob store in this phase. The row records that a photo
                # arrived and under which slot; the bytes are not kept.
                stored_path=None,
                taken_at=None,
            )
        )
    if stage:
        tranche.observed_stage = stage
    db.commit()
    return MilestoneResponse(tranche=tranche.number, photos=len(uploaded))


def _current_tranche(loan: models.Loan) -> models.Tranche:
    """The tranche a photo is evidence for.

    A tranche on hold is waiting on exactly this evidence, so it wins. Failing
    that it is the NEXT unpaid milestone, not the last one in the schedule — a
    borrower reporting foundation progress on a five-stage schedule must not
    have their photos filed against `finishing`. A fully paid loan falls back to
    its final tranche, and a loan with no draw schedule at all has nothing to
    attach evidence to and is a 404.
    """
    if not loan.tranches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan {loan.id} has no draw schedule yet.",
        )
    held = [t for t in loan.tranches if t.status == "on_hold"]
    if held:
        return min(held, key=lambda t: t.number)
    upcoming = [t for t in loan.tranches if t.status != "paid"]
    if upcoming:
        return min(upcoming, key=lambda t: t.number)
    return max(loan.tranches, key=lambda t: t.number)
