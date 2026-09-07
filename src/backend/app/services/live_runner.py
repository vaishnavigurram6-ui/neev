"""The live ADK path. Written and type-checked; NEVER EXECUTED in this build.

It ships unexercised by design (spec §5.1 and the CLAUDE.md dry run): the owner
validates it in Cloud Shell once credits are approved. Two properties make that
safe to leave here:

  1. Every ADK import is inside the method body, so this module imports cleanly
     in the backend venv, which has no google-adk at all.
  2. Construction goes through get_runner(), which refuses without an explicit
     NEEV_ALLOW_BILLED_CALLS=1.

The event sequence mirrors FixtureRunner's exactly, because the Analyzing
screen's five phases are all sub-steps inside boq_analyst — they are NOT the five
agents, contrary to the handoff README. The tool-call -> phase map is spec §5.2.
"""

from typing import AsyncIterator

from app.core.settings import assert_billed_calls_permitted
from app.schemas.events import DoneEvent, PhaseEvent, PipelineEvent
from app.schemas.pipeline import PipelineOutput
from app.services.pipeline_parse import parse_state
from app.services.runner import BoqAnalysisRequest

# Which display phase each ADK tool call advances (spec §5.2).
TOOL_TO_PHASE: dict[str, int] = {
    "lookup_benchmark_rate": 1,
    "check_rate_deviation": 1,
    "check_missing_scope": 2,
    "check_steel_rcc_ratio": 3,
    "check_payment_schedule": 4,
}

PHASE_NAMES: list[str] = [
    "Reading the document",
    "Checking every rate against Kompally benchmarks",
    "Looking for missing scope",
    "Checking specifications and quantities",
    "Reviewing the payment schedule and terms",
]


class AdkPipelineRunner:
    """Drives the real five-agent SequentialAgent through an InMemoryRunner."""

    mode = "live"

    def __init__(self) -> None:
        # Set once run() completes; read by final_output(). One runner instance
        # serves one analysis, which is how JobRegistry uses it.
        self._last_state: dict | None = None
        self.last_parse_errors: dict[str, str] = {}

    async def run(self, req: BoqAnalysisRequest) -> AsyncIterator[PipelineEvent]:
        assert_billed_calls_permitted()

        # Imported here, not at module scope: the backend venv has no ADK, and
        # importing neev_pipeline constructs a Gemini client at module load.
        from google.adk.runners import InMemoryRunner  # noqa: PLC0415
        from google.genai import types  # noqa: PLC0415
        from neev_pipeline.agent import root_agent  # noqa: PLC0415

        runner = InMemoryRunner(agent=root_agent, app_name="neev")
        session = await runner.session_service.create_session(
            app_name="neev", user_id=f"loan-{req.loan_id}"
        )

        message = types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        f"Analyse the attached Bill of Quantities for loan {req.loan_id}. "
                        f"Location: {req.locality}. "
                        f"Built-up area: {req.built_up_sqft} sqft. "
                        f"Sanctioned amount: {req.sanctioned}."
                    )
                )
            ],
        )

        # Started and finished are tracked separately. Conflating them marks a
        # phase finished the moment it starts, which leaves the last phase
        # spinning forever and double-sends "done" for another.
        started: set[int] = {0}
        finished: set[int] = set()
        yield PhaseEvent(index=0, status="running", name=PHASE_NAMES[0])

        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=message
        ):
            for call in _tool_calls(event):
                phase = TOOL_TO_PHASE.get(call)
                if phase is None or phase in started:
                    continue
                # Reaching phase N means every earlier phase is finished — the
                # tools fire in pipeline order. Closing them all here also
                # covers a phase whose tool never fired (a clean BoQ skips
                # check_missing_scope, for instance).
                for index in range(phase):
                    if index not in finished:
                        finished.add(index)
                        yield PhaseEvent(index=index, status="done", name=PHASE_NAMES[index])
                started.add(phase)
                yield PhaseEvent(index=phase, status="running", name=PHASE_NAMES[phase])

        # Read the session back before yielding the terminal event: _drive()
        # calls final_output() as soon as run() is exhausted, so the state has
        # to be in hand by then.
        self._last_state = (
            await runner.session_service.get_session(
                app_name="neev", user_id=session.user_id, session_id=session.id
            )
        ).state

        # Settle every phase still open, the last one included.
        for index in range(len(PHASE_NAMES)):
            if index not in finished:
                finished.add(index)
                yield PhaseEvent(index=index, status="done", name=PHASE_NAMES[index])

        yield DoneEvent(redirect=f"/owner/loans/{req.loan_id}/boq")

    def final_output(self, req: BoqAnalysisRequest) -> PipelineOutput | None:
        """The run's five output_key values, parsed into a PipelineOutput.

        The values live in ADK session state as raw model TEXT, not dicts, so
        they go through app.services.pipeline_parse — the same layer
        scripts/record_golden_run.py uses, which is what keeps a live run and a
        recorded one from drifting apart.

        None when anything required failed to parse: better to store nothing
        than to store a guess. The failure is kept on `last_parse_errors` so the
        caller can log which output_key was at fault rather than a bare None.
        """
        state = self._last_state
        if state is None:
            self.last_parse_errors = {"session": "no run has completed"}
            return None

        result = parse_state(state)
        self.last_parse_errors = result.errors
        return result.output


def _tool_calls(event: object) -> list[str]:
    """Names of the function calls carried by one ADK event, if any."""
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) or []
    names = []
    for part in parts:
        call = getattr(part, "function_call", None)
        if call is not None and getattr(call, "name", None):
            names.append(call.name)
    return names
