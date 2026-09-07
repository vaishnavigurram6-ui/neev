"""Replays the authored pipeline run on a timer.

Makes zero network calls of any kind. The event sequence is identical to what
AdkPipelineRunner emits, so the Analyzing screen cannot tell the two apart —
which is the whole point of the seam (spec 5.1a).
"""

import asyncio
from typing import AsyncIterator

from app.fixtures.loader import load_analyzing_script, load_pipeline_output
from app.schemas.events import DoneEvent, FindingEvent, PhaseEvent, PipelineEvent, ProgressEvent
from app.schemas.pipeline import PipelineOutput
from app.services.runner import BoqAnalysisRequest


class FixtureRunner:
    mode = "fixture"

    def __init__(self, step_delay_s: float = 0.9) -> None:
        # Pacing only. Set to 0 in tests so the suite stays instant.
        self.step_delay_s = step_delay_s

    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        script = load_analyzing_script()
        phases = script["phases"]
        progress = script["progress"]
        findings = script["findings"]

        for index, phase in enumerate(phases):
            yield PhaseEvent(index=index, status="running", name=phase["name"], sub=phase["sub"])
            await self._pause()

            if index < len(progress):
                step = progress[index]
                yield ProgressEvent(pct=step["pct"], detail=step["detail"], eta_s=step["eta_s"])

            yield PhaseEvent(index=index, status="done", name=phase["name"], sub=phase["sub"])

            for finding in findings:
                if finding["after_phase"] == index:
                    yield FindingEvent(
                        flag=finding["flag"], tone=finding["tone"], text=finding["text"]
                    )
                    await self._pause()

        yield DoneEvent(redirect=f"/owner/loans/{req.loan_id}/boq")

    async def _pause(self) -> None:
        if self.step_delay_s:
            await asyncio.sleep(self.step_delay_s)

    def final_output(self, req: BoqAnalysisRequest) -> PipelineOutput | None:
        """The authored output for this loan, if one exists.

        Loans the fixture does not cover return None rather than another loan's
        figures — serving 1001's numbers under a different borrower's name is
        worse than an empty state.
        """
        try:
            return load_pipeline_output(req.loan_id)
        except KeyError:
            return None
