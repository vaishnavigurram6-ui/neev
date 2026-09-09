"""Regression checks for anonymous access, untrusted evidence and commit ordering."""
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.db import models
from app.api.routes.loans import UPLOAD_SLOT_PREFIX
from app.db.session import SessionLocal
from app.schemas.events import DoneEvent, ErrorEvent
from app.services.jobs import JobRegistry
from app.services.runner import BoqAnalysisRequest
from tests.conftest import BANK_LOGIN, OWNER_1002_LOGIN, OWNER_LOGIN


PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00"
    b"\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def image_bytes():
    out = BytesIO()
    Image.new("RGB", (2, 2)).save(out, "PNG")
    return out.getvalue()


@pytest.mark.parametrize("url", ["/api/loans/1001", "/api/portfolio", "/api/contractors",
    "/api/loans/1001/tranches/4", "/api/jobs/missing", "/api/jobs/missing/events"])
def test_anonymous_private_reads_are_rejected(client, url):
    assert client.get(url).status_code == 401


def test_demo_login_is_explicitly_gated(client, monkeypatch):
    from app.core.settings import get_settings
    monkeypatch.setenv("NEEV_DEMO_AUTH", "false")
    get_settings.cache_clear()
    assert client.post("/api/auth/session", json=BANK_LOGIN).status_code == 403


def test_forged_unsigned_session_is_rejected(client):
    client.cookies.set("neev_session", "bank:all:Attacker")
    assert client.get("/api/portfolio").status_code == 401


def test_milestone_keeps_claim_separate_and_retains_bytes(signed_client):
    response = signed_client.post("/api/loans/1001/milestones", data={"stage": "finishing"},
        files={"photos": ("site.png", image_bytes(), "image/png")})
    assert response.status_code == 200
    with SessionLocal() as db:
        tranche = next(t for t in db.get(models.Loan, "1001").tranches if t.number == 4)
        assert tranche.claimed_stage == "finishing"
        assert tranche.observed_stage == "slab"
        assert tranche.needs_human_review is True
        assert tranche.recommendation == "ESCALATE"
        # The uploaded row, not the seeded one: the seed now gives its evidence
        # rows real frames too, so "the first row with bytes" would pick the
        # golden case's own photograph and pass without proving anything.
        photo = next(p for p in tranche.photos if UPLOAD_SLOT_PREFIX in p.slot_key)
        assert Path(photo.stored_path).read_bytes() == image_bytes()


@pytest.mark.parametrize("data", [b"", b"not an image", b"\xff\xd8\xffcorrupt"])
def test_invalid_photo_is_rejected_without_evidence_rows(signed_client, data):
    with SessionLocal() as db:
        before = len(list(db.scalars(select(models.Photo))))
    result = signed_client.post("/api/loans/1001/milestones",
        files={"photos": ("fake.jpg", data, "image/jpeg")})
    assert result.status_code == 422
    with SessionLocal() as db:
        assert len(list(db.scalars(select(models.Photo)))) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["save", "missing"])
async def test_job_failure_is_visible_before_terminal_event(monkeypatch, failure):
    import app.services.jobs as module
    from app.services.fixture_runner import FixtureRunner
    runner = FixtureRunner(step_delay_s=0)
    if failure == "missing":
        monkeypatch.setattr(runner, "final_output", lambda req: None)
    monkeypatch.setattr(module, "get_runner", lambda: runner)
    registry = JobRegistry()
    if failure == "save":
        def fail(*args):
            raise RuntimeError("private database parameters must not reach clients")
        monkeypatch.setattr(registry, "_persist", fail)
    job = registry.create(BoqAnalysisRequest(loan_id="1001", filename="test.pdf",
        content_type="application/pdf", size_bytes=1))
    events = [event async for event in registry.stream(job.id)]
    assert job.status == "error"
    assert isinstance(events[-2], ErrorEvent) and isinstance(events[-1], DoneEvent)
    assert sum(isinstance(e, DoneEvent) for e in events) == 1
    assert "private database" not in job.error


def test_decision_events_are_append_only_and_retries_are_deduplicated(signed_client):
    url = "/api/loans/1001/tranches/4/decision"
    first = signed_client.post(url, json={"action": "HOLD"}, headers={"Idempotency-Key": "a"})
    again = signed_client.post(url, json={"action": "HOLD"}, headers={"Idempotency-Key": "a"})
    assert first.json() == again.json()
    assert signed_client.post(url, json={"action": "ESCALATE"}, headers={"Idempotency-Key": "a"}).status_code == 409
    assert signed_client.post(url, json={"action": "ESCALATE"}, headers={"Idempotency-Key": "b"}).status_code == 200
    with SessionLocal() as db:
        assert [e.action for e in db.scalars(select(models.DecisionEvent).order_by(models.DecisionEvent.id))] == ["HOLD", "ESCALATE"]

