"""View models the screens consume.

Numbers cross this boundary as numbers. `value_kind` tells the frontend which
formatter to apply, which is what keeps formatINR() the single formatter and
stops pre-formatted money entering the API (spec 5.1a).
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field

from app.schemas.pipeline import Tone

ValueKind = Literal["money", "money_compact", "count", "pct", "ratio", "text"]


class BaseModel(PydanticBaseModel):
    # Response serialization includes defaults. Tell OpenAPI the actual wire shape.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


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
    analysis_mode: str = "unknown"
    provenance: dict[str, str] = Field(default_factory=dict)
    borrower: str
    contractor: str | None
    received_on: date | None
    item_count: int
    rev: int
    cards: list[StatCardView]
    groups: list[FlagGroupView]
    all_groups: list[FlagGroupView]
    questions: list[QuestionView]
    # How many more questions the analysis wrote than the screen shows. Stated
    # rather than dropped silently: every withheld question's flag is still in
    # the table above it.
    questions_withheld: int = 0
    # Lines the benchmark table had nothing to compare against. Not findings —
    # gaps in our own data — so they are counted here and not listed as flags.
    unbenchmarked_count: int = 0
    payment_schedule: list[PaymentStageView]
    # The quoted contract total. Present so the rail does not have to invert it
    # out of amount_before_slab / pct_before_slab, which is what the screen was
    # doing and which divides by zero on a schedule with nothing due before slab.
    boq_total: float
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
    provenance: dict[str, str] = Field(default_factory=dict)
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
    # paid | on_hold | upcoming. Added by Task 18: without it the decision screen
    # cannot tell a draw awaiting a decision from one already disbursed, and it
    # offered "Release" on money that had already gone out. `str`, not a Literal,
    # so an unrecognised status degrades to a screen that offers no decision
    # rather than a 500.
    status: str
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
    # Every earlier phase, so a decision is taken against the whole record
    # rather than one tranche in isolation. Forward-referenced: PhaseHistoryView
    # is declared below, next to BuildProgressView, which also carries it.
    phases: list["PhaseHistoryView"] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Added by Tasks 12/13, which needed three view models the plan named in its
# route tables but never defined. They live here rather than in the route layer
# because this module is the single place presentation shapes are declared, and
# app/mappers/ stays the only layer that builds them.
# ---------------------------------------------------------------------------


class LoanSummaryView(BaseModel):
    """The loan itself — what every owner and bank header needs to name it.

    Deliberately not screen-shaped: it carries the loan's own facts, and each
    screen picks the subset it renders.
    """

    loan_id: str
    borrower: str
    locality: str
    plot_label: str | None
    built_up_sqft: int | None
    sanctioned: float
    disbursed: float
    contractor: str | None
    latest_rev: int | None
    recommendation: str | None
    exposure: float | None
    gap: float | None
    current_stage: str | None
    tranche_count: int


class ProgressTrancheView(BaseModel):
    number: int
    name: str
    sub: str
    amount: float
    status_label: str
    tone: Tone
    state: Literal["done", "current", "todo"]


class StandingRowView(BaseModel):
    label: str
    # A str only ever carries the em dash for an unverified figure, paired with
    # value_kind "text" — the same convention MathRowView uses.
    value: float | str
    value_kind: ValueKind = "money"
    tone: Tone = "neutral"


class PhaseHistoryView(BaseModel):
    """One build phase, after the fact: claimed, seen, decided.

    Read by both Build Progress (the owner's account of their build) and Tranche
    Decision (the lender's audit trail), from one mapper, so the two cannot tell
    different stories about the same phase.
    """

    tranche_number: int
    milestone: str
    label: str
    status: Literal["paid", "on_hold", "upcoming"]
    status_label: str
    tone: Tone
    inspected_on: date | None
    claimed_stage: str | None
    observed_stage: str | None
    # False for phases released before Neev was involved: no photographs were
    # collected, and saying so is more honest than an empty evidence grid.
    observed_by_neev: bool
    photos: list[PhotoView] = Field(default_factory=list)
    evidence_notes: list[str] = Field(default_factory=list)
    confidence: str | None = None
    needs_human_review: bool = False
    verified_value: float | None = None
    # Exposure AT THIS PHASE, not today's. Front-loaded payments mean it was
    # worse early and improved as work caught up; carrying today's figure back
    # across every row would hide exactly that.
    exposure: float | None = None
    exposure_undefined: bool = False
    # The step, not the cumulative: reporting disbursed_cum as "released" would
    # triple-count the first tranche by the third row.
    released_amount: float
    disbursed_cum: float
    recommendation: str | None = None
    decision: "PhaseDecisionView | None" = None


class PhaseDecisionView(BaseModel):
    action: str
    tone: Tone
    decided_by: str
    decided_at: date
    note: str | None = None


class BuildProgressView(BaseModel):
    loan_id: str
    borrower: str
    locality: str
    plot_label: str | None
    sanctioned: float
    disbursed: float
    current_stage: str | None
    last_verified_on: date | None
    paused: bool
    tranches: list[ProgressTrancheView]
    standing: list[StandingRowView]
    steps: list[str]
    # Negative when the sanction will not finish the house at local rates.
    shortfall: float | None
    phases: list[PhaseHistoryView] = Field(default_factory=list)


class ContractorRowView(BaseModel):
    id: str
    name: str
    meta: str
    sites: int
    flags_per_boq: float | None
    underspecified_share: float | None
    overrun_pct: float | None
    sites_gone_quiet: int
    tier: str
    tone: Tone


class ContractorScorecardView(BaseModel):
    rows: list[ContractorRowView]

PhaseHistoryView.model_rebuild()
TrancheDecisionView.model_rebuild()


class ChangeOrderView(BaseModel):
    """One variation the contractor has proposed, priced against the signed BoQ."""

    id: int
    title: str
    signed_desc: str
    signed_amount: float
    proposed_desc: str
    proposed_amount: float
    delta: float
    neevs_read: str
    status: str
    tone: Tone = "warn"
    counter_amount: float | None = None
    owner_note: str | None = None
    replied_at: datetime | None = None
    # Whether this order still awaits the owner. The screen needs the question
    # "can I act on this?" answered once, here, rather than re-derived from a
    # status string on every row.
    open: bool = True


class ChangeOrdersView(BaseModel):
    loan_id: str
    signed_total: float
    orders: list[ChangeOrderView]
    accepted_total: float
    pending_total: float
    # Signed + accepted + everything still pending, as proposed. The figure the
    # owner is deciding against, and the one that can breach the sanction.
    if_accepted_total: float
    sanctioned: float
    # Positive means over sanction. Signed so the screen never has to guess
    # which side of the line it is on.
    over_sanction: float
