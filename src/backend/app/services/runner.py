"""The seam the live pipeline plugs into (spec §5.1a).

Routes depend on the PipelineRunner protocol and never branch on mode. Adding
the live path later means adding one class and one factory branch — no route,
schema, or component changes.
"""

from typing import AsyncIterator, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.core.settings import Settings, assert_billed_calls_permitted, get_settings
from app.schemas.events import PipelineEvent
from app.schemas.pipeline import PipelineOutput


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
    built_up_sqft: int | None = Field(default=None, gt=0)
    sanctioned: int | None = None
    artifact_path: str | None = None
    disbursed: int = 0
    tranche_number: int | None = None
    claimed_stage: str = "not_assessed"
    requested_amount: int = 0
    photo_paths: list[str] = Field(default_factory=list)


@runtime_checkable
class PipelineRunner(Protocol):
    # How a run this runner produced should be filed. Lets the driver record
    # provenance without a second NEEV_MODE check -- see get_runner's note.
    mode: str

    # Declared `def`, not `async def`: both implementations are async
    # generators, whose type is a plain callable returning an AsyncIterator.
    # `async def run(...) -> AsyncIterator[...]` describes a coroutine that
    # returns an iterator instead, which neither runner satisfies.
    def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        """Yield progress events as the analysis proceeds, ending with DoneEvent."""
        ...

    def final_output(self, req: BoqAnalysisRequest) -> PipelineOutput | None:
        """A validated result, or None when the run cannot be persisted."""
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
