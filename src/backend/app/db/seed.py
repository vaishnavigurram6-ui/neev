"""Idempotent seed.

Sources, in order of authority:
  - fixtures/draw_schedule.csv          -> tranche rows, sanctioned, disbursed
  - app/fixtures/portfolio_rows.json    -> borrower names, localities, and the
                                           design's risk figures and ordering
  - app/fixtures/loan_*_pipeline.json   -> BoQ line items, flags, questions,
                                           narratives for 1001 and 1002

Run: python -m app.db.seed --reset
"""

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, select

from app.db import models
from app.db.session import SessionLocal, init_db
from app.fixtures.loader import available_loan_ids, load_pipeline_output

REPO_ROOT = Path(__file__).resolve().parents[4]
DRAW_SCHEDULE = REPO_ROOT / "fixtures" / "draw_schedule.csv"
PORTFOLIO_ROWS = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio_rows.json"

CONTRACTORS = [
    # From Neev 5 Contractor Scorecard.dc.html. Loan 1001's contractor is named
    # on the BoQ Review header: "Sri Sai Constructions".
    {"id": "c1", "name": "Sri Sai Constructions", "sites": 4, "flags_per_boq": 7.2,
     "underspecified_share": 0.31, "overrun_pct": 0.18, "sites_gone_quiet": 1, "tier": "WATCH"},
    {"id": "c2", "name": "Bhavya Builders", "sites": 3, "flags_per_boq": 3.1,
     "underspecified_share": 0.14, "overrun_pct": 0.07, "sites_gone_quiet": 0, "tier": "REVIEW"},
    {"id": "c3", "name": "Sree Rama Constructions", "sites": 3, "flags_per_boq": 1.4,
     "underspecified_share": 0.05, "overrun_pct": 0.02, "sites_gone_quiet": 0, "tier": "RELIABLE"},
]

LOAN_CONTRACTOR = {
    "1001": "c1", "1003": "c1", "1004": "c1", "1009": "c1",
    "1002": "c3", "1005": "c3", "1010": "c3",
    "1006": "c2", "1007": "c2", "1008": "c2",
}

PLOT_LABELS = {"1001": "Plot 47, Kompally"}
# built_up_sqft now lives in portfolio_rows.json, so scripts/record_golden_run.py
# can read it without importing this module (which needs SQLAlchemy).

# Tranche status for the golden case: T1/T2 paid, T3 held pending this decision.
# Loan 1001's ledger. T1-T3 are PAID and the tranche under decision is T4.
#
# This resolves a contradiction in the source data: the frozen figures, the
# Tranche Decision mockup and the fixture's own officer_view all put
# 18,00,000 disbursed (3 x 6,00,000), which only adds up if T3 has gone out —
# yet the tranche was also marked on_hold. Money cannot be both disbursed and
# withheld. The mockup's own arithmetic settles it: its gap row reads
# "(28,00,000 - 18,00,000) - 15,80,000", treating 18,00,000 as already drawn.
#
# So the decision on screen is the NEXT draw, and every frozen figure survives:
# disbursed 18,00,000, verified value in place 13,90,000, exposure 1.29,
# cost-to-complete gap -5,80,000, recommendation HOLD.
TRANCHE_STATUS_1001 = {1: "paid", 2: "paid", 3: "paid", 4: "on_hold"}

# The tranche under decision. draw_schedule.csv stops at T3 for loan 1001, and
# that CSV is read directly by tests/test_offline.py — so the pending request is
# added here, in the seed, rather than by editing the fixture out from under
# those 28 tests.
#
# 0.80 cumulative x 28,00,000 sanctioned = 22,40,000, so the request itself is
# 4,40,000. observed_stage stays "slab": the photographs verify the slab, which
# is what inspection_result reports, while the money being asked for is the
# brickwork-and-roof draw.
PENDING_TRANCHE_1001 = {
    "number": 4,
    "milestone": "brickwork_roof",
    "planned_cum_pct": 0.80,
    "disbursed_cum": 2240000,
    "inspection_date": date(2026, 8, 10),
    "observed_stage": "slab",
}

