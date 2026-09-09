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

import json
from typing import AsyncIterator

from app.core.settings import assert_billed_calls_permitted
from app.schemas.events import DoneEvent, PhaseEvent, PipelineEvent
from app.schemas.pipeline import PipelineOutput
from app.services.pipeline_parse import parse_output_key, parse_state
from app.services.runner import (
    BoqAnalysisRequest,
    InspectionOutcome,
    MilestoneInspectionRequest,
)

# Which display phase each ADK tool call advances (spec §5.2).
TOOL_TO_PHASE: dict[str, int] = {
    "lookup_benchmark_rates": 1,
    "check_rate_deviations": 1,
    "lookup_benchmark_rate": 1,
    "check_rate_deviation": 1,
    "check_missing_scope": 2,
    "check_steel_rcc_ratio": 3,
    "check_payment_schedule": 4,
}

# The milestone path's two phases. Named for what a borrower waiting on a
# payment cares about, not for the agents doing it.
INSPECTION_PHASE_NAMES: list[str] = [
    "Reading your site photos",
    "Re-checking this payment against the work in place",
]

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
        from app.services.artifacts import read_artifact
        if not req.artifact_path:
            raise ValueError("Live analysis requires a stored BoQ artifact.")
        document = read_artifact(req.artifact_path)

        # Imported here, not at module scope: the fixture backend has no ADK.
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
                        f"Sanctioned amount: {req.sanctioned}. "
                        f"Disbursed cumulative: {req.disbursed}. "
                        f"Requested amount: {req.requested_amount}. "
                        f"Claimed stage: {req.claimed_stage}. "
                        f"Site photo paths for verify_construction_stage: {json.dumps(req.photo_paths)}. "
                        "No site photos means inspection is not_assessed and human review is required."
                    )
                ),
                types.Part.from_bytes(data=document, mime_type=req.content_type),
            ],
        )
        # Site evidence paths are server-generated references, never user paths.
        from io import BytesIO
        from PIL import Image
        for reference in req.photo_paths:
            data = read_artifact(reference)
            with Image.open(BytesIO(data)) as image:
                mime = Image.MIME[image.format]
            message.parts.append(types.Part.from_bytes(data=data, mime_type=mime))

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

    async def inspect(self, req: MilestoneInspectionRequest) -> AsyncIterator[PipelineEvent]:
        """Drive the inspector and the risk agent over one reported milestone.

        Two agents, not five. The BoQ has not changed since it was analysed, so
        re-reading it would spend three more agents to reproduce numbers already
        stored — `expected_total_cost` and `completed_value_estimate` come in on
        the request instead.

        A fresh SequentialAgent over the two existing agent objects rather than
        new ones: the instructions, the tools and the output_keys are the same
        ones the full pipeline uses, so a milestone and a full run cannot drift
        apart in what they mean by "observed stage".
        """
        assert_billed_calls_permitted()
        from app.services.artifacts import read_artifact

        from google.adk.agents import SequentialAgent  # noqa: PLC0415
        from google.adk.runners import InMemoryRunner  # noqa: PLC0415
        from google.genai import types  # noqa: PLC0415
        from neev_pipeline.agent import (  # noqa: PLC0415
            disbursal_risk_agent,
            visual_inspector_agent,
        )

        # `.clone()`, not the agent objects themselves: ADK gives an agent one
        # parent, and both of these already belong to the five-agent
        # `neev_pipeline` built at module import. Passing them here raises
        # "already has a parent agent". A clone carries the same instruction,
        # tools and output_key, so this still cannot drift from what a full run
        # means by "observed stage" — which redefining them here would.
        pipeline = SequentialAgent(
            name="neev_milestone_inspection",
            sub_agents=[visual_inspector_agent.clone(), disbursal_risk_agent.clone()],
        )
        runner = InMemoryRunner(agent=pipeline, app_name="neev")
        # `disbursal_risk_agent`'s instruction interpolates {cost_estimate},
        # which in a full run is whatever `cost_estimation_agent` left in
        # session state. Standalone there is no such key and ADK raises
        # "Context variable not found" before the model is ever called — so the
        # two figures the request carries are seeded in the same shape and the
        # same place a full run would leave them. Written as JSON text because
        # that is what an output_key holds: raw model output, not a dict.
        session = await runner.session_service.create_session(
            app_name="neev",
            user_id=f"loan-{req.loan_id}",
            state={
                "cost_estimate": json.dumps(
                    {
                        "expected_total_cost": req.expected_total_cost,
                        "completed_value_estimate": req.completed_value_estimate,
                    }
                )
            },
        )

        parts = [
            types.Part(
                text=(
                    f"The borrower on loan {req.loan_id} has reported milestone "
                    f"'{req.claimed_stage}' and submitted the attached site photos. "
                    f"Location: {req.locality}. "
                    f"Site photo paths for verify_construction_stage: "
                    f"{json.dumps(req.photo_paths)}. "
                    f"Sanctioned amount: {req.sanctioned}. "
                    f"Disbursed cumulative: {req.disbursed}. "
                    f"Requested amount: {req.requested_amount}. "
                    f"Expected total cost: {req.expected_total_cost}. "
                    f"Completed value estimate: {req.completed_value_estimate}. "
                    "No site photos means inspection is not_assessed and human "
                    "review is required."
                )
            )
        ]
        # Server-generated references, never a caller's path.
        from io import BytesIO
        from PIL import Image
        for reference in req.photo_paths:
            data = read_artifact(reference)
            with Image.open(BytesIO(data)) as image:
                mime = Image.MIME[image.format]
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))

        yield PhaseEvent(index=0, status="running", name=INSPECTION_PHASE_NAMES[0])
        finished: set[int] = set()
        reached_risk = False
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(role="user", parts=parts),
        ):
            # `assess_tranche` firing is the boundary between the two phases:
            # the photographs have been read by the time the risk tool is
            # called with what they showed.
            if not reached_risk and "assess_tranche" in _tool_calls(event):
                reached_risk = True
                finished.add(0)
                yield PhaseEvent(index=0, status="done", name=INSPECTION_PHASE_NAMES[0])
                yield PhaseEvent(index=1, status="running", name=INSPECTION_PHASE_NAMES[1])

        self._last_state = (
            await runner.session_service.get_session(
                app_name="neev", user_id=session.user_id, session_id=session.id
            )
        ).state

        # Settle whatever is still open, once. Yielding a phase done twice made
        # the screen tick a step it had already ticked.
        for index in range(len(INSPECTION_PHASE_NAMES)):
            if index not in finished:
                finished.add(index)
                yield PhaseEvent(index=index, status="done", name=INSPECTION_PHASE_NAMES[index])
        yield DoneEvent(redirect=f"/owner/loans/{req.loan_id}/progress")

    def inspection_output(self, req: MilestoneInspectionRequest) -> InspectionOutcome | None:
        """The two output_keys this run produced, through the same validators.

        `parse_output_key` rather than `parse_state`: the latter requires
        `boq_findings`, `cost_estimate` and `explanation`, which an inspection
        does not produce and should not have to fake. Same per-key normalizer
        and same model either way, so a stage read here validates exactly as it
        would in a full run.

        Nothing is returned unless the inspection itself parsed. A risk
        assessment without the observation behind it is a recommendation with no
        evidence, which is the one thing this screen must not store.
        """
        state = self._last_state
        if state is None:
            self.last_parse_errors = {"session": "no inspection has completed"}
            return None

        errors: dict[str, str] = {}
        parsed: dict[str, object] = {}
        for key in ("inspection_result", "risk_assessment"):
            raw = state.get(key)
            if raw is None:
                errors[key] = "absent from session state"
                continue
            try:
                parsed[key] = parse_output_key(key, raw)
            except Exception as exc:  # noqa: BLE001 - reported, never raised
                errors[key] = str(exc)

        self.last_parse_errors = errors
        if "inspection_result" not in parsed:
            return None
        return InspectionOutcome(
            inspection_result=parsed["inspection_result"],  # type: ignore[arg-type]
            risk_assessment=parsed.get("risk_assessment"),  # type: ignore[arg-type]
        )

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
