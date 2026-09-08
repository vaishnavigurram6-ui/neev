"""The job registry's one hard requirement: every subscriber sees every event,
in order, ending with DoneEvent — however late it subscribes.

A subscriber that misses the terminal DoneEvent leaves the Analyzing screen
spinning forever, which is the failure these tests exist to prevent.
"""

import asyncio

import pytest

from app.schemas.events import DoneEvent, PhaseEvent, ProgressEvent
from app.services.jobs import Job, JobRegistry
from app.services.runner import BoqAnalysisRequest

REQ = BoqAnalysisRequest(
    loan_id="1001", filename="sample_boq.pdf", content_type="application/pdf", size_bytes=1024
)


@pytest.mark.asyncio
async def test_a_subscriber_that_joins_late_replays_then_follows():
    registry = JobRegistry()
    job = Job(id="j1", loan_id="1001")
    registry._jobs[job.id] = job

    job.publish(PhaseEvent(index=0, status="running", name="Reading the document"))
    job.publish(ProgressEvent(pct=12, detail="item 5 of 40"))

    async def finish():
        await asyncio.sleep(0)
        job.publish(PhaseEvent(index=0, status="done", name="Reading the document"))
        job.publish(DoneEvent(redirect="/owner/loans/1001/boq"))
        job.status = "done"

    task = asyncio.create_task(finish())
    events = [event async for event in registry.stream(job.id)]
    await task

    assert len(events) == 4
    assert isinstance(events[-1], DoneEvent)


@pytest.mark.asyncio
async def test_an_event_published_during_replay_is_not_dropped():
    # The regression: stream() used to snapshot the event list, yield (handing
    # control back to the producer), and only subscribe afterwards. Anything
    # published in that window — the DoneEvent included — was lost.
    registry = JobRegistry()
    job = Job(id="j2", loan_id="1001")
    registry._jobs[job.id] = job
    job.publish(PhaseEvent(index=0, status="running", name="Reading the document"))

    seen = []
    stream = registry.stream(job.id)
    seen.append(await anext(stream))  # consuming the replayed event yields control

    # Exactly the window the old implementation left open.
    job.publish(DoneEvent(redirect="/owner/loans/1001/boq"))
    job.status = "done"

    seen.append(await anext(stream))
    assert isinstance(seen[-1], DoneEvent)


@pytest.mark.asyncio
async def test_a_finished_job_streams_its_whole_history_and_stops():
    registry = JobRegistry()
    job = Job(id="j3", loan_id="1001")
    registry._jobs[job.id] = job
    job.publish(PhaseEvent(index=0, status="running", name="Reading the document"))
    job.publish(DoneEvent(redirect="/owner/loans/1001/boq"))
    job.status = "done"

    events = [event async for event in registry.stream(job.id)]
    assert len(events) == 2
    assert isinstance(events[-1], DoneEvent)


@pytest.mark.asyncio
async def test_two_subscribers_each_receive_the_full_sequence():
    registry = JobRegistry()
    job = Job(id="j4", loan_id="1001")
    registry._jobs[job.id] = job

    async def produce():
        for index in range(3):
            await asyncio.sleep(0)
            job.publish(PhaseEvent(index=index, status="done", name=f"phase {index}"))
        job.publish(DoneEvent(redirect="/owner/loans/1001/boq"))
        job.status = "done"

    async def consume():
        return [event async for event in registry.stream(job.id)]

    first, second, _ = await asyncio.gather(consume(), consume(), produce())
    assert len(first) == len(second) == 4
    assert isinstance(first[-1], DoneEvent)
    assert isinstance(second[-1], DoneEvent)


@pytest.mark.asyncio
async def test_streaming_an_unknown_job_raises_keyerror():
    with pytest.raises(KeyError):
        async for _ in JobRegistry().stream("nope"):
            pass


@pytest.mark.asyncio
async def test_create_drives_a_real_run_to_completion(monkeypatch, seeded_db):
    import app.services.jobs as jobs_module
    from app.services.fixture_runner import FixtureRunner

    monkeypatch.setattr(jobs_module, "get_runner", lambda *a, **k: FixtureRunner(step_delay_s=0))

    registry = JobRegistry()
    job = registry.create(REQ)
    events = [event async for event in registry.stream(job.id)]
    assert isinstance(events[-1], DoneEvent)
    assert job.status == "done"
    assert job.error is None


@pytest.mark.asyncio
async def test_a_failing_run_still_terminates_the_stream(monkeypatch):
    """A crash must not strand the client. The stream still ends in DoneEvent,
    and the reason is recorded on the job for a route to surface."""
    import app.services.jobs as jobs_module

    class Boom:
        async def run(self, req):
            raise RuntimeError("pipeline exploded")
            yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(jobs_module, "get_runner", lambda *a, **k: Boom())

    registry = JobRegistry()
    job = registry.create(REQ)
    events = [event async for event in registry.stream(job.id)]
    assert isinstance(events[-1], DoneEvent)
    assert job.status == "error"
    assert "RuntimeError" in (job.error or "")


def test_each_runner_declares_the_provenance_its_runs_are_filed_under():
    """pipeline_mode is the only provenance a stored revision carries.

    Hardcoding "fixture" was harmless while the live runner returned no output.
    Now that it returns a parsed PipelineOutput, a live run would be filed as a
    fixture one -- and nothing downstream could tell a real analysis from a
    replay. The runner carries it so that get_runner() stays the only place in
    the codebase that reads NEEV_MODE.
    """
    from app.services.fixture_runner import FixtureRunner
    from app.services.live_runner import AdkPipelineRunner

    assert FixtureRunner().mode == "fixture"
    assert AdkPipelineRunner().mode == "live"


def test_no_service_but_the_runner_factory_reads_the_mode():
    """The invariant CLAUDE.md calls load-bearing, enforced instead of trusted."""
    import pathlib

    services = pathlib.Path(__file__).resolve().parents[1] / "app" / "services"
    readers = sorted(
        path.name
        for path in services.glob("*.py")
        if "neev_mode" in path.read_text(encoding="utf-8")
    )
    assert readers == ["runner.py"]
