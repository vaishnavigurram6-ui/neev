"""The factory is the only place that reads NEEV_MODE. These tests prove that
fixture mode is what you get by default, and that reaching for live mode without
the explicit opt-in fails loudly instead of billing."""

import pytest

from app.core.settings import BilledCallsNotPermitted, Settings
from app.services.fixture_runner import FixtureRunner
from app.services.runner import get_runner


def test_default_mode_returns_the_fixture_runner():
    assert isinstance(get_runner(Settings()), FixtureRunner)


def test_typo_in_mode_still_returns_the_fixture_runner():
    assert isinstance(get_runner(Settings(neev_mode="LIVE_ish")), FixtureRunner)


def test_live_mode_without_the_opt_in_raises_naming_the_variable():
    with pytest.raises(BilledCallsNotPermitted) as excinfo:
        get_runner(Settings(neev_mode="live"))
    assert "NEEV_ALLOW_BILLED_CALLS" in str(excinfo.value)


def test_live_runner_module_imports_without_the_adk_installed():
    # The ADK import lives inside the method body, so importing the module is
    # safe in a venv that has no google-adk — which the backend venv does not.
    import app.services.live_runner as live

    assert hasattr(live, "AdkPipelineRunner")
