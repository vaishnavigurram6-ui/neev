"""Uploading a BoQ, reading a revision back, and the sanction comparison.

The upload does not analyse anything inline. It records the request and hands
back a job id; the analysis runs behind `PipelineRunner` and is watched over
SSE. That is what lets the same screen serve a 12-second fixture replay and a
two-minute live run without knowing which it is watching.

CLOSED (2026-08-28) — this used to note that nothing persisted the analysed
revision, so a finished run left `BoqRevision` untouched and the run's own
`DoneEvent` redirected to a page that answered 404. It is fixed where it
belonged: `PipelineRunner` gained `final_output()`, and `JobRegistry._persist`
writes the revision and its `raw_output` through `app/services/persistence.py`.
`app/api/analysis.py` reads `raw_output` first, so a live run substitutes with no
change here. This route still reads no mode, which is the property that made the
fix possible in the first place.
"""

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.api.analysis import analysis_for, latest_revision, revision_number
from app.api.deps import AuthorizedLoan
from app.db import models
from app.mappers.boq import to_boq_review
from app.mappers.sanction import to_sanction_check
from app.schemas.views import BoqReviewView, SanctionCheckView
from app.services.jobs import registry
from app.services.runner import BoqAnalysisRequest

router = APIRouter(prefix="/api/loans", tags=["boq"])


class UploadAccepted(BaseModel):
    job_id: str
    loan_id: str


@router.post("/{loan_id}/boq", response_model=UploadAccepted)
async def upload_boq(
    loan: AuthorizedLoan,
    file: UploadFile = File(...),
    built_up_sqft: int | None = Form(default=None),
) -> UploadAccepted:
    # Starlette fills `size` from the multipart part, so the bytes never need to
    # be pulled into memory here. They are not carried into the request object
    # either: fixture mode ignores them, and the live runner reads them back
    # from the stored artefact (see BoqAnalysisRequest).
    size = file.size if file.size is not None else len(await file.read())
    request = BoqAnalysisRequest(
        loan_id=loan.id,
        filename=file.filename or "boq.pdf",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        locality=loan.locality,
        built_up_sqft=built_up_sqft or loan.built_up_sqft,
        sanctioned=loan.sanctioned,
    )
    job = registry.create(request)
    return UploadAccepted(job_id=job.id, loan_id=loan.id)


@router.get("/{loan_id}/boq/latest", response_model=BoqReviewView)
def boq_latest(loan: AuthorizedLoan) -> BoqReviewView:
    return _review(loan, latest_revision(loan))


@router.get("/{loan_id}/boq/rev/{rev}", response_model=BoqReviewView)
def boq_revision(loan: AuthorizedLoan, rev: int) -> BoqReviewView:
    return _review(loan, revision_number(loan, rev))


@router.get("/{loan_id}/sanction-check", response_model=SanctionCheckView)
def sanction_check(loan: AuthorizedLoan) -> SanctionCheckView:
    revision = latest_revision(loan)
    return to_sanction_check(loan, revision, analysis_for(revision).cost_estimate)


def _review(loan: models.Loan, revision: models.BoqRevision) -> BoqReviewView:
    """The route sources the mapper's inputs, because the route is where the
    revision's provenance is already resolved (see app/api/analysis.py)."""
    output = analysis_for(revision)
    return to_boq_review(loan, revision, output.cost_estimate, output.payment_schedule)
