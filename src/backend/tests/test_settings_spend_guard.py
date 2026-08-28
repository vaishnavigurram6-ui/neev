"""The spend fence. These tests are the reason a NEEV_MODE typo can never
silently start billing."""

import pytest

from app.core.settings import (
    BilledCallsNotPermitted,
    Settings,
    assert_billed_calls_permitted,
)


def test_mode_defaults_to_fixture_when_unset():
    assert Settings().neev_mode == "fixture"


def test_unrecognized_mode_falls_back_to_fixture(monkeypatch):
    monkeypatch.setenv("NEEV_MODE", "liv")  # a typo, not a mode
    assert Settings().neev_mode == "fixture"


def test_live_mode_is_accepted_as_a_value():
    # Selecting live mode is allowed; ACTING on it is what is fenced.
    assert Settings(neev_mode="live").neev_mode == "live"


def test_billed_calls_are_refused_by_default():
    with pytest.raises(BilledCallsNotPermitted) as excinfo:
        assert_billed_calls_permitted(Settings(neev_mode="live"))
    assert "NEEV_ALLOW_BILLED_CALLS" in str(excinfo.value)


def test_billed_calls_permitted_only_with_the_explicit_opt_in():
    settings = Settings(neev_mode="live", neev_allow_billed_calls=True)
    assert_billed_calls_permitted(settings) is None
