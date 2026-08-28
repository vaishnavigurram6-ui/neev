"""Where a revision's pipeline output comes from.

`to_boq_review` and `to_sanction_check` are pure: they take a `CostEstimate` and
a payment schedule rather than loading anything, because a mapper that loaded
the authored fixture itself would bypass the PipelineRunner seam — in live mode
it would serve loan 1001's frozen figures for whatever loan id it was handed.
Sourcing those inputs is the caller's job. This module is that caller.

It does not branch on mode, and must not. It reads the revision's own persisted
output first; only a revision that has none falls back to the authored fixture
for that loan. A live run writes `BoqRevision.raw_output` when it stores the
revision, and this function then serves the live figures with no edit here.
"""

from fastapi import HTTPException, status

from app.db import models
from app.fixtures.loader import load_pipeline_output
from app.schemas.pipeline import PipelineOutput


def analysis_for(revision: models.BoqRevision) -> PipelineOutput:
    """The pipeline output behind one BoQ revision.

    Raises 404 when a revision exists but nothing ever analysed it — a real
    "nothing to show yet", not a blank screen dressed up as a result.
    """
    if revision.raw_output:
        return PipelineOutput.model_validate_json(revision.raw_output)
    try:
        return load_pipeline_output(revision.loan_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis stored for loan {revision.loan_id} revision {revision.rev}.",
        ) from exc


def latest_revision(loan: models.Loan) -> models.BoqRevision:
    """The newest revision, or a 404. Revisions are ordered by `rev` on the ORM."""
    if not loan.revisions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan {loan.id} has no BoQ yet.",
        )
    return loan.revisions[-1]


def revision_number(loan: models.Loan, rev: int) -> models.BoqRevision:
    revision = next((r for r in loan.revisions if r.rev == rev), None)
    if revision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan {loan.id} has no BoQ revision {rev}.",
        )
    return revision
