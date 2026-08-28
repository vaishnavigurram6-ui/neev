"""Backend tests never reach the network.

Any outbound socket connection fails the test rather than costing money. This
is the same discipline as tests/test_offline.py at the repo root, enforced
structurally instead of by convention.
"""

import socket

import pytest


class NetworkAccessDenied(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    def _denied(*args, **kwargs):
        raise NetworkAccessDenied(
            "A backend test attempted an outbound network connection. "
            "The dry run forbids it — stub the call instead."
        )

    monkeypatch.setattr(socket.socket, "connect", _denied)
    monkeypatch.setattr(socket.socket, "connect_ex", _denied)
    monkeypatch.setattr(socket, "create_connection", _denied)


@pytest.fixture(autouse=True)
def _force_fixture_mode(monkeypatch):
    monkeypatch.setenv("NEEV_MODE", "fixture")
    monkeypatch.delenv("NEEV_ALLOW_BILLED_CALLS", raising=False)
    from app.core.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