# Which tranche carries the pipeline's risk assessment, per loan: the one a
# decision is pending on.
RISK_TRANCHE = {"1001": 4}
DEFAULT_RISK_TRANCHE = 3


def _tables_in_delete_order() -> list:
    return [
        models.Decision, models.Photo, models.Tranche, models.Flag, models.LineItem,
        models.Question, models.ChangeOrder, models.BoqRevision, models.Loan, models.Contractor,
    ]


def seed(reset: bool = False) -> dict[str, int]:
    init_db()
    with SessionLocal() as db:
        if reset:
            for table in _tables_in_delete_order():
                db.execute(delete(table))
            db.commit()

        if db.scalar(select(models.Loan).limit(1)) is not None:
            # Already seeded. Idempotent by design: reseeding a populated
            # database is a no-op rather than a duplicate-key error.
            return _counts(db)

        for row in CONTRACTORS:
            db.add(models.Contractor(**row))

        rows = json.loads(PORTFOLIO_ROWS.read_text(encoding="utf-8"))
        schedule = _read_draw_schedule()

        for rank, row in enumerate(rows):
            loan_id = row["loan_id"]
            tranches = list(schedule[loan_id])
            if loan_id == "1001":
                tranches.append(PENDING_TRANCHE_1001)
            db.add(
                models.Loan(
                    id=loan_id,
                    borrower_name=row["borrower"],
                    locality=row["locality"],
                    plot_label=PLOT_LABELS.get(loan_id),
                    built_up_sqft=row.get("built_up_sqft"),
                    sanctioned=tranches[0]["sanctioned"],
                    disbursed=row["disbursed"],
                    contractor_id=LOAN_CONTRACTOR.get(loan_id),
                    paid_up_to=row["paid_up_to"],
                    seen_on_site=row["seen_on_site"],
                    behind_schedule=row["behind"],
                    exposure_ratio=row["exposure"],
                    cost_to_complete_gap=row["gap"],
                    recommendation=_recommendation(row["action"]),
                    hotlist_rank=rank,
                )
            )
            for entry in tranches:
                status = (
                    TRANCHE_STATUS_1001.get(entry["number"], "upcoming")
                    if loan_id == "1001"
                    else ("paid" if entry["disbursed_cum"] <= row["disbursed"] else "upcoming")
                )
                db.add(
                    models.Tranche(
                        loan_id=loan_id,
                        number=entry["number"],
                        milestone=entry["milestone"],
                        planned_cum_pct=entry["planned_cum_pct"],
                        disbursed_cum=entry["disbursed_cum"],
                        inspection_date=entry["inspection_date"],
                        observed_stage=entry["observed_stage"],
                        status=status,
                    )
                )
        db.commit()

        for loan_id in available_loan_ids():
            _seed_pipeline_output(db, loan_id)
        db.commit()

        _seed_derived_risk(db, rows)
        db.commit()

        _seed_change_orders(db)
        db.commit()

        return _counts(db)


def _recommendation(action: str) -> str:
    return {"HOLD": "HOLD", "INSPECT": "INSPECT", "ON TRACK": "RELEASE"}[action]


def _read_draw_schedule() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with DRAW_SCHEDULE.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            out.setdefault(raw["loan_id"], []).append(
                {
                    "number": int(raw["tranche_no"]),
                    "milestone": raw["milestone"],
                    "planned_cum_pct": float(raw["planned_cum_pct"]),
                    "sanctioned": int(raw["sanctioned"]),
                    "disbursed_cum": int(raw["disbursed_cum"]),
                    "inspection_date": date.fromisoformat(raw["inspection_date"]),
                    "observed_stage": raw["observed_stage"],
                }
            )
    return out


# Which BoQ Review group each flag belongs under. Groups and their order are the
# mockup's, verbatim.
# Grouping lives in one place. This file used to carry its own copy of the
# item-id -> section map, so changing the real one in app/services/persistence.py
# silently did nothing to the seeded rows -- the two drifted the moment captured
# runs replaced the authored fixture.
from app.services.persistence import FLAG_GROUPS_BY_TYPE, UNGROUPED


