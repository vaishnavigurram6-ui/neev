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
    assert client.post("/api/auth/session", json={"role": "bank", "phone": "9999999999"}).status_code == 403


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