"""In-process job registry and SSE fan-out.

One process, one registry — enough for a demo and for a single-node deployment.
Events are retained on the Job so a late subscriber (a page refresh mid-analysis)
replays what it missed instead of showing an empty screen.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

from app.schemas.events import DoneEvent, ErrorEvent, PipelineEvent
from app.services.runner import BoqAnalysisRequest, PipelineRunner, get_runner

logger = logging.getLogger(__name__)

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
    # When the analysis was STARTED, which is what spends money — a run that
    # 503s halfway has already paid for the agents that answered. The daily cap
    # counts these rather than stored revisions, since a revision only exists
    # if the run succeeded.
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def publish(self, event: PipelineEvent) -> None:
        self.events.append(event)
        self._updated.set()

    async def wait_for_update(self, timeout: float | None = None) -> bool:
        """Block until publish() appends. True if it did, False on timeout.

        Safe against a lost wakeup: clearing and re-checking happen with no
        await between them, so no publish can slip past unobserved.

        The timeout exists for the heartbeat. A live run is quiet for a long
        while — the last three agents all fire after the final tool call, which
        measured 93 seconds of silence on one real run — and a stream that
        writes nothing for that long is a stream an intermediate proxy is
        entitled to close.
        """
        self._updated.clear()
        if timeout is None:
            await self._updated.wait()
            return True
        try:
            await asyncio.wait_for(self._updated.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False


# Failures a reader can do something about, in their own words. Matched on class
# name rather than by importing the classes: `_ResourceExhaustedError` lives in
# `google.adk.models.google_llm` and importing it here would pull ADK into
# fixture mode, which is the one thing the runner seam exists to prevent.
_FAILURE_MESSAGES: dict[str, str] = {
    # ADK's 429. On the Gemini API the binding limit is input tokens per minute
    # per model, so it clears on its own — a minute, not a day.
    "_ResourceExhaustedError": (
        "Too many contracts were analysed in the last minute. "
        "Wait a minute and start the check again — nothing was lost."
    ),
    # The model itself under load. Retries are already exhausted by the time
    # this surfaces, so asking again shortly is the honest advice.
    "ServerError": (
        "The service that reads contracts is busy right now. "
        "Try again in a few minutes — your document is still here."
    ),
    "ClientError": (
        "The service that reads contracts refused this document. "
        "Check it opens as a PDF or a clear photo, then try again."
    ),
}

_GENERIC_FAILURE = "The check did not finish. Nothing was saved — please try again."


def _reader_facing(exc: Exception) -> str:
    """One sentence a borrower can act on, never the exception's own text."""
    for klass in type(exc).__mro__:
        message = _FAILURE_MESSAGES.get(klass.__name__)
        if message:
            return message
    return _GENERIC_FAILURE


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
                if isinstance(event, ErrorEvent):
                    raise RuntimeError("Pipeline reported an analysis failure.")
                if not isinstance(event, DoneEvent):
                    job.publish(event)
            self._persist(runner, req)
            job.publish(DoneEvent(redirect=f"/owner/loans/{job.loan_id}/boq"))
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - recorded on the job, never raised at the client
            # Exceptions can contain SQL parameters, document text or credentials,
            # so the client-visible message is written here rather than taken from
            # the exception. The class name is not fit for a reader either:
            # "Analysis could not be saved (_ResourceExhaustedError)" told a
            # borrower that a save had failed when what actually happened was a
            # per-minute rate limit during the analysis itself.
            job.error = _reader_facing(exc)
            # The reader gets a sentence; the log gets the cause. Both are
            # needed and they are not the same audience: a borrower cannot act
            # on "_ResourceExhaustedError", and an operator cannot debug "the
            # check did not finish". `exc_info` keeps the traceback out of the
            # message and in the log, where it belongs.
            logger.error(
                "analysis job %s failed for loan %s: %s",
                job.id,
                job.loan_id,
                type(exc).__name__,
                exc_info=exc,
            )
            redirect = f"/owner/loans/{job.loan_id}/boq"
            # Say the run failed, then still terminate the stream. Publishing
            # ErrorEvent first means a client that understands it can show the
            # failure; one that does not simply follows the redirect as before.
            job.publish(ErrorEvent(message=job.error, redirect=redirect))
            # Publish the terminal event BEFORE flipping status: a subscriber
            # that is caught up returns as soon as status stops being
            # "running", so a status set first would strand it with no
            # DoneEvent and leave the Analyzing screen spinning.
            job.publish(DoneEvent(redirect=redirect))
            job.status = "error"

    def started_since(self, cutoff: datetime, loan_id: str | None = None) -> int:
        """How many analyses were started after `cutoff`, optionally for one loan.

        In memory, so a restart forgets. That is the right trade for a demo
        guard rather than a billing control: the deployment this protects runs
        at --min-instances 1 and --max-instances 1, so one warm process holds
        the count for as long as the demo lasts, and a cold start resetting it
        is not the failure mode worth engineering against.
        """
        return sum(
            1
            for job in self._jobs.values()
            if job.created_at >= cutoff and (loan_id is None or job.loan_id == loan_id)
        )

    async def stream(
        self, job_id: str, heartbeat_s: float | None = None
    ) -> AsyncIterator[PipelineEvent | None]:
        """Replay everything already emitted, then follow live.

        The cursor walks the job's append-only event list, so replay and live
        follow are the same loop. A page that refreshes mid-analysis therefore
        cannot miss an event published while it was catching up — including the
        terminal DoneEvent, which is what would otherwise leave the Analyzing
        screen spinning forever.

        Yields None when `heartbeat_s` elapses with nothing new, so the caller
        can write something to the socket and keep the connection alive. None
        rather than a heartbeat event type: a heartbeat is transport, not part
        of the run, and putting it in the event union would send it to every
        client reducer to ignore.
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

            if not await job.wait_for_update(heartbeat_s):
                yield None


    def _persist(self, runner: PipelineRunner, req: BoqAnalysisRequest) -> None:
        """Validate and commit before the driver publishes terminal success."""
        from app.schemas.pipeline import PipelineOutput
        from app.db.session import SessionLocal
        from app.services.persistence import store_revision

        output = runner.final_output(req)
        if output is None:
            raise ValueError("Pipeline returned no valid final output.")
        data = output.model_dump()
        if runner.mode == "live" and not req.photo_paths:
            data["inspection_result"] = None
        output = PipelineOutput.model_validate(data)
        with SessionLocal() as db:
            store_revision(db, req.loan_id, output, source_filename=req.filename,
                           mode=runner.mode, request=req)


registry = JobRegistry()
