"""In-process job registry and SSE fan-out.

One process, one registry — enough for a demo and for a single-node deployment.
Events are retained on the Job so a late subscriber (a page refresh mid-analysis)
replays what it missed instead of showing an empty screen.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

from app.schemas.events import DoneEvent, ErrorEvent, PipelineEvent
from app.services.runner import BoqAnalysisRequest, get_runner

# Cap on retained jobs. Each holds its full event list for replay, so an
# unbounded registry is a slow leak in a long-lived process. Oldest completed
# jobs are dropped first; a running job is never evicted.
MAX_RETAINED_JOBS = 50

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
        self._evict()
        return job

    def _evict(self) -> None:
        """Drop the oldest finished jobs once the registry exceeds its cap.

        Insertion order is creation order (dicts preserve it), so the first
        finished job found is the oldest. Running jobs are skipped: a subscriber
        may still be following one.
        """
        while len(self._jobs) > MAX_RETAINED_JOBS:
            evictable = next(
                (jid for jid, j in self._jobs.items() if j.status != "running"), None
            )
            if evictable is None:
                return  # everything is still running; nothing safe to drop
            self._jobs.pop(evictable, None)
            self._tasks.pop(evictable, None)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def _drive(self, job: Job, req: BoqAnalysisRequest) -> None:
        try:
            runner = get_runner()
            async for event in runner.run(req):
                job.publish(event)
            self._persist(runner, req)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - recorded on the job, never raised at the client
            job.error = str(exc)
            redirect = f"/owner/loans/{job.loan_id}/boq"
            # Say the run failed, then still terminate the stream. Publishing
            # ErrorEvent first means a client that understands it can show the
            # failure; one that does not simply follows the redirect as before.
            job.publish(ErrorEvent(message=str(exc), redirect=redirect))
            # Publish the terminal event BEFORE flipping status: a subscriber
            # that is caught up returns as soon as status stops being
            # "running", so a status set first would strand it with no
            # DoneEvent and leave the Analyzing screen spinning.
            job.publish(DoneEvent(redirect=redirect))
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


    def _persist(self, runner: object, req: BoqAnalysisRequest) -> None:
        """Store the finished run as a new BoqRevision.

        Without this a completed analysis left the loan at whatever revision the
        seed gave it, and the loans with no seeded revision redirected to a BoQ
        page that 404'd. A runner that cannot supply a final output returns None
        and nothing is stored.

        Imported inside the method so the services layer keeps no import-time
        dependency on the DB layer, and a failure to store never fails the run —
        the events have already been delivered.
        """
        output = getattr(runner, "final_output", lambda _req: None)(req)
        if output is None:
            return
        try:
            from app.db.session import SessionLocal
            from app.services.persistence import store_revision

            with SessionLocal() as db:
                store_revision(
                    db,
                    req.loan_id,
                    output,
                    source_filename=req.filename,
                    mode="fixture",
                )
        except Exception as exc:  # noqa: BLE001 - the run itself succeeded
            self._last_persist_error = str(exc)


registry = JobRegistry()
