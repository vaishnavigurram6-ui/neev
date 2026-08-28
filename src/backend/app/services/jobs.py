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
    _waiters: list[asyncio.Queue] = field(default_factory=list, repr=False)

    def publish(self, event: PipelineEvent) -> None:
        self.events.append(event)
        for queue in self._waiters:
            queue.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._waiters.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._waiters:
            self._waiters.remove(queue)


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
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as an SSE error
            job.status = "error"
            job.error = str(exc)
            job.publish(DoneEvent(redirect=f"/owner/loans/{job.loan_id}/boq"))

    async def stream(self, job_id: str) -> AsyncIterator[PipelineEvent]:
        """Replay everything already emitted, then follow live."""
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)

        for event in list(job.events):
            yield event
            if isinstance(event, DoneEvent):
                return

        if job.status != "running":
            return

        queue = job.subscribe()
        try:
            while True:
                event = await queue.get()
                yield event
                if isinstance(event, DoneEvent):
                    return
        finally:
            job.unsubscribe(queue)


registry = JobRegistry()
