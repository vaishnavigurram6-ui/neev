"""FixtureRunner emits the same sequence the live runner must emit."""

import pytest

from app.schemas.events import DoneEvent, FindingEvent, PhaseEvent, ProgressEvent
from app.services.fixture_runner import FixtureRunner
from app.services.runner import BoqAnalysisRequest

REQ = BoqAnalysisRequest(
    loan_id="1001", filename="sample_boq.pdf", content_type="application/pdf", size_bytes=1024
)


async def _collect(runner):
    return [event async for event in runner.run(REQ)]


@pytest.mark.asyncio
async def test_emits_five_phases_each_running_then_done():
    events = await _collect(FixtureRunner(step_delay_s=0))
    phases = [e for e in events if isinstance(e, PhaseEvent)]
    for index in range(5):
        statuses = [p.status for p in phases if p.index == index]
        assert "running" in statuses and "done" in statuses, index


@pytest.mark.asyncio
async def test_findings_and_progress_are_interleaved():
    events = await _collect(FixtureRunner(step_delay_s=0))
    assert any(isinstance(e, FindingEvent) for e in events)
    assert any(isinstance(e, ProgressEvent) for e in events)


@pytest.mark.asyncio
async def test_last_event_is_done_and_redirects_to_the_boq_review_route():
    events = await _collect(FixtureRunner(step_delay_s=0))
    assert isinstance(events[-1], DoneEvent)
    assert events[-1].redirect == "/owner/loans/1001/boq"


@pytest.mark.asyncio
async def test_progress_never_exceeds_100_and_ends_at_100():
    events = await _collect(FixtureRunner(step_delay_s=0))
    pcts = [e.pct for e in events if isinstance(e, ProgressEvent)]
    assert max(pcts) == 100
    assert pcts == sorted(pcts)
