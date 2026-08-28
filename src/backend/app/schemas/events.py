"""The SSE event contract.

This vocabulary belongs to the pipeline, not to the Analyzing screen. It is
written now so the live runner has a defined target to emit against rather than
being reverse-engineered from a finished UI (spec §5.1a).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.pipeline import Tone


class PhaseEvent(BaseModel):
    type: Literal["phase"] = "phase"
    index: int
    status: Literal["done", "running", "queued"]
    name: str
    sub: str | None = None


class FindingEvent(BaseModel):
    type: Literal["finding"] = "finding"
    flag: str
    tone: Tone
    text: str


class ProgressEvent(BaseModel):
    type: Literal["progress"] = "progress"
    pct: int
    detail: str
    eta_s: int | None = None


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    redirect: str


class ErrorEvent(BaseModel):
    """A run that crashed, named as such.

    CONTRACT CHANGE (Task 12). Without this, a crashed analysis published only a
    DoneEvent and the Analyzing screen redirected as though it had succeeded —
    the reason was recorded on the job and never reached the client.

    It is additive and never terminal: the stream still ends with DoneEvent, so
    a consumer that does not know this variant behaves exactly as before. A
    consumer that does know it can show the failure before following the
    redirect.
    """

    type: Literal["error"] = "error"
    message: str
    # Where to send the reader anyway, so a failure is never a dead end.
    redirect: str | None = None


PipelineEvent = Annotated[
    PhaseEvent | FindingEvent | ProgressEvent | ErrorEvent | DoneEvent,
    Field(discriminator="type"),
]
