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

It does ask the resolved runner what it is, once, in the daily-cap guard — a
free replay has no credit to protect. That is a different thing from reading
NEEV_MODE: the mode is still resolved in exactly one place, and this route would
keep working if a third runner appeared.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.analysis import analysis_for, latest_revision, revision_number
from app.api.deps import AuthorizedLoan
from app.core.settings import get_settings
from app.db import models
from app.mappers.boq import to_boq_review
from app.mappers.sanction import to_sanction_check
from app.schemas.views import BoqReviewView, SanctionCheckView
from app.services.jobs import registry
from app.services.runner import BoqAnalysisRequest, get_runner
from app.services.artifacts import read_upload, store_artifact
from app.api.routes.loans import _current_tranche

router = APIRouter(prefix="/api/loans", tags=["boq"])


class UploadAccepted(BaseModel):
    job_id: str
    loan_id: str


@router.post("/{loan_id}/boq", response_model=UploadAccepted)
async def upload_boq(
    loan: AuthorizedLoan,
    file: UploadFile = File(...),
    built_up_sqft: int | None = Form(default=None, gt=0),
) -> UploadAccepted:
    # Starlette fills `size` from the multipart part, so the bytes never need to
    # be pulled into memory here. They are not carried into the request object
    # either: fixture mode ignores them, and the live runner reads them back
    # from the stored artefact (see BoqAnalysisRequest).
    _refuse_if_over_the_daily_cap(loan)
    data, mime = await read_upload(file)
    tranche = _current_tranche(loan) if loan.tranches else None
    request = BoqAnalysisRequest(
        loan_id=loan.id,
        filename=file.filename or "boq.pdf",
        content_type=mime,
        size_bytes=len(data),
        artifact_path=store_artifact(data),
        locality=loan.locality,
        built_up_sqft=built_up_sqft or loan.built_up_sqft,
        sanctioned=loan.sanctioned,
        disbursed=loan.disbursed,
        tranche_number=tranche.number if tranche else None,
        claimed_stage=(tranche.claimed_stage or tranche.milestone) if tranche else "not_assessed",
        requested_amount=max(0, tranche.disbursed_cum - loan.disbursed) if tranche else 0,
        photo_paths=[p.stored_path for p in tranche.photos if p.stored_path] if tranche else [],
    )
    job = registry.create(request)
    return UploadAccepted(job_id=job.id, loan_id=loan.id)


def _refuse_if_over_the_daily_cap(loan: models.Loan) -> None:
    """Stop a public URL from spending credit without limit.

    A live analysis drives five agents against Gemini and costs real money. The
    deployed demo is `--allow-unauthenticated` and its sign-in accepts any
    ten-digit number, so without this the only thing between the billing
    account and a crawler is Google's own free-tier cap of twenty requests a
    day — which disappears the moment the key moves to the paid tier.

    Counts analyses STARTED, not revisions stored: a run that fails halfway has
    already paid for the agents that answered, and a revision only exists if the
    run succeeded. Two limits, because one loan hammering its own upload and a
    hundred loans doing it once each cost the same.

    A fixture replay is exempt, because there is nothing to protect: it reads a
    recorded run off disk and reaches no model. Capping it only throttles the
    free path — which is the path a demo recording uses, where running out of
    takes is the whole cost. The question is asked of the runner rather than of
    NEEV_MODE, so `get_runner` stays the one place that resolves the mode and
    this route keeps reading none (see the module docstring, and
    `jobs.py::_persist`, which reads `runner.mode` the same way).
    """
    if get_runner().mode != "live":
        return

    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)

    per_loan = settings.neev_max_analyses_per_loan_per_day
    if per_loan > 0 and registry.started_since(cutoff, loan.id) >= per_loan:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "This contract has been checked as many times as we allow in a day. "
                "Open the check you have already run, or try again tomorrow."
            ),
        )

    overall = settings.neev_max_analyses_per_day
    if overall > 0 and registry.started_since(cutoff) >= overall:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="We are checking as many contracts as we can today. Try again tomorrow.",
        )


@router.get("/{loan_id}/boq/latest", response_model=BoqReviewView)
def boq_latest(loan: AuthorizedLoan) -> BoqReviewView:
    return _review(loan, latest_revision(loan))


@router.get("/{loan_id}/boq/rev/{rev}", response_model=BoqReviewView)
def boq_revision(loan: AuthorizedLoan, rev: int) -> BoqReviewView:
    return _review(loan, revision_number(loan, rev))


@router.get("/{loan_id}/sanction-check", response_model=SanctionCheckView)
def sanction_check(loan: AuthorizedLoan) -> SanctionCheckView:
    revision = latest_revision(loan)
    output = analysis_for(revision)
    view = to_sanction_check(loan, revision, output.cost_estimate)
    view.provenance = output.provenance
    return view


def _review(loan: models.Loan, revision: models.BoqRevision) -> BoqReviewView:
    """The route sources the mapper's inputs, because the route is where the
    revision's provenance is already resolved (see app/api/analysis.py)."""
    output = analysis_for(revision)
    view = to_boq_review(loan, revision, output.cost_estimate, output.payment_schedule)
    view.analysis_mode = revision.pipeline_mode
    view.provenance = output.provenance
    return view
