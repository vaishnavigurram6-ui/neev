"""Backend tests never reach the network.

Any outbound socket connection fails the test rather than costing money. This
is the same discipline as tests/test_offline.py at the repo root, enforced
structurally instead of by convention.

The three route fixtures at the bottom are opt-in, not autouse: only the two
route modules ask for a seeded database and a live TestClient, and the mapper
and schema tests are faster without them.
"""

import socket

import pytest
from fastapi.testclient import TestClient


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
    monkeypatch.setenv("NEEV_DEMO_AUTH", "true")
    monkeypatch.delenv("NEEV_ALLOW_BILLED_CALLS", raising=False)
    from app.core.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# The demo accounts, as tests use them. Imported rather than retyped so a
# change to the account list is one edit, not forty.
OWNER_LOGIN = {"username": "ravi", "password": "neev-demo"}
OWNER_1002_LOGIN = {"username": "prasad", "password": "neev-demo"}
BANK_LOGIN = {"username": "officer", "password": "neev-demo"}


@pytest.fixture(autouse=True)
def _empty_job_registry():
    """The job registry is a module-level singleton, so jobs outlive the test
    that made them. That was harmless until the daily analysis cap started
    counting them: a test that uploads twice would then make the next test's
    first upload the third of the day, and the pair would pass or fail on
    alphabetical order."""
    from app.services.jobs import registry

    registry._jobs.clear()
    yield
    registry._jobs.clear()


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Point the engine at a throwaway file and seed the whole book into it."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path / "artifacts"))
    from app.core.settings import get_settings

    get_settings.cache_clear()
    import app.db.session as session_module

    session_module.reconfigure()
    from app.db.seed import seed
    from app.db.session import init_db

    init_db()
    seed(reset=True)
    yield
    # Re-point the engine at the default URL before the temp directory goes
    # away, so a later test cannot open a connection to a deleted file.
    get_settings.cache_clear()
    session_module.reconfigure()


@pytest.fixture
def instant_pipeline(monkeypatch):
    """Strip the fixture runner's pacing so the SSE tests stay sub-second."""
    import app.services.jobs as jobs_module
    from app.services.fixture_runner import FixtureRunner

    monkeypatch.setattr(jobs_module, "get_runner", lambda *a, **k: FixtureRunner(step_delay_s=0))


@pytest.fixture
def client(seeded_db):
    """A TestClient held open for the whole test.

    The context manager matters: it keeps one event loop alive across requests,
    so the asyncio.Task the job registry starts on the upload request is still
    on a live loop when the SSE request subscribes to it. Without it each
    request would get its own loop and the SSE subscriber would await an
    asyncio.Event belonging to a loop that had already closed.
    """
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def signed_client(client):
    """Explicitly authenticated route fixture; anonymous tests retain client."""
    assert client.post("/api/auth/session", json=BANK_LOGIN).status_code == 200
    return client
