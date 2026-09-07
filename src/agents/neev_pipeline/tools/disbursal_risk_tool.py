# agents/neev_pipeline/tools/disbursal_risk_tool.py
# Pure arithmetic — no LLM inside the math, no nested dicts (flat scalar
# params avoid the KeyError class of failures when the model builds the call).

from ..config import (
    MILESTONE_ORDER,
    cumulative_weight,
    EXPOSURE_HOLD_THRESHOLD,
    ltv_default_prior,
)


def assess_tranche(
    expected_total_cost: float,
    observed_stage: str,
    stage_confidence: str,
    sanctioned_amount: float,
    disbursed_cumulative: float,
    completed_value_estimate: float,
    matches_claim: bool = True,
) -> dict:
    """Computes disbursement exposure and cost-to-complete gap; recommends
    RELEASE / HOLD / ESCALATE for the current tranche.

    Args:
        expected_total_cost: Full build cost from cost_estimation_agent (INR).
        observed_stage: Stage from visual_inspector_agent — one of
            foundation, plinth, slab, brickwork_roof, finishing.
        stage_confidence: 'high' | 'med' | 'low' from visual_inspector_agent.
        sanctioned_amount: Total sanctioned loan (INR).
        disbursed_cumulative: Amount already paid out incl. this point (INR).
        completed_value_estimate: Market value of the finished house (INR),
            from cost_estimation_agent, used for live LTV context.
        matches_claim: Whether the site evidence actually supports what the
            borrower claimed, from visual_inspector_agent. False means the
            photos contradict the claim or the approved plan -- money must not
            be released on evidence that disagrees with itself.
    Returns:
        dict with 'exposure_ratio', 'recommendation', 'cost_to_complete_gap',
        'live_ltv_pct', 'ltv_default_prior', 'reasons'.
    """
    reasons = []

    # An unverifiable stage is not an error, it is an answer. With no usable
    # photo the inspector reports something outside MILESTONE_ORDER, and
    # cumulative_weight() would raise -- which took a whole billed five-agent
    # run down the first time this path ran for real. Progress that cannot be
    # verified cannot justify a release, so say INSPECT and quote no exposure
    # rather than compute one from a stage nobody confirmed.
    if observed_stage not in MILESTONE_ORDER:
        live_ltv = (disbursed_cumulative / completed_value_estimate * 100
                    if completed_value_estimate else 0.0)
        return {
            "exposure_ratio": None,
            "exposure_undefined": True,
            "recommendation": "INSPECT",
            "pct_complete": 0.0,
            "verified_value": 0.0,
            # Nothing is verified, so the whole build is still to pay for.
            "cost_to_complete": round(expected_total_cost, 0),
            "cost_to_complete_gap": round(
                (sanctioned_amount - disbursed_cumulative)
                - expected_total_cost, 0),
            "live_ltv_pct": round(live_ltv, 1),
            "ltv_default_prior": ltv_default_prior(live_ltv),
            "reasons": [
                f"Construction stage could not be verified from the evidence "
                f"supplied (reported as {observed_stage or 'none'!r}). Exposure is "
                f"undefined without a confirmed stage, so no release decision can "
                f"be made -- route to physical inspection.",
            ],
        }

    pct_complete = cumulative_weight(observed_stage)
    verified_value = expected_total_cost * pct_complete

    exposure = disbursed_cumulative / verified_value if verified_value else float("inf")

    remaining_cost = expected_total_cost * (1 - pct_complete)
    remaining_funds = sanctioned_amount - disbursed_cumulative
    gap = remaining_funds - remaining_cost  # negative => build will stall

    live_ltv = (disbursed_cumulative / completed_value_estimate * 100
                if completed_value_estimate else 0.0)

    # Decision — evidence gates first, then exposure. Order matters: a
    # comfortable exposure must never let contradicted evidence through, which
    # is what happened on the first real capture of loan 1002.
    if not matches_claim:
        recommendation = "ESCALATE"
        reasons.append("Site evidence contradicts the borrower's claim or the "
                       "approved plan; no release until the discrepancy is "
                       "explained. See the inspection notes.")
    elif stage_confidence == "low":
        recommendation = "ESCALATE"
        reasons.append("Photo-evidence confidence is low; route to physical inspection "
                       "before any release decision.")
    elif exposure > EXPOSURE_HOLD_THRESHOLD:
        recommendation = "HOLD"
        reasons.append(f"Disbursed (₹{disbursed_cumulative:,.0f}) exceeds verified "
                       f"value in place (₹{verified_value:,.0f}); exposure "
                       f"{exposure:.2f} > {EXPOSURE_HOLD_THRESHOLD}.")
    else:
        recommendation = "RELEASE"
        reasons.append(f"Exposure {exposure:.2f} within threshold; verified stage "
                       f"'{observed_stage}' supports cumulative disbursement.")

    if gap < 0:
        reasons.append(f"Cost-to-complete gap is negative (₹{gap:,.0f}): remaining "
                       f"funds will not finish the build at expected cost — "
                       f"owner should re-scope now.")

    return {
        "exposure_ratio": round(exposure, 2),
        # Present on both return paths so a caller never has to guess whether
        # the key exists; RiskAssessment declares it either way.
        "exposure_undefined": False,
        "recommendation": recommendation,
        "pct_complete": pct_complete,
        "verified_value": round(verified_value, 0),
        # Already computed for the gap and previously discarded, which left
        # "Needed to finish" and "Cost to complete" as em dashes on screen.
        "cost_to_complete": round(remaining_cost, 0),
        "cost_to_complete_gap": round(gap, 0),
        "live_ltv_pct": round(live_ltv, 1),
        "ltv_default_prior": ltv_default_prior(live_ltv),
        "reasons": reasons,
    }
