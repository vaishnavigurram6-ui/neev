"""The inputs a live capture puts in the prompt, sourced per loan.

scripts/record_golden_run.py used to hardcode loan 1001's facts -- 1800 sqft,
Kompally, 28L sanctioned. Capturing 1002 with those would have produced a
genuine pipeline run against the wrong house, which is worse than authored data
because it looks real. These come from the committed data files, so a fresh
clone with no seeded database can still record a run.
"""

import pytest

from app.fixtures.loader import load_loan_facts


def test_the_golden_loan_carries_its_own_facts():
    facts = load_loan_facts("1001")
    assert facts["locality"] == "Kompally, Hyderabad"
    assert facts["built_up_sqft"] == 1800
    assert facts["sanctioned"] == 2_800_000
    assert facts["disbursed"] == 1_800_000
    assert facts["stage"] == "slab"


def test_the_clean_loan_does_not_inherit_the_golden_ones():
    facts = load_loan_facts("1002")
    assert facts["locality"] == "Kukatpally, Hyderabad"
    assert facts["built_up_sqft"] == 1650
    assert facts["sanctioned"] == 2_500_000
    assert facts["disbursed"] == 1_214_337


def test_the_stage_is_what_the_owner_claims_not_what_was_observed():
    """Loan 1003 is behind: tranche 3 is for slab, the inspection saw plinth.

    The prompt must carry the claim. Passing the observed stage would tell
    visual_inspector_agent the answer to the question it is asked.
    """
    assert load_loan_facts("1003")["stage"] == "slab"


def test_an_unknown_loan_is_refused_rather_than_defaulted():
    with pytest.raises(KeyError, match="9999"):
        load_loan_facts("9999")
