"""Mappers are the only presentation-aware layer. These tests pin the two
properties that keep them from leaking: no formatted money, and grouping/order
taken from the mockups rather than recomputed."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

def captured(loan_id: str = "1001"):
    """The captured run's own figures, read rather than transcribed.

    These used to be numbers from the mockups. The fixtures are recorded live
    runs now, so a literal would break on every re-capture and prove nothing.
    """
    from app.fixtures.loader import load_pipeline_output

    return load_pipeline_output(loan_id)



from app.db import models
from app.db.seed import seed
from app.db.session import SessionLocal, init_db
from app.fixtures.loader import load_pipeline_output
from app.mappers.boq import QUESTIONS_SHOWN, _questions, to_boq_review
from app.mappers.portfolio import to_portfolio
from app.mappers.tranche import to_tranche_decision


def _review(loan, revision=None):
    """to_boq_review is pure; the test plays the caller and sources its inputs."""
    output = load_pipeline_output(loan.id)
    return to_boq_review(
        loan, revision or loan.revisions[-1], output.cost_estimate, output.payment_schedule
    )


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
        view = _review(loan, revision)

    # a number, not "₹28,47,930"
    assert view.cards[0].value == captured().boq_findings.boq_total
    for card in view.cards:
        assert not isinstance(card.value, str) or card.value_kind == "text"


def test_flag_groups_lead_with_findings_and_withhold_what_we_could_not_check():
    """Order is editorial, and the editorial point is what a reader sees first.

    Was the mockup's work-section order, then finding-type groups with "no
    benchmark" last. A captured run raises one UNBENCHMARKED flag per line it
    could not price -- twelve on loan 1001, against three real rate outliers --
    so they are counted rather than listed: they are gaps in our benchmark
    table, not findings against the contractor, and a table that mixes the two
    reads as an alarm nobody can act on.
    """
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        view = _review(loan)

    names = [g.name for g in view.groups]
    assert names[0] == "RATES ABOVE BENCHMARK"
    assert "NO BENCHMARK TO COMPARE AGAINST" not in names
    assert "OTHER" not in names, "every flag type must have a home"

    # Withheld, not lost: the count is on the view and the card agrees with the
    # rows, which is the property the group order exists to protect.
    assert view.unbenchmarked_count > 0
    flags_card = next(c for c in view.cards if c.label == "FLAGS RAISED")
    assert flags_card.value == sum(len(g.items) for g in view.groups)


def test_the_questions_panel_is_capped_and_renumbered():
    """Twenty-six questions is a list nobody sends.

    A captured run writes one question per flag. The panel's deliverable is a
    WhatsApp message, so it carries at most eight and says how many it held
    back. Numbers are the panel's own 1..n, not the stored row numbers, so a
    capped list never shows "1, 2, 5".
    """
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        view = _review(loan)

    assert 0 < len(view.questions) <= QUESTIONS_SHOWN
    assert [q.number for q in view.questions] == list(range(1, len(view.questions) + 1))
    assert view.questions_withheld == 0 or len(view.questions) == QUESTIONS_SHOWN


def test_questions_rank_by_what_they_cost_and_never_empty_a_hand_written_list():
    """Rate outliers first, vague specs last, and the cap applied after ranking.

    Unit-level because the seeded revision's four questions are hand-authored
    (they match no flag text), which is the other case this pins: a list that
    cannot be ranked is kept whole rather than silently emptied.
    """
    def question(number, text):
        return SimpleNamespace(number=number, text=text, status="draft")

    def flag(type_, text):
        return SimpleNamespace(type=type_, question=text)

    # Deliberately stored worst-first-last: ranking must beat row order.
    stored = [question(n, f"q{n}") for n in range(1, 4)]
    findings = [
        flag("UNDERSPECIFIED", "q1"),
        flag("MISSING_SCOPE", "q2"),
        flag("RATE_OUTLIER", "q3"),
    ]
    ranked, withheld = _questions(SimpleNamespace(questions=stored), findings)
    assert [q.text for q in ranked] == ["q3", "q2", "q1"]
    assert withheld == 0

    # A question whose only flag was withheld goes with it.
    ranked, _ = _questions(SimpleNamespace(questions=stored), findings[1:])
    assert [q.text for q in ranked] == ["q3", "q2"]

    # And nothing matching at all keeps the authored list, in its own order.
    ranked, withheld = _questions(SimpleNamespace(questions=stored), [])
    assert [q.text for q in ranked] == ["q1", "q2", "q3"]
    assert withheld == 0

    # The cap bites after ranking, not before.
    many = [question(n, f"m{n}") for n in range(1, 12)]
    ranked, withheld = _questions(
        SimpleNamespace(questions=many),
        [flag("UNDERSPECIFIED", f"m{n}") for n in range(1, 11)] + [flag("RATE_OUTLIER", "m11")],
    )
    assert len(ranked) == QUESTIONS_SHOWN and withheld == 3
    assert ranked[0].text == "m11"


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
        view = _review(loan)
    assert view.gst_stated is False
