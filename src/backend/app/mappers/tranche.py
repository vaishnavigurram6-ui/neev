"""Tranche Decision — the "math in one line each" table and the evidence grid.

Each math row carries the calculation as text and the result as a number, so the
screen renders the arithmetic the design shows without the backend formatting
any money.
"""

from app.db import models
from app.schemas.views import (
    EvidenceChipView,
    MathRowView,
    PhotoView,
    StageView,
    TrancheDecisionView,
)

STAGE_ORDER = ["foundation", "plinth", "slab", "brickwork_roof", "finishing"]
STAGE_LABEL = {
    "foundation": "Foundation",
    "plinth": "Plinth",
    "slab": "Slab",
    "brickwork_roof": "Brickwork",
    "finishing": "Finishing",
}
RECOMMENDATION_TONE = {
    "HOLD": "danger",
    "ESCALATE": "danger",
    "INSPECT": "warn",
    "RELEASE": "success",
}


def to_tranche_decision(loan: models.Loan, tranche: models.Tranche) -> TrancheDecisionView:
    # Only tranches settled BEFORE this one. The tranche being rendered must be
    # excluded: when it is itself already paid it would otherwise be its own
    # predecessor, making request_amount 0 and printing "T3 + T3" in the math.
    prior_paid = [
        t for t in loan.tranches if t.status == "paid" and t.number < tranche.number
    ]
    request_amount = tranche.disbursed_cum - (
        prior_paid[-1].disbursed_cum if prior_paid else 0
    )

    stages: list[StageView] = []
    for name in STAGE_ORDER:
        matching = next((t for t in loan.tranches if t.milestone == name), None)
        if matching is None:
            stages.append(StageView(name=STAGE_LABEL[name], sub="not started", state="todo"))
            continue
        if matching.status == "paid":
            state, sub = "done", f"verified T{matching.number}"
        elif matching.number == tranche.number:
            state, sub = "current", "read from photos"
        else:
            state, sub = "todo", "not started"
        stages.append(StageView(name=STAGE_LABEL[name], sub=sub, state=state))

    disbursed_calc = " + ".join(f"T{t.number}" for t in prior_paid + [tranche])
    gap = tranche.cost_to_complete_gap
    math = [
        MathRowView(
            label="Disbursed so far",
            calc=disbursed_calc,
            result=float(tranche.disbursed_cum),
            result_kind="money",
        ),
        MathRowView(
            label="Verified value in place",
            calc="stage × BoQ schedule of values",
            result=_number_or_dash(tranche.verified_value),
            result_kind=_kind(tranche.verified_value, "money"),
        ),
        MathRowView(
            label="Disbursement exposure",
            calc=f"{tranche.disbursed_cum} ÷ {tranche.verified_value or 0}",
            result=_number_or_dash(tranche.exposure_ratio),
            result_kind=_kind(tranche.exposure_ratio, "ratio"),
            # An undefined ratio means there is no verified value in place at
            # all — the worst case, and never something to render as a pass.
            tone=(
                "danger"
                if tranche.exposure_ratio is None or tranche.exposure_ratio > 1.0
                else "success"
            ),
        ),
        MathRowView(
            label="Cost to complete",
            calc=f"remaining BoQ items × current {loan.locality} rates",
            result=_number_or_dash(tranche.cost_to_complete),
            result_kind=_kind(tranche.cost_to_complete, "money"),
        ),
        MathRowView(
            label="Cost-to-complete gap",
            calc=f"({loan.sanctioned} − {tranche.disbursed_cum}) − {tranche.cost_to_complete or 0}",
            result=_number_or_dash(gap),
            result_kind=_kind(gap, "money"),
            # A gap of None is a closed loan: no shortfall to report, but not a
            # pass either. Only a real, non-negative figure earns "success".
            tone="neutral" if gap is None else ("danger" if gap < 0 else "success"),
        ),
    ]

    photos = [
        PhotoView(slot_key=photo.slot_key, caption=photo.caption, chips=_chips(photo))
        for photo in tranche.photos
    ]

    return TrancheDecisionView(
        loan_id=loan.id,
        borrower=loan.borrower_name,
        locality=loan.locality,
        tranche_number=tranche.number,
        milestone=tranche.milestone,
        request_amount=float(request_amount),
        recommendation=tranche.recommendation or "INSPECT",
        recommendation_tone=RECOMMENDATION_TONE.get(tranche.recommendation or "INSPECT", "warn"),  # type: ignore[arg-type]
        exposure=tranche.exposure_ratio,
        exposure_undefined=tranche.exposure_undefined,
        needs_human_review=tranche.needs_human_review,
        confidence=tranche.confidence,
        stages=stages,
        math=math,
        photos=photos,
        owner_view=tranche.owner_view,
        officer_view=tranche.officer_view,
    )


def _number_or_dash(value: float | int | None) -> float | str:
    """A missing figure renders as an em dash, never as a misleading 0."""
    return "—" if value is None else float(value)


def _kind(value: float | int | None, kind: str) -> str:
    return "text" if value is None else kind


def _chips(photo: models.Photo) -> list[EvidenceChipView]:
    chips: list[EvidenceChipView] = []
    if photo.geotag_match is not None:
        chips.append(
            EvidenceChipView(
                label="Geotag matches" if photo.geotag_match else "Geotag mismatch",
                tone="success" if photo.geotag_match else "danger",
            )
        )
    if photo.timestamp_ok is not None:
        chips.append(
            EvidenceChipView(
                label="Timestamp checks out" if photo.timestamp_ok else "Timestamp suspect",
                tone="success" if photo.timestamp_ok else "danger",
            )
        )
    if photo.same_angle is not None:
        chips.append(
            EvidenceChipView(
                label="Same angle as last set" if photo.same_angle else "Different angle",
                tone="success" if photo.same_angle else "warn",
            )
        )
    return chips
