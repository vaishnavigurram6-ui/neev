"""The analysis stream.

The Analyzing screen's one hard requirement is that the stream always ends. A
job the server has never heard of — the usual cause is a page reloaded after a
restart — gets a terminal `done` rather than an open socket, because a spinner
that never stops is worse than a redirect that arrives early.
"""

from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionUser
from app.schemas.events import DoneEvent
from app.services.jobs import registry

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# How long the stream may stay silent before it writes a comment. A live run's
# last three agents fire after the final tool call — 93 seconds of silence on a
# measured run — and Cloud Run, browsers and any proxy in between are all
# entitled to close an idle connection. Fixture mode never goes quiet this long,
# which is why this was not needed until the pipeline ran for real.
HEARTBEAT_S = 15.0

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    # Nginx buffers proxied responses by default, which would hold every event
    # until the run finished and make the whole screen pointless.
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


class JobStatusResponse(BaseModel):
    job_id: str
    loan_id: str
    status: str
    error: str | None


@router.get("/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str, user: CurrentUser) -> JobStatusResponse:
    """Why a run failed, for a client that missed the stream's error event."""
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No job {job_id}."
        )
    _authorize(job.loan_id, user)
    return JobStatusResponse(
        job_id=job.id, loan_id=job.loan_id, status=job.status, error=job.error
    )


@router.get("/{job_id}/events")
async def job_events(job_id: str, user: CurrentUser) -> StreamingResponse:
    job = registry.get(job_id)
    if job is not None:
        _authorize(job.loan_id, user)
    # Where an unknown job sends the reader. Role-aware, so a lender whose tab
    # reloads after a restart is not dropped into the borrower onboarding flow.
    fallback_redirect = "/bank/portfolio" if user and user.role == "bank" else "/owner/onboarding"

    async def generate() -> AsyncIterator[str]:
        try:
            async for event in registry.stream(job_id, heartbeat_s=HEARTBEAT_S):
                if event is None:
                    # An SSE comment. EventSource ignores it, so no client
                    # knows or cares — it exists to put a byte on the wire.
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {event.model_dump_json()}\n\n"
        except KeyError:
            # Unknown job. Send the reader somewhere real and close.
            fallback = DoneEvent(redirect=fallback_redirect)
            yield f"data: {fallback.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


def _authorize(loan_id: str, user: SessionUser) -> None:
    if user.role == "owner" and user.loan_id != loan_id:
        raise HTTPException(403, "This job belongs to another loan.")
