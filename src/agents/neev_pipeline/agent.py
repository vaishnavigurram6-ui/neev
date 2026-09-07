# agents/neev_pipeline/agent.py
# Neev pipeline: SequentialAgent, five specialists, shared state via output_key.
# NOTE: replaces the earlier Workflow(edges=...) form, which is not the ADK API.

from google.adk.agents import Agent, SequentialAgent

from .config import GEMINI_MODEL
from .tools.boq_analyst_tool import (
    lookup_benchmark_rate,
    check_rate_deviation,
    check_steel_rcc_ratio,
    check_missing_scope,
    check_payment_schedule,
)
from .tools.cost_estimation_tool import estimate_construction_cost
from .tools.visual_inspector_tool import verify_construction_stage
from .tools.disbursal_risk_tool import assess_tranche

boq_analyst_agent = Agent(
    name="boq_analyst_agent",
    model=GEMINI_MODEL,
    instruction=(
        "You are a quantity surveyor working FOR the home owner. Read the attached "
        "Bill of Quantities (PDF/image/Excel) and:\n"
        "1. Parse every line item to {id, desc, qty, unit, rate, amount}.\n"
        "2. For each priced item, call lookup_benchmark_rate then check_rate_deviation. "
        "Flag type RATE_OUTLIER only when the tool returns flag=true; quote the tool's "
        "deviation number verbatim. If no benchmark matched, mark UNBENCHMARKED — never "
        "estimate a benchmark yourself.\n"
        "3. Flag UNDERSPECIFIED items: no grade (e.g. TMT without Fe500), no brand, "
        "no IS standard.\n"
        "4. Sum steel (kg) and RCC (cum) quantities and call check_steel_rcc_ratio.\n"
        "5. Call check_missing_scope with all item descriptions; each missing item "
        "becomes a MISSING_SCOPE flag.\n"
        "6. Read the payment schedule; call check_payment_schedule with the fraction "
        "due before slab.\n"
        "7. Also flag if GST treatment is not stated anywhere (GST_SILENT).\n\n"
        "For EVERY flag produce: {item, type, evidence, question}. 'evidence' cites "
        "the tool output or the document line. 'question' is one polite sentence the "
        "owner can send the contractor in writing. Questions, not verdicts — never "
        "state or imply the contractor is cheating.\n\n"
        "Output JSON: {line_items: [...], flags: [...], boq_total, "
        "payment_pct_before_slab}."
    ),
    tools=[
        lookup_benchmark_rate,
        check_rate_deviation,
        check_steel_rcc_ratio,
        check_missing_scope,
        check_payment_schedule,
    ],
    output_key="boq_findings",
)

cost_estimation_agent = Agent(
    name="cost_estimation_agent",
    model=GEMINI_MODEL,
    instruction=(
        "Using {boq_findings} and the stated location and built-up area, call "
        "estimate_construction_cost to establish expected_total_cost and the "
        "completed_value_estimate (median market ₹/sqft x built-up area). "
        "Report sanction_gap = sanctioned_amount - expected_total_cost when the "
        "sanctioned amount is provided. Use only tool-returned numbers.\n"
        "Then account for WHERE the gap comes from, as `sections`: one entry per "
        "work section that differs, {name, quoted, market, delta}, delta = "
        "quoted - market. A negative delta means the BoQ is under-provisioned "
        "for that section. Cover only sections you can source from "
        "{boq_findings} or the tool — omit the array rather than estimate one, "
        "and never let the entries contradict expected_total_cost.\n"
        "Output JSON: {expected_total_cost, completed_value_estimate, "
        "sanction_gap, sections}."
    ),
    tools=[estimate_construction_cost],
    output_key="cost_estimate",
)

visual_inspector_agent = Agent(
    name="visual_inspector_agent",
    model=GEMINI_MODEL,
    instruction=(
        "Verify the submitted site photos (2-3 angles) against the claimed "
        "construction stage using verify_construction_stage. Use the tool's "
        "checklist-based, banded-confidence output as-is — do not invent a more "
        "precise percentage than the tool returns, and never override a "
        "needs_human_review flag.\n"
        "Output JSON: {stage, confidence, matches_claim, evidence_notes}."
    ),
    tools=[verify_construction_stage],
    output_key="inspection_result",
)

disbursal_risk_agent = Agent(
    name="disbursal_risk_agent",
    model=GEMINI_MODEL,
    instruction=(
        "Call assess_tranche exactly once, passing FLAT SCALAR values read from "
        "{cost_estimate}, {inspection_result}, and the loan context (sanctioned "
        "amount, cumulative disbursed). Do not compute any ratio yourself; report "
        "the tool's output unchanged.\n"
        "Output JSON: the assess_tranche result verbatim."
    ),
    tools=[assess_tranche],
    output_key="risk_assessment",
)

explainer_agent = Agent(
    name="explainer_agent",
    model=GEMINI_MODEL,
    instruction=(
        "Write two rationales from {boq_findings}, {cost_estimate}, "
        "{inspection_result}, {risk_assessment}:\n"
        "- owner_view: plain, empathetic language. Name the specific rupee "
        "figures (e.g. the cost-to-complete gap) and what the owner can do next. "
        "Include the negotiation questions from boq_findings when present.\n"
        "- officer_view: audit-grade. Exposure ratio, verified value, evidence "
        "list, benchmark sources.\n"
        "HARD RULE: you may only reference numbers that appear in upstream state. "
        "If a number is not there, say so rather than estimating.\n"
        "Output JSON: {owner_view, officer_view}."
    ),
    output_key="explanation",
)

root_agent = SequentialAgent(
    name="neev_pipeline",
    sub_agents=[
        boq_analyst_agent,
        cost_estimation_agent,
        visual_inspector_agent,
        disbursal_risk_agent,
        explainer_agent,
    ],
)
