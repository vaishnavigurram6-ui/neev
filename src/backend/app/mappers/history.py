"""Per-phase history — what was claimed, what was seen, what was decided.

One mapper feeds two screens: Build Progress (the owner's account of their own
build) and Tranche Decision (the lender's audit trail). They must not be able to
tell different stories about the same phase, which is why neither computes any of
this for itself.

Two things here are deliberate and easy to get wrong:

  * `exposure` is computed AT each phase from what had been drawn and what was
    verified then. Carrying today's 1.29 back across every row would hide the
    shape of the problem -- on loan 1001 exposure was worse at the plinth than it
    is now, because the schedule was front-loaded and the work caught up later.
  * `released_amount` is the step, not the cumulative. `disbursed_cum` is a
    running total, so reporting it as "released" triple-counts the first tranche
    by the third row.
"""

from app.db import models
from app.schemas.views import PhaseDecisionView, PhaseHistoryView, PhotoView
from app.mappers.tranche import STAGE_LABEL, _chips

STATUS_LABEL = {"paid": "Released", "on_hold": "On hold", "upcoming": "Not requested"}
STATUS_TONE = {"paid": "success", "on_hold": "danger", "upcoming": "neutral"}


def to_phase_history(loan: models.Loan) -> list[PhaseHistoryView]:
    phases: list[PhaseHistoryView] = []
    previous_cum = 0

    for tranche in sorted(loan.tranches, key=lambda t: t.number):
        status = tranche.status if tranche.status in STATUS_LABEL else "upcoming"
        released = max(0, tranche.disbursed_cum - previous_cum)

        verified = _verified_at(loan, tranche)
        drawn = tranche.disbursed_cum if status == "paid" else previous_cum
        exposure = _exposure(drawn, verified)

        phases.append(
            PhaseHistoryView(
                tranche_number=tranche.number,
                milestone=tranche.milestone,
                label=STAGE_LABEL.get(tranche.milestone, tranche.milestone.replace("_", " ")),
                status=status,  # type: ignore[arg-type]
                status_label=STATUS_LABEL[status],
                tone=STATUS_TONE[status],  # type: ignore[arg-type]
                inspected_on=tranche.inspection_date,
                claimed_stage=tranche.claimed_stage or tranche.milestone,
                observed_stage=tranche.observed_stage,
                observed_by_neev=bool(tranche.confidence and tranche.observed_stage
                                      and tranche.observed_stage != "not_assessed"),
                photos=[
                    PhotoView(slot_key=p.slot_key, caption=p.caption, chips=_chips(p))
                    for p in tranche.photos
                ],
                evidence_notes=[p.caption for p in tranche.photos if p.caption],
                confidence=tranche.confidence,
                needs_human_review=tranche.needs_human_review,
                verified_value=verified,
                exposure=exposure,
                exposure_undefined=exposure is None and verified is not None,
                released_amount=float(released),
                disbursed_cum=float(tranche.disbursed_cum),
                recommendation=tranche.recommendation,
                decision=_decision(tranche),
            )
        )
        previous_cum = tranche.disbursed_cum

    return phases


def _verified_at(loan: models.Loan, tranche: models.Tranche) -> float | None:
    """Value in place when this phase completed.

    Where the pipeline recorded a figure, that figure wins. Otherwise it is
    derived from the one already on screen: 13,90,000 verified at 50% complete
    implies a 27,80,000 base, so each phase is its cumulative planned share of
    that. Anything else would contradict the Tranche Decision screen.
    """
    if tranche.verified_value is not None:
        return float(tranche.verified_value)

    anchor = next((t for t in loan.tranches if t.verified_value is not None), None)
    if anchor is None or not tranche.planned_cum_pct:
        return None

    # The anchor's figure evidences the stage the photographs SHOW, not the
    # milestone the tranche is named after: on loan 1001 the 13,90,000 sits on
    # T4 (brickwork, 80% planned) while the photographs verify the slab (50%).
    # Dividing by 0.80 would put the base at 17,37,500 and make the slab row
    # read 8,68,750 -- contradicting the Tranche Decision screen it is supposed
    # to agree with.
    evidenced = next(
        (t for t in loan.tranches if t.milestone == (anchor.observed_stage or anchor.milestone)),
        anchor,
    )
    if not evidenced.planned_cum_pct:
        return None

    base = float(anchor.verified_value) / float(evidenced.planned_cum_pct)
    # Nothing beyond the evidenced stage has been verified: a later phase shows
    # the same figure, not an extrapolation of work nobody has seen.
    share = min(float(tranche.planned_cum_pct), float(evidenced.planned_cum_pct))
    return round(base * share)


def _exposure(drawn: float, verified: float | None) -> float | None:
    """None rather than infinity when nothing is verified: Infinity is not valid
    JSON, and a ratio against zero is not a ratio."""
    if not verified:
        return None
    return round(drawn / verified, 2)


def _decision(tranche: models.Tranche) -> PhaseDecisionView | None:
    decision = tranche.decision
    if decision is None:
        return None
    tone = "success" if decision.action == "RELEASE" else "danger"
    return PhaseDecisionView(
        action=decision.action,
        tone=tone,  # type: ignore[arg-type]
        decided_by=decision.decided_by,
        decided_at=decision.decided_at.date(),
        note=decision.note,
    )
