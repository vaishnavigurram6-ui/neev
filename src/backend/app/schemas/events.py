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


PipelineEvent = Annotated[
    PhaseEvent | FindingEvent | ProgressEvent | DoneEvent,
    Field(discriminator="type"),
]
