"""The seeded book must match the screens exactly, and seeding twice must not
double the rows."""

import pytest
from sqlalchemy import func, select

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


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    import app.db.session as session_module

    session_module.reconfigure()
    init_db()
    yield
    get_settings.cache_clear()


def test_seed_creates_ten_loans():
    seed(reset=True)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(models.Loan)) == 10


def test_seed_is_idempotent():
    seed(reset=True)
    seed()
    seed()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(models.Loan)) == 10


def test_loan_1001_row_agrees_with_its_captured_run():
    seed(reset=True)
    with SessionLocal() as db:
        loan = db.scalar(select(models.Loan).where(models.Loan.id == "1001"))
        assert loan is not None
        assert loan.borrower_name == "Ravi Kumar"
        assert loan.locality == "Kompally"
        assert loan.sanctioned == 2800000
        assert loan.disbursed == 1800000
        # These follow the captured run, not portfolio_rows.json: the row and
        # the tranche screen it links to have to show the same number, and the
        # authored 1.29 no longer matches what the pipeline computes.
        risk = captured().risk_assessment
        assert loan.exposure_ratio == risk.exposure_ratio
        assert loan.cost_to_complete_gap == int(risk.cost_to_complete_gap)
        assert loan.recommendation == risk.recommendation


def test_flags_are_persisted_with_their_evidence_not_just_a_label():
    seed(reset=True)
    with SessionLocal() as db:
        flags = db.scalars(
            select(models.Flag).join(models.BoqRevision).where(models.BoqRevision.loan_id == "1001")
        ).all()
        assert len(flags) == len(captured().boq_findings.flags)
        assert all(flag.evidence and flag.question for flag in flags)
        rate_flags = [f for f in flags if f.type == "RATE_OUTLIER"]
        assert all(f.benchmark_rate is not None for f in rate_flags)


def test_closed_loans_have_a_null_gap_rather_than_zero():
    seed(reset=True)
    with SessionLocal() as db:
        loan = db.scalar(select(models.Loan).where(models.Loan.id == "1007"))
        assert loan is not None
        assert loan.cost_to_complete_gap is None