def _seed_pipeline_output(db, loan_id: str) -> None:
    output = load_pipeline_output(loan_id)
    findings = output.boq_findings

    revision = models.BoqRevision(
        loan_id=loan_id,
        rev=1,
        received_on=date(2026, 8, 12) if loan_id == "1001" else None,
        source_filename="sample_boq.pdf" if loan_id == "1001" else "clean_boq.pdf",
        boq_total=int(findings.boq_total),
        payment_pct_before_slab=findings.payment_pct_before_slab,
        item_count=40 if loan_id == "1001" else 43,
        pipeline_mode="fixture",
    )
    db.add(revision)
    db.flush()

    for item in findings.line_items:
        db.add(
            models.LineItem(
                revision_id=revision.id, item_id=item.id, section=item.section, desc=item.desc,
                qty=item.qty, unit=item.unit, rate=item.rate, amount=item.amount,
            )
        )

    for flag in findings.flags:
        db.add(
            models.Flag(
                revision_id=revision.id, item=flag.item, type=flag.type, label=flag.label,
                tone=flag.tone,
                group_name=FLAG_GROUPS_BY_TYPE.get(flag.type, UNGROUPED),
                evidence=flag.evidence, question=flag.question,
                benchmark_rate=flag.benchmark_rate, deviation_pct=flag.deviation_pct,
                expected_qty=flag.expected_qty, expected_unit=flag.expected_unit,
                expected_amount=flag.expected_amount,
            )
        )

    # The "Send before you sign" list, from the BoQ Review mockup verbatim.
    if loan_id == "1001":
        for number, text in enumerate(
            [
                "Confirm the TMT grade for item 4.2 — Fe 500 or Fe 500D per IS 1786 — in writing.",
                "RCC M25 is priced at ₹9,800/cum against a ₹8,033 local benchmark. What is the basis?",
                "External plaster and terrace waterproofing are absent. In scope, or extra — and at what rate?",
                "45% is due before slab. Please restructure toward the standard 25%-before-slab pattern.",
            ],
            start=1,
        ):
            db.add(models.Question(loan_id=loan_id, number=number, text=text, status="draft"))

    risk = output.risk_assessment
    inspection = output.inspection_result
    if risk is not None:
        risk_tranche_no = RISK_TRANCHE.get(loan_id, DEFAULT_RISK_TRANCHE)
        current = db.scalar(
            select(models.Tranche).where(
                models.Tranche.loan_id == loan_id,
                models.Tranche.number == risk_tranche_no,
            )
        )
        if current is not None:
            current.verified_value = int(risk.verified_value)
            current.exposure_ratio = risk.exposure_ratio
            current.exposure_undefined = risk.exposure_undefined
            # `is not None`, not truthiness: a genuine 0 is a real figure.
            current.cost_to_complete = (
                int(risk.cost_to_complete) if risk.cost_to_complete is not None else None
            )
            current.cost_to_complete_gap = int(risk.cost_to_complete_gap)
            current.recommendation = risk.recommendation

            # The Portfolio Hotlist row reads off the LOAN, the Tranche Decision
            # screen off the tranche. Both must be the same number or a row
            # links to a screen that contradicts it. The loan used to keep
            # portfolio_rows.json's authored exposure while the tranche took the
            # pipeline's -- 1.29 on the row against 1.11 on the screen once
            # captured runs replaced the authored fixture.
            parent = db.get(models.Loan, loan_id)
            if parent is not None:
                parent.exposure_ratio = risk.exposure_ratio
                parent.exposure_undefined = risk.exposure_undefined
                parent.cost_to_complete_gap = int(risk.cost_to_complete_gap)
                parent.recommendation = risk.recommendation
            current.owner_view = output.explanation.owner_view
            current.officer_view = output.explanation.officer_view
            if inspection is not None:
                current.confidence = inspection.confidence
                current.needs_human_review = inspection.needs_human_review
                for index, note in enumerate(inspection.evidence_notes[:3]):
                    db.add(
                        models.Photo(
                            tranche_id=current.id,
                            slot_key=f"{loan_id}-t{risk_tranche_no}-angle{index + 1}",
                            caption=note,
                            geotag_match=inspection.geotag_match,
                            timestamp_ok=inspection.timestamp_ok,
                            same_angle=inspection.same_angle,
                            taken_at=datetime(2026, 8, 10, 11, 42),
                        )
                    )


