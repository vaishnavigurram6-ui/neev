"""A completed run must leave a stored revision behind.

Before this, FixtureRunner touched no database: a finished analysis left the loan
at whatever revision the seed gave it, and the eight loans with no seeded
revision redirected to a BoQ page that 404'd.
"""

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
from app.services.fixture_runner import FixtureRunner
from app.services.jobs import MAX_RETAINED_JOBS, Job, JobRegistry
from app.services.persistence import FLAG_GROUPS_BY_TYPE, store_revision
from app.services.runner import BoqAnalysisRequest


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'p.db'}")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    import app.db.session as session_module

    session_module.reconfigure()
    init_db()
    seed(reset=True)
    yield
    get_settings.cache_clear()


def _req(loan_id: str) -> BoqAnalysisRequest:
    return BoqAnalysisRequest(
        loan_id=loan_id, filename="revised_boq.pdf", content_type="application/pdf", size_bytes=2048
    )


def test_store_revision_appends_the_next_rev_with_its_raw_output():
    runner = FixtureRunner(step_delay_s=0)
    output = runner.final_output(_req("1001"))
    assert output is not None

    with SessionLocal() as db:
        before = len(db.get(models.Loan, "1001").revisions)
        revision = store_revision(db, "1001", output, source_filename="revised_boq.pdf")

    assert revision.rev == before + 1
    assert revision.raw_output, "raw_output is what analysis.py reads first"
    assert revision.boq_total == captured().boq_findings.boq_total
    assert revision.pipeline_mode == "fixture"

    with SessionLocal() as db:
        stored = db.get(models.BoqRevision, revision.id)
        assert len(stored.flags) == len(captured().boq_findings.flags)
        # Groups come from the flag's type now, not a hand-written item map,
        # so every stored group must be one the mapper knows how to order.
        assert {f.group_name for f in stored.flags} <= set(
            FLAG_GROUPS_BY_TYPE.values()
        )
        assert "OTHER" not in {f.group_name for f in stored.flags}


def test_a_loan_the_fixture_does_not_cover_stores_nothing():
    """Better an empty state than loan 1001's figures under another borrower's
    name.

    All ten seeded loans now have a recorded run, so the uncovered case needs a
    loan id that is not one of them — which is also the realistic shape of the
    bug this guards against: a request arriving for a loan nobody analysed.
    """
    assert FixtureRunner(step_delay_s=0).final_output(_req("9999")) is None


async def test_driving_a_job_to_completion_persists_a_revision():
    registry = JobRegistry()
    job = registry.create(_req("1001"))
    task = registry._tasks[job.id]
    await task

    assert job.status == "done"
    with SessionLocal() as db:
        revisions = db.get(models.Loan, "1001").revisions
        assert len(revisions) == 2, "the run should have appended a revision"
        assert revisions[-1].raw_output


def test_registry_evicts_finished_jobs_but_never_a_running_one():
    registry = JobRegistry()
    for i in range(MAX_RETAINED_JOBS + 10):
        job = Job(id=f"done{i}", loan_id="1001", status="done")
        registry._jobs[job.id] = job
    running = Job(id="live", loan_id="1001", status="running")
    registry._jobs[running.id] = running

    registry._evict()

    assert len(registry._jobs) <= MAX_RETAINED_JOBS
    assert "live" in registry._jobs, "a running job must survive eviction"


def test_eviction_gives_up_rather_than_dropping_running_jobs():
    registry = JobRegistry()
    for i in range(MAX_RETAINED_JOBS + 5):
        job = Job(id=f"live{i}", loan_id="1001", status="running")
        registry._jobs[job.id] = job

    registry._evict()

    assert len(registry._jobs) == MAX_RETAINED_JOBS + 5
