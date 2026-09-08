from app.db import models
from app.mappers.sanction import to_sanction_check
from app.schemas.pipeline import CostEstimate, CostSection


def test_section_delta_is_derived_and_underprovision_is_not_a_saving():
    section = CostSection(name="RCC", quoted=100000, market=200000, delta=-100000)
    estimate = CostEstimate(expected_total_cost=1500000, completed_value_estimate=2000000,
                            sections=[section])
    loan = models.Loan(id="test", sanctioned=1000000, locality="Test")
    revision = models.BoqRevision(boq_total=1200000, flags=[models.Flag(type="RATE_OUTLIER")])
    view = to_sanction_check(loan, revision, estimate)
    assert view.sections[0].delta == 100000
    assert view.sections[0].tone == "danger"
    assert view.options[0].saves_label == "reduces the quote"


def test_missing_quote_cannot_be_advertised_as_a_saving():
    section = CostSection(name="Unknown", market=200000, delta=-100000)
    estimate = CostEstimate(expected_total_cost=1500000, completed_value_estimate=2000000,
                            sections=[section])
    loan = models.Loan(id="test", sanctioned=1000000, locality="Test")
    revision = models.BoqRevision(boq_total=1200000, flags=[models.Flag(type="RATE_OUTLIER")])
    view = to_sanction_check(loan, revision, estimate)
    assert view.options[0].saves_label == "reduces the quote"
    assert view.sections[0].tone == "neutral"


def test_equal_section_costs_are_neutral():
    section = CostSection(name="RCC", quoted=200000, market=200000, delta=0)
    estimate = CostEstimate(expected_total_cost=1500000, completed_value_estimate=2000000,
                            sections=[section])
    loan = models.Loan(id="test", sanctioned=1000000, locality="Test")
    revision = models.BoqRevision(boq_total=1200000, flags=[])
    assert to_sanction_check(loan, revision, estimate).sections[0].tone == "neutral"