def _seed_derived_risk(db, rows: list[dict]) -> None:
    """Give every loan a coherent drill-in, not just 1001 and 1002.

    Only the two golden loans have authored pipeline output, so the other eight
    portfolio rows linked to a tranche screen that contradicted the row itself:
    the row read "HOLD, 1.42" while the screen read "INSPECT, exposure
    undefined" with an em dash in every math line.

    Nothing here is invented. Each loan's exposure, disbursed total and
    cost-to-complete gap are already authored in portfolio_rows.json; the two
    missing figures follow from them by definition:

        verified_value   = disbursed / exposure     (exposure IS disbursed/verified)
        cost_to_complete = (sanctioned - disbursed) - gap

    So the math table ties out arithmetically instead of showing blanks.

    What is NOT filled in: owner_view and officer_view stay null, because no
    narrative was ever written for these loans. The rationale panel shows an
    honest empty state rather than prose invented on their behalf.

    The linked tranche stays `paid`. That money is already out, so the screen
    correctly offers no decision -- and it is consistent with the portfolio
    ratio being a screen rather than a per-loan verdict, which
    scripts/portfolio_view.sql states outright.
    """
    for row in rows:
        loan_id = row["loan_id"]
        if loan_id in available_loan_ids():
            continue  # 1001 and 1002 carry real authored output

        loan = db.get(models.Loan, loan_id)
        if loan is None:
            continue

        drawn = [t for t in loan.tranches if t.status in ("paid", "on_hold")]
        if not drawn:
            continue
        target = max(drawn, key=lambda t: t.number)

        exposure = row["exposure"]
        disbursed = float(row["disbursed"])
        gap = row["gap"]

        target.exposure_ratio = exposure
        target.verified_value = int(round(disbursed / exposure)) if exposure else None
        target.exposure_undefined = not exposure
        target.recommendation = _recommendation(row["action"])
        if gap is not None:
            target.cost_to_complete_gap = int(gap)
            target.cost_to_complete = int(round((loan.sanctioned - disbursed) - gap))


def _seed_change_orders(db) -> None:
    # From Neev 6 Change Orders.dc.html.
    db.add_all(
        [
            models.ChangeOrder(
                loan_id="1001",
                title="Kitchen platform upgrade",
                signed_desc="Granite for kitchen platform, 18mm — 6.5 sqm at ₹2,900",
                signed_amount=18850,
                proposed_desc="Quartz composite platform, 20mm — 6.5 sqm at ₹5,400",
                proposed_amount=35100,
                neevs_read="Quartz at ₹5,400/sqm is within the Kompally range of ₹4,900–5,800, so the rate is fair. The change is a genuine upgrade, not a repricing of signed work.",
                status="pending",
                tone="warn",
            ),
            models.ChangeOrder(
                loan_id="1001",
                title="Additional electrical points",
                signed_desc="Concealed wiring per point — 68 points at ₹720",
                signed_amount=48960,
                proposed_desc="Concealed wiring per point — 79 points at ₹860",
                proposed_amount=67940,
                neevs_read="The 11 extra points are reasonable. The rate rising from ₹720 to ₹860 on the same work is not — the signed rate should hold for the added points.",
                status="pending",
                tone="danger",
            ),
        ]
    )


def _counts(db) -> dict[str, int]:
    from sqlalchemy import func

    return {
        table.__tablename__: db.scalar(select(func.count()).select_from(table)) or 0
        for table in _tables_in_delete_order()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Neev application database.")
    parser.add_argument("--reset", action="store_true", help="Delete every row first.")
    args = parser.parse_args()
    for table, count in seed(reset=args.reset).items():
        print(f"{table:16} {count}")
