"""Per-phase history: what was claimed, what was seen, what was decided.

Build Progress and Tranche Decision both carry it, from one mapper, so the
owner's account of their build and the lender's audit trail cannot drift apart.
"""

import pytest

from app.db import models
from app.db.seed import seed
from app.db.session import SessionLocal, init_db
from app.mappers.history import to_phase_history


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'h.db'}")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    import app.db.session as session_module

    session_module.reconfigure()
    init_db()
    seed(reset=True)
    yield
    get_settings.cache_clear()


def _phases(loan_id="1001"):
    with SessionLocal() as db:
        return to_phase_history(db.get(models.Loan, loan_id))


def test_every_tranche_becomes_a_phase_in_order():
    phases = _phases()
    assert [p.tranche_number for p in phases] == [1, 2, 3, 4]
    assert [p.milestone for p in phases] == [
        "foundation",
        "plinth",
        "slab",
        "brickwork_roof",
    ]


def test_verified_value_is_monotonic_and_ends_at_the_frozen_figure():
    # Derived from the one figure already on screen: 13,90,000 verified at the
    # slab, which is 50% complete, implies a 27,80,000 base. Anything else would
    # contradict the Tranche Decision screen.
    verified = [p.verified_value for p in _phases()[:3]]
    assert all(v is not None for v in verified)
    assert verified == sorted(verified), "value in place cannot go backwards"
    assert verified[2] == 1390000


def test_released_amount_is_the_step_not_the_cumulative():
    # 6,00,000 each, not 6/12/18 lakh. Reporting the cumulative as "released"
    # would triple-count the first tranche by the third row.
    assert [p.released_amount for p in _phases()[:3]] == [600000, 600000, 600000]


def test_exposure_is_computed_at_each_phase_not_carried_from_today():
    phases = _phases()
    # Front-loaded payments mean exposure was worse early and improved as work
    # caught up. Showing today's 1.29 against every past phase would hide that.
    assert phases[0].exposure is not None
    assert phases[1].exposure > phases[2].exposure
    assert phases[2].exposure == 1.29


def test_the_phases_neev_did_not_watch_say_so_and_carry_no_evidence():
    """T1-T3 predate Neev's involvement: they were released with no photographs.

    Backfilling evidence and approvals there would show the bank releasing at
    1.73 with proof in hand, which is not what happened. The photo set the
    fixture does have was submitted with the T4 request, so it belongs to T4 --
    which is also where the Tranche Decision screen shows it.
    """
    phases = _phases()
    unwatched, watched = phases[:3], phases[3]
    assert all(p.photos == [] for p in unwatched)
    assert all(p.observed_by_neev is False for p in unwatched)
    assert watched.observed_by_neev is True
    assert watched.photos, "T4 is where Neev starts"


def test_the_pending_phase_is_marked_as_awaiting_a_decision():
    pending = _phases()[3]
    assert pending.status == "on_hold"
    assert pending.decision is None
    assert pending.recommendation == "HOLD"


def test_a_clean_loan_has_history_too():
    phases = _phases("1002")
    assert len(phases) >= 3
    assert all(p.milestone for p in phases)
