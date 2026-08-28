"""View models the screens consume.

Numbers cross this boundary as numbers. `value_kind` tells the frontend which
formatter to apply, which is what keeps formatINR() the single formatter and
stops pre-formatted money entering the API (spec 5.1a).
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.pipeline import Tone

ValueKind = Literal["money", "money_compact", "count", "pct", "ratio", "text"]


class StatCardView(BaseModel):
    label: str
    value: float | str
    value_kind: ValueKind
    sub: str
    tone: Tone = "neutral"


class FlagRowView(BaseModel):
    item: str
    desc: str
    qty: float | None = None
    unit: str | None = None
    rate: float | None = None
    amount: float | None = None
    expected_qty: float | None = None
    expected_unit: str | None = None
    expected_amount: float | None = None
    note: str
    label: str
    tone: Tone


class FlagGroupView(BaseModel):
    name: str
    items: list[FlagRowView]


class QuestionView(BaseModel):
    number: int
    text: str
    status: str


class PaymentStageView(BaseModel):
    label: str
    pct: float
    before_slab: bool


class BoqReviewView(BaseModel):
    loan_id: str
    borrower: str
    contractor: str | None
    received_on: date | None
    item_count: int
    rev: int
    cards: list[StatCardView]
    groups: list[FlagGroupView]
    all_groups: list[FlagGroupView]
    questions: list[QuestionView]
    payment_schedule: list[PaymentStageView]
    pct_before_slab: float
    amount_before_slab: float
    gst_stated: bool


class SanctionBarView(BaseModel):
    label: str
    value: float
    pct_of_max: float
    sub: str
    tone: Tone = "neutral"


class SanctionSectionView(BaseModel):
    name: str
    quoted: float | None
    quoted_note: str | None
    market: float | None
    delta: float
    tone: Tone


class SanctionOptionView(BaseModel):
    title: str
    saves_label: str
    desc: str


class SanctionCheckView(BaseModel):
    loan_id: str
    bars: list[SanctionBarView]
    shortfall: float
    sections: list[SanctionSectionView]
    options: list[SanctionOptionView]


class PortfolioRowView(BaseModel):
    loan_id: str
    borrower: str
    locality: str
    paid_up_to: str
    seen_on_site: str
    behind_schedule: bool
    disbursed: float
    exposure: float | None
    gap: float | None
    gap_note: str | None = None
    action_label: str
    tone: Tone
    href: str


class PortfolioView(BaseModel):
    cards: list[StatCardView]
    rows: list[PortfolioRowView]


class MathRowView(BaseModel):
    label: str
    calc: str
    result: float | str
    result_kind: ValueKind
    tone: Tone = "neutral"


class StageView(BaseModel):
    name: str
    sub: str
    state: Literal["done", "current", "todo"]


class EvidenceChipView(BaseModel):
    label: str
    tone: Tone


class PhotoView(BaseModel):
    slot_key: str
    caption: str | None
    chips: list[EvidenceChipView] = Field(default_factory=list)


class TrancheDecisionView(BaseModel):
    loan_id: str
    borrower: str
    locality: str
    tranche_number: int
    milestone: str
    request_amount: float
    recommendation: str
    recommendation_tone: Tone
    exposure: float | None
    exposure_undefined: bool
    needs_human_review: bool
    confidence: str | None
    stages: list[StageView]
    math: list[MathRowView]
    photos: list[PhotoView]
    owner_view: str | None
    officer_view: str | None