def test_the_daily_cap_stops_a_public_url_spending_without_limit(signed_client, monkeypatch):
    """A live analysis costs real money and the deployed demo is a public URL
    whose sign-in accepts any ten-digit number. On the Gemini free tier Google's
    own 20-a-day cap is the backstop; on the paid tier there is none.

    The cap counts analyses STARTED, because a run that fails halfway has
    already paid for the agents that answered.
    """
    from app.core.settings import get_settings

    monkeypatch.setenv("NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY", "2")
    get_settings.cache_clear()
    try:
        pdf = {"file": ("boq.pdf", b"%PDF-1.4 test\n%%EOF", "application/pdf")}
        assert signed_client.post("/api/loans/1001/boq", files=pdf).status_code == 200
        assert signed_client.post("/api/loans/1001/boq", files=pdf).status_code == 200

        refused = signed_client.post("/api/loans/1001/boq", files=pdf)
        assert refused.status_code == 429
        # Copy a borrower can act on, and no mention of quotas or credits.
        detail = refused.json()["detail"]
        assert "try again tomorrow" in detail.lower()
        for leak in ("quota", "credit", "Gemini", "429"):
            assert leak.lower() not in detail.lower()
    finally:
        get_settings.cache_clear()


def test_the_cap_is_per_loan_not_global(signed_client, monkeypatch):
    """One borrower exhausting their own allowance must not lock out the book."""
    from app.core.settings import get_settings

    monkeypatch.setenv("NEEV_MAX_ANALYSES_PER_LOAN_PER_DAY", "1")
    monkeypatch.setenv("NEEV_MAX_ANALYSES_PER_DAY", "50")
    get_settings.cache_clear()
    try:
        pdf = {"file": ("boq.pdf", b"%PDF-1.4 test\n%%EOF", "application/pdf")}
        assert signed_client.post("/api/loans/1001/boq", files=pdf).status_code == 200
        assert signed_client.post("/api/loans/1001/boq", files=pdf).status_code == 429

        # A lender's session reads the whole book, so switch to 1002's owner.
        signed_client.cookies.clear()
        signed_client.post(
            "/api/auth/session",
            json=OWNER_1002_LOGIN,
        )
        assert signed_client.post("/api/loans/1002/boq", files=pdf).status_code == 200
    finally:
        get_settings.cache_clear()


async def test_reporting_photos_runs_the_inspector_and_the_risk_agent(client, instant_pipeline):
    """The product's second promise: "photos verify each payment".

    For a while the photo path kept none of it — it stored the frames, set
    ESCALATE by hand, and never asked the model anything. Reporting a milestone
    now runs the same two agents a full BoQ analysis uses, and what they read is
    written to the tranche the photographs were evidence for.
    """
    from app.db import models
    from app.db.session import SessionLocal
    from app.services.jobs import registry

    client.post("/api/auth/session", json=OWNER_LOGIN)
    with SessionLocal() as db:
        before = next(t for t in db.get(models.Loan, "1001").tranches if t.number == 4)
        # Wipe the seeded reading so a stale value cannot make this pass.
        before.observed_stage = None
        before.confidence = None
        before.exposure_ratio = None
        db.commit()

    response = client.post(
        "/api/loans/1001/milestones",
        data={"stage": "brickwork_roof"},
        files=[("photos", ("slab.png", PNG, "image/png"))],
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    assert job_id, "reporting a milestone must start an inspection"

    # Drain the stream, which is what waits for the inspection to finish.
    client.get(f"/api/jobs/{job_id}/events")
    assert registry.get(job_id).status == "done", registry.get(job_id).error

    with SessionLocal() as db:
        after = next(t for t in db.get(models.Loan, "1001").tranches if t.number == 4)
        # The agents' reading, not the hardcoded escalation.
        assert after.observed_stage == "slab"
        assert after.confidence is not None
        assert after.exposure_ratio is not None
        assert after.recommendation in ("RELEASE", "HOLD", "ESCALATE", "INSPECT")
        # Derived from the inspection rather than left stale. Not asserted
        # against the stage this test claimed: fixture mode replays a recording
        # made against the claim of the day, so only a live run can judge a
        # claim it has not seen before.
        from app.fixtures.loader import load_pipeline_output

        recorded = load_pipeline_output("1001").inspection_result
        assert db.get(models.Loan, "1001").behind_schedule is (not recorded.matches_claim)


async def test_a_milestone_with_no_stored_analysis_stays_under_review(client):
    """There is nothing to price a draw against until a BoQ has been analysed,
    so the inspection is skipped rather than run on invented figures — and the
    tranche keeps the one honest answer, which is that a human should look."""
    from app.db import models
    from app.db.session import SessionLocal

    client.post(
        "/api/auth/session",
        json=OWNER_1002_LOGIN,
    )
    with SessionLocal() as db:
        loan = db.get(models.Loan, "1002")
        for revision in list(loan.revisions):
            db.delete(revision)
        db.commit()

    response = client.post(
        "/api/loans/1002/milestones",
        files=[("photos", ("slab.png", PNG, "image/png"))],
    )
    assert response.status_code == 200, response.text
    assert response.json()["job_id"] is None

    with SessionLocal() as db:
        tranche = next(
            t for t in db.get(models.Loan, "1002").tranches if t.needs_human_review
        )
        assert tranche.recommendation == "ESCALATE"
