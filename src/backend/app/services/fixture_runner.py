"""Replays an authored pipeline run. Fully implemented in Task 5."""

from typing import AsyncIterator

from app.schemas.events import DoneEvent, PipelineEvent
from app.services.runner import BoqAnalysisRequest


class FixtureRunner:
    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        yield DoneEvent(redirect=f"/owner/loans/{req.loan_id}/boq")
