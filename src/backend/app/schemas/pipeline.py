"""The five ADK output_key shapes, as Pydantic models.

Transcribed from src/agents/neev_pipeline/agent.py, where each agent's instruction
ends with an explicit "Output JSON: {...}" contract:

  boq_analyst_agent      -> boq_findings      {line_items, flags, boq_total,
                                               payment_pct_before_slab}
  cost_estimation_agent  -> cost_estimate     {expected_total_cost,
                                               completed_value_estimate, sanction_gap}
  visual_inspector_agent -> inspection_result {stage, confidence, matches_claim,
                                               evidence_notes}
  disbursal_risk_agent   -> risk_assessment   the assess_tranche result verbatim
  explainer_agent        -> explanation       {owner_view, officer_view}

Fields beyond those contracts are present because the tools return them
(needs_human_review, benchmark_rate) or because a screen needs them and a real
run can supply them (geotag_match, cost_to_complete). They are optional so
today's authored fixture and tomorrow's live output both validate.

Money is stored as a number of rupees, never as a formatted string.
"""

from typing import Literal

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, model_validator


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

FlagType = Literal[
    "RATE_OUTLIER",
    "UNBENCHMARKED",
    "UNDERSPECIFIED",
    "MISSING_SCOPE",
    "GST_SILENT",
    "STEEL_RATIO",
    "FRONT_LOADED",
]

Tone = Literal["danger", "warn", "success", "neutral"]


class LineItem(BaseModel):
    id: str
    desc: str
    qty: float
    unit: str
    rate: float
    amount: float
    section: str | None = None


class Flag(BaseModel):
    item: str
    type: FlagType
    evidence: str
    question: str
    # Presentation-independent status. Never a colour: the theme resolves tone.
    tone: Tone = "danger"
    # Short human label the pill shows, e.g. "Rate +22%", "No grade", "Missing".
    label: str
    benchmark_rate: float | None = None
    deviation_pct: float | None = None
    # Set on MISSING_SCOPE flags, where there is no priced line to point at.
    expected_qty: float | None = None
    expected_unit: str | None = None
    expected_amount: float | None = None


class BoqFindings(BaseModel):
    line_items: list[LineItem]
    flags: list[Flag]
    boq_total: float
    payment_pct_before_slab: float


class PaymentStage(BaseModel):
    label: str
    pct: float
    before_slab: bool


class CostEstimate(BaseModel):
    expected_total_cost: float
    completed_value_estimate: float
    sanction_gap: float | None = None
    fair_price_for_quoted_scope: float | None = None
    missing_scope_value: float | None = None
    sections: list["CostSection"] = Field(default_factory=list)


class CostSection(BaseModel):
    """One row of the Sanction Check "where the gap comes from" table."""

    name: str
    quoted: float | None = None
    market: float | None = None
    delta: float
    quoted_note: str | None = None

    @model_validator(mode="after")
    def reconcile_delta(self):
        # Positive = added cost; negative = potential saving. Derive, never
        # trust a model's sign or mutate the original captured evidence file.
        if self.quoted is not None and self.market is not None:
            self.delta = self.market - self.quoted
        return self


# The five milestones a photograph can show. Anything else -- "not_assessed"
# above all -- means nothing was observed, and every figure the risk tool
# derives from a stage is then an assumption rather than a measurement.
OBSERVABLE_STAGES = frozenset(
    {"foundation", "plinth", "slab", "brickwork_roof", "finishing"}
)


class InspectionResult(BaseModel):
    stage: str
    confidence: Literal["high", "medium", "low"]
    matches_claim: bool
    evidence_notes: list[str] = Field(default_factory=list)
    needs_human_review: bool = True
    geotag_match: bool | None = None
    timestamp_ok: bool | None = None
    same_angle: bool | None = None


class RiskAssessment(BaseModel):
    # None when the ratio is undefined (expected_total_cost == 0). Infinity is
    # not valid JSON, so it is never serialised as a number.
    exposure_ratio: float | None = None
    exposure_undefined: bool = False
    projected_exposure_ratio: float | None = None
    recommendation: Literal["RELEASE", "HOLD", "ESCALATE", "INSPECT"]
    pct_complete: float
    verified_value: float
    cost_to_complete: float | None = None
    cost_to_complete_gap: float
    live_ltv_pct: float | None = None
    ltv_default_prior: float | None = None
    reasons: list[str] = Field(default_factory=list)


class Explanation(BaseModel):
    owner_view: str
    officer_view: str


class PipelineOutput(BaseModel):
    """One loan's complete pipeline state — the five output_key values together.

    inspection_result and risk_assessment are optional: a loan that has not yet
    requested a tranche has neither.
    """

    boq_findings: BoqFindings
    cost_estimate: CostEstimate
    inspection_result: InspectionResult | None = None
    risk_assessment: RiskAssessment | None = None
    explanation: Explanation
    payment_schedule: list[PaymentStage] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_evidence_gate(self):
        inspection, risk = self.inspection_result, self.risk_assessment
        if risk and risk.recommendation == "RELEASE" and (
            not inspection or inspection.needs_human_review
            or not inspection.matches_claim or inspection.confidence == "low"
            or inspection.stage not in OBSERVABLE_STAGES
        ):
            risk.recommendation = "ESCALATE"
            risk.reasons.append("Release blocked: inspection evidence requires human review.")
        return self


CostEstimate.model_rebuild()
