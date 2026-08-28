"""Mappers are the only presentation-aware layer. These tests pin the two
properties that keep them from leaking: no formatted money, and grouping/order
taken from the mockups rather than recomputed."""

import pytest
from sqlalchemy import select

from app.db import models
from app.db.seed import seed
from app.db.session import SessionLocal, init_db
from app.mappers.boq import to_boq_review
from app.mappers.portfolio import to_portfolio
from app.mappers.tranche import to_tranche_decision


@pytest.fixture(autouse=True)
def _seeded(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    import app.db.session as session_module

    session_module.reconfigure()
    init_db()
    seed(reset=True)
    yield
    get_settings.cache_clear()


def test_boq_review_carries_numbers_not_formatted_strings():
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        revision = loan.revisions[-1]
        view = to_boq_review(loan, revision)

    assert view.cards[0].value == 3200000  # a number, not "₹32,00,000"
    for card in view.cards:
        assert not isinstance(card.value, str) or card.value_kind == "text"


def test_flag_groups_follow_the_mockups_order():
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        view = to_boq_review(loan, loan.revisions[-1])
    assert [g.name for g in view.groups] == [
        "FOUNDATION & RCC",
        "STEEL",
        "PLASTERING — EXPECTED BUT ABSENT",
        "FLOORING & ELECTRICAL",
    ]


def test_portfolio_preserves_the_designs_exposure_descending_order():
    with SessionLocal() as db:
        loans = db.scalars(select(models.Loan).order_by(models.Loan.hotlist_rank)).all()
        view = to_portfolio(list(loans))
    assert [row.loan_id for row in view.rows][:4] == ["1003", "1004", "1001", "1009"]


def test_every_portfolio_row_has_its_own_drill_in_href():
    # The prototype gives only loan 1001 a real href; spec 7.4 fixes that.
    with SessionLocal() as db:
        loans = db.scalars(select(models.Loan).order_by(models.Loan.hotlist_rank)).all()
        view = to_portfolio(list(loans))
    hrefs = {row.loan_id: row.href for row in view.rows}
    assert len(set(hrefs.values())) == len(hrefs)
    assert all(row.loan_id in row.href for row in view.rows)


def test_closed_loans_render_as_text_not_a_zero_gap():
    with SessionLocal() as db:
        loans = db.scalars(select(models.Loan).order_by(models.Loan.hotlist_rank)).all()
        view = to_portfolio(list(loans))
    closed = next(row for row in view.rows if row.loan_id == "1007")
    assert closed.gap is None
    assert closed.gap_note == "closed"


def test_escalate_is_never_rendered_as_on_track():
    # RiskAssessment.recommendation includes ESCALATE. Falling through to the
    # RELEASE default would paint an escalated loan green.
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        loan.recommendation = "ESCALATE"
        view = to_portfolio([loan])
    assert view.rows[0].action_label == "ESCALATE"
    assert view.rows[0].tone == "danger"


def test_request_amount_excludes_the_tranche_being_decided():
    # `paid` must not contain the tranche under review: it would then be its own
    # predecessor, zeroing the request and printing "T3 + T3" in the math table.
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        t3 = next(t for t in loan.tranches if t.number == 3)
        view = to_tranche_decision(loan, t3)
    assert view.request_amount == 600000
    assert view.math[0].calc == "T1 + T2 + T3"


def test_request_amount_is_right_even_when_the_tranche_is_already_paid():
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1002")
        t3 = next(t for t in loan.tranches if t.number == 3)
        t2 = next(t for t in loan.tranches if t.number == 2)
        assert t3.status == "paid"  # the case that used to return 0
        view = to_tranche_decision(loan, t3)
    assert view.request_amount == t3.disbursed_cum - t2.disbursed_cum
    assert view.math[0].calc == "T1 + T2 + T3"


def test_undefined_exposure_is_not_rendered_as_a_pass():
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        t3 = next(t for t in loan.tranches if t.number == 3)
        t3.exposure_ratio = None
        t3.exposure_undefined = True
        t3.cost_to_complete_gap = None
        view = to_tranche_decision(loan, t3)
    exposure = next(row for row in view.math if row.label == "Disbursement exposure")
    assert exposure.result == "—"
    assert exposure.result_kind == "text"
    assert exposure.tone == "danger"
    gap = next(row for row in view.math if row.label == "Cost-to-complete gap")
    assert gap.result == "—"
    assert gap.tone == "neutral"


def test_gst_stated_agrees_with_the_sanction_check_for_the_same_loan():
    # Loan 1001's Sanction Check adds an unpriced "GST provision" section, so
    # BoQ Review must not report GST as stated.
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        view = to_boq_review(loan, loan.revisions[-1])
    assert view.gst_stated is False
