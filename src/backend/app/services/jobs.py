"""In-process job registry and SSE fan-out.

One process, one registry — enough for a demo and for a single-node deployment.
Events are retained on the Job so a late subscriber (a page refresh mid-analysis)
replays what it missed instead of showing an empty screen.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

from app.schemas.events import DoneEvent, PipelineEvent
from app.services.runner import BoqAnalysisRequest, get_runner

JobStatus = Literal["running", "done", "error"]


@dataclass
class Job:
    id: str
    loan_id: str
    status: JobStatus = "running"
    events: list[PipelineEvent] = field(default_factory=list)
    error: str | None = None
    # Wakes every subscriber. `events` is append-only and is the single source
    # of truth, so each subscriber tracks its own index into it — there are no
    # per-subscriber queues to keep in step, and nothing can be published into
    # the gap between a subscriber replaying history and starting to follow.
    _updated: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def publish(self, event: PipelineEvent) -> None:
        self.events.append(event)
        self._updated.set()

    async def wait_for_update(self) -> None:
        """Block until publish() appends, or return at once if it already has.

        Safe against a lost wakeup: clearing and re-checking happen with no
        await between them, so no publish can slip past unobserved.
        """
        self._updated.clear()
        await self._updated.wait()


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def create(self, req: BoqAnalysisRequest) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], loan_id=req.loan_id)
        self._jobs[job.id] = job
        self._tasks[job.id] = asyncio.create_task(self._drive(job, req))
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def _drive(self, job: Job, req: BoqAnalysisRequest) -> None:
        try:
            async for event in get_runner().run(req):
                job.publish(event)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - recorded on the job, never raised at the client
            job.error = str(exc)
            # Publish the terminal event BEFORE flipping status: a subscriber
            # that is caught up returns as soon as status stops being
            # "running", so a status set first would strand it with no
            # DoneEvent and leave the Analyzing screen spinning.
            #
            # KNOWN LIMITATION: PipelineEvent has no error variant, so the
            # client redirects as though the run succeeded. `job.error` holds
            # the reason; Task 12's GET /api/jobs/{id} should surface it, and
            # adding an ErrorEvent is a change to the shared event contract
            # that the frontend consumes, so it is not made here.
            job.publish(DoneEvent(redirect=f"/owner/loans/{job.loan_id}/boq"))
            job.status = "error"

    async def stream(self, job_id: str) -> AsyncIterator[PipelineEvent]:
        """Replay everything already emitted, then follow live.

        The cursor walks the job's append-only event list, so replay and live
        follow are the same loop. A page that refreshes mid-analysis therefore
        cannot miss an event published while it was catching up — including the
        terminal DoneEvent, which is what would otherwise leave the Analyzing
        screen spinning forever.
        """
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)

        cursor = 0
        while True:
            while cursor < len(job.events):
                event = job.events[cursor]
                cursor += 1
                yield event
                if isinstance(event, DoneEvent):
                    return

            # Caught up. A finished job has nothing more coming.
            if job.status != "running":
                return

            await job.wait_for_update()


registry = JobRegistry()
