"""The seam the live pipeline plugs into (spec §5.1a).

Routes depend on the PipelineRunner protocol and never branch on mode. Adding
the live path later means adding one class and one factory branch — no route,
schema, or component changes.
"""

from typing import AsyncIterator, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.core.settings import Settings, assert_billed_calls_permitted, get_settings
from app.schemas.events import PipelineEvent
from app.schemas.pipeline import InspectionResult, PipelineOutput, RiskAssessment


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


class InspectionOutcome(BaseModel):
    """What reading a reported milestone produces: a stage and what it implies.

    Deliberately not a `PipelineOutput`. That type is the whole five-agent run,
    and `parse_state` treats three of its keys as required — an inspection has
    none of them and never will, so returning one would mean either lying about
    what ran or teaching the parser that a BoQ analysis is optional.
    """

    inspection_result: InspectionResult | None = None
    risk_assessment: RiskAssessment | None = None


class MilestoneInspectionRequest(BaseModel):
    """Everything the inspector and risk agents need for one reported milestone.

    Reporting progress is the product's second promise — "photos verify each
    payment" — and until now the photo path never asked the model anything: it
    stored the frames and hardcoded ESCALATE. This is what makes that promise
    true.

    It carries the two figures the risk tool cannot derive from photographs,
    `expected_total_cost` and `completed_value_estimate`. In a full pipeline run
    those come from `cost_estimation_agent` through session state; here they are
    read from the loan's stored analysis, because re-reading a BoQ nobody
    changed would cost three more agents and produce the same numbers.
    """

    loan_id: str
    tranche_number: int
    claimed_stage: str
    photo_paths: list[str] = Field(default_factory=list)
    locality: str = "Kompally, Hyderabad"
    sanctioned: int = 0
    disbursed: int = 0
    requested_amount: int = 0
    expected_total_cost: float = 0.0
    completed_value_estimate: float = 0.0


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

    # The milestone path. Also declared `def`, for the same reason as `run`.
    def inspect(self, req: MilestoneInspectionRequest) -> AsyncIterator[PipelineEvent]:
        """Yield progress as the photos are read, ending with DoneEvent."""
        ...

    def inspection_output(self, req: MilestoneInspectionRequest) -> InspectionOutcome | None:
        """The inspection and the risk assessment it produced, or None."""
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
