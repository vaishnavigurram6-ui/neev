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

from app.schemas.events import DoneEvent
from app.services.jobs import registry

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

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
def job_status(job_id: str) -> JobStatusResponse:
    """Why a run failed, for a client that missed the stream's error event."""
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No job {job_id}."
        )
    return JobStatusResponse(
        job_id=job.id, loan_id=job.loan_id, status=job.status, error=job.error
    )


@router.get("/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    async def generate() -> AsyncIterator[str]:
        try:
            async for event in registry.stream(job_id):
                yield f"data: {event.model_dump_json()}\n\n"
        except KeyError:
            # Unknown job. Send the reader somewhere real and close.
            fallback = DoneEvent(redirect="/owner/onboarding")
            yield f"data: {fallback.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)
