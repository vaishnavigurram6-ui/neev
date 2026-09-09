"""The loan itself, the four questions, and the owner's build progress.

None of these is screen-shaped: `GET /api/loans/{id}` is the loan, not a header;
`/progress` is the payment ladder and the standing figures, which the Build
Progress screen renders and the Update Progress screen reads for its stage list.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Path, Response, UploadFile, status
from pydantic import BaseModel

from app.api.deps import AuthorizedLoan, DbSession
from app.db import models
from app.api.analysis import analysis_for
from app.mappers.boq import visible_questions
from app.mappers.loan import to_build_progress, to_loan_summary
from app.schemas.views import BuildProgressView, LoanSummaryView
from app.services.artifacts import read_artifact, read_upload, store_artifact
from app.services.jobs import registry
from app.services.runner import MilestoneInspectionRequest
from typing import Literal

router = APIRouter(prefix="/api/loans", tags=["loans"])

# Photos a borrower uploads are stored by reference, not by blob: the row holds
# a path into ARTIFACT_DIR rather than the image, and a real deployment swaps
# that directory for object storage. `GET /{loan_id}/photos/{photo_id}` reads
# them back, which is what lets a lender see the evidence a borrower sent.
UPLOAD_SLOT_PREFIX = "upload"

# The formats read_upload accepts, keyed by their magic bytes. The stored file
# is the validated original, so its type is read from the bytes rather than
# from a content-type header the uploader chose or a column that could drift
# out of step with the file.
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


class QuestionsSentResponse(BaseModel):
    sent: int


class MilestoneResponse(BaseModel):
    tranche: int
    photos: int
    # The inspection reading the photographs. None when there was no stored
    # analysis to price the draw against, in which case the tranche is marked
    # for human review and says so rather than guessing.
    job_id: str | None = None


@router.get("/{loan_id}", response_model=LoanSummaryView)
def loan_summary(loan: AuthorizedLoan) -> LoanSummaryView:
    return to_loan_summary(loan)


def _sniff(data: bytes) -> str:
    """WebP is RIFF....WEBP — a prefix check cannot see past the length field."""
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    # read_upload rejected everything else, so this is a file written by an
    # older build. Served as a download rather than guessed at.
    return "application/octet-stream"


@router.get(
    "/{loan_id}/photos/{photo_id}",
    responses={200: {"content": {"image/jpeg": {}}, "description": "The photograph."}},
)
def loan_photo(
    loan: AuthorizedLoan, db: DbSession, photo_id: int = Path(ge=1)
) -> Response:
    """One photograph from this loan's evidence.

    Loan-scoped on purpose: `AuthorizedLoan` lets a lender read any loan in the
    book and an owner only their own, and the photo is looked up *within* the
    authorized loan rather than by id alone — otherwise any signed-in borrower
    could walk the id space and read another family's site photographs.

    Private and immutable: the bytes never change once written, but they are
    somebody's home under construction, so this is `private` rather than
    `public` and never lands in a shared cache.
    """
    photo = db.get(models.Photo, photo_id)
    tranche_ids = {tranche.id for tranche in loan.tranches}
    if photo is None or photo.tranche_id not in tranche_ids or not photo.stored_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan {loan.id} has no photograph {photo_id}.",
        )
    try:
        data = read_artifact(photo.stored_path)
    except (ValueError, OSError):
        # A row whose file is gone: the instance recycled, or the reference is
        # from another machine's ARTIFACT_DIR. Not a 500 — there is simply no
        # photograph to serve.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That photograph is no longer stored.",
        ) from None

    return Response(
        content=data,
        media_type=_sniff(data),
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/{loan_id}/questions/send", response_model=QuestionsSentResponse)
def send_questions(loan: AuthorizedLoan, db: DbSession) -> QuestionsSentResponse:
    """Marks the drafted questions sent.

    Idempotent: a second click does not re-stamp `sent_at` on a question already
    sent, and the count returned is how many questions are now with the
    contractor — the number the screen says it sent, both times.

    Only the questions the screen actually showed are stamped. The BoQ Review
    panel ranks and caps the list (see `mappers.boq.visible_questions`), and the
    WhatsApp message the owner sends carries exactly those — so stamping the
    whole stored list would record eighteen questions as "sent" that nobody
    ever sent.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    revision = max(loan.revisions, key=lambda r: r.rev, default=None)
    questions = visible_questions(revision) if revision else []
    for question in questions:
        if question.status == "draft":
            question.status = "sent"
            question.sent_at = now
    db.commit()
    return QuestionsSentResponse(
        sent=sum(1 for q in questions if q.status in ("sent", "replied"))
    )


