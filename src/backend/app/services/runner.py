"""The seam the live pipeline plugs into (spec §5.1a).

Routes depend on the PipelineRunner protocol and never branch on mode. Adding
the live path later means adding one class and one factory branch — no route,
schema, or component changes.
"""

from typing import AsyncIterator, Protocol, runtime_checkable

from pydantic import BaseModel

from app.core.settings import Settings, assert_billed_calls_permitted, get_settings
from app.schemas.events import PipelineEvent


class BoqAnalysisRequest(BaseModel):
    """Everything a runner needs to analyse one uploaded BoQ.

    Deliberately carries no file bytes: fixture mode ignores the upload, and the
    live runner reads the bytes back from the stored artefact. That keeps this
    object small enough to log and to put in a job record.
    """

    loan_id: str
    filename: str
    content_type: str
    size_bytes: int
    locality: str = "Kompally, Hyderabad"
    built_up_sqft: int | None = None
    sanctioned: int | None = None


@runtime_checkable
class PipelineRunner(Protocol):
    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        """Yield progress events as the analysis proceeds, ending with DoneEvent."""
        ...


def get_runner(settings: Settings | None = None) -> PipelineRunner:
    """Resolve the runner for the current mode.

    THE ONLY place in the codebase that reads NEEV_MODE. If you find yourself
    checking the mode anywhere else — a route, a mapper, a component — that is a
    defect; depend on this protocol instead.
    """
    settings = settings or get_settings()

    if settings.neev_mode == "live":
        # Raises unless NEEV_ALLOW_BILLED_CALLS is set. Under the dry run it
        # always raises, which is the intended behaviour.
        assert_billed_calls_permitted(settings)
        from app.services.live_runner import AdkPipelineRunner

        return AdkPipelineRunner()

    from app.services.fixture_runner import FixtureRunner

    return FixtureRunner()