@router.get("/{loan_id}/progress", response_model=BuildProgressView)
def build_progress(loan: AuthorizedLoan) -> BuildProgressView:
    return to_build_progress(loan)


@router.post("/{loan_id}/milestones", response_model=MilestoneResponse)
async def report_milestone(
    loan: AuthorizedLoan,
    db: DbSession,
    photos: list[UploadFile],
    stage: Literal["foundation", "plinth", "slab", "brickwork_roof", "finishing"] | None = Form(default=None),
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
    if not uploaded or len(uploaded) > 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reporting a milestone needs 1 to 6 photos.",
        )

    tranche = _current_tranche(loan)
    validated = [(photo, await read_upload(photo, image_only=True)) for photo in uploaded]
    for photo, (data, _mime) in validated:
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
                stored_path=store_artifact(data),
                taken_at=None,
            )
        )
    if stage:
        tranche.claimed_stage = stage
    # Marked for review immediately, and left that way until the inspection
    # comes back. The borrower has asked for money against these photographs;
    # the honest interim state is "a human should look", not a recommendation
    # nobody has made yet.
    tranche.needs_human_review = True
    tranche.recommendation = "ESCALATE"
    loan.recommendation = "ESCALATE"
    db.commit()

    job = _inspect_the_photos(loan, tranche, db)
    return MilestoneResponse(
        tranche=tranche.number, photos=len(uploaded), job_id=job.id if job else None
    )


def _inspect_the_photos(
    loan: models.Loan, tranche: models.Tranche, db: DbSession
):
    """Hand the reported milestone to the inspector and the risk agent.

    This is the product's second promise — "photos verify each payment" — and
    for a while the photo path kept none of it: it stored the frames, set
    ESCALATE by hand, and never asked the model anything. The same two agents a
    full BoQ analysis uses read them now.

    Two figures the photographs cannot supply come from the loan's stored
    analysis: the expected total cost and the completed value estimate. Without
    a stored analysis there is nothing to price the draw against, so the
    inspection is skipped and the tranche stays marked for human review — which
    is what it already says.
    """
    revision = max(loan.revisions, key=lambda r: r.rev, default=None)
    if revision is None:
        return None
    try:
        estimate = analysis_for(revision).cost_estimate
    except HTTPException:
        return None
    if estimate is None:
        return None

    return registry.create_inspection(
        MilestoneInspectionRequest(
            loan_id=loan.id,
            tranche_number=tranche.number,
            claimed_stage=tranche.claimed_stage or tranche.milestone,
            photo_paths=[p.stored_path for p in tranche.photos if p.stored_path],
            locality=loan.locality,
            sanctioned=loan.sanctioned,
            disbursed=loan.disbursed,
            requested_amount=max(0, tranche.disbursed_cum - loan.disbursed),
            expected_total_cost=estimate.expected_total_cost,
            completed_value_estimate=estimate.completed_value_estimate,
        )
    )


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
            detail=f"Loan {loan.id} has no disbursement schedule yet.",
        )
    held = [t for t in loan.tranches if t.status == "on_hold"]
    if held:
        return min(held, key=lambda t: t.number)
    upcoming = [t for t in loan.tranches if t.status != "paid"]
    if upcoming:
        return min(upcoming, key=lambda t: t.number)
    return max(loan.tranches, key=lambda t: t.number)
