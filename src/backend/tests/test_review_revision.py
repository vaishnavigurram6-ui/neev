from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import models
from app.db.session import SessionLocal
from app.fixtures.loader import load_pipeline_output
from app.services.persistence import store_revision
from app.services.runner import BoqAnalysisRequest
from tests.conftest import OWNER_LOGIN


def test_new_revision_questions_and_risk_replace_only_the_target_snapshot(signed_client):
    output = load_pipeline_output("1001").model_copy(deep=True)
    output.boq_findings.flags[0].question = "New revision-specific question"
    output.risk_assessment.exposure_ratio = 8.0
    request = BoqAnalysisRequest(loan_id="1001", filename="test.pdf", size_bytes=1,
        content_type="application/pdf", tranche_number=4)
    with SessionLocal() as db:
        store_revision(db, "1001", output, request=request)
    current = signed_client.get("/api/loans/1001/boq/latest").json()
    old = signed_client.get("/api/loans/1001/boq/rev/1").json()
    assert current["questions"][0]["text"] == "New revision-specific question"
    assert len(old["questions"]) == 4 and old["questions"][0]["status"] == "draft"
    assert signed_client.get("/api/loans/1001/tranches/4").json()["exposure"] == 8.0
    assert signed_client.post("/api/loans/1001/questions/send").json()["sent"] == len(current["questions"])
    assert signed_client.get("/api/loans/1001/boq/rev/1").json()["questions"][0]["status"] == "draft"


def test_all_rows_are_the_actual_document_items(signed_client):
    """The All view is the document, with only the red flags marked.

    A label on every row -- "Vague spec", "No benchmark", and the old "Not
    assessed" fallback -- left nothing standing out and read as though the whole
    contract were suspect. Only a `danger` flag marks a row here; the quieter
    findings are in the flagged table, which exists to list them.
    """
    view = signed_client.get("/api/loans/1001/boq/latest").json()
    rows = [item for group in view["all_groups"] for item in group["items"]]
    assert len(rows) == view["item_count"] == 40
    assert len({row["item"] for row in rows}) == 40

    marked = [row for row in rows if row["label"]]
    assert marked, "a contract with rate outliers must mark them here too"
    assert all(row["tone"] == "danger" for row in marked)
    assert all(row["note"] for row in marked), "a marked row says what is wrong"
    # And a quiet row claims nothing in either direction.
    quiet = [row for row in rows if not row["label"]]
    assert quiet and all(row["tone"] == "neutral" and row["note"] == "" for row in quiet)


@pytest.mark.parametrize("area,data,status", [(-1, b"%PDF-1.4\n%%EOF", 422),
    (0, b"%PDF-1.4\n%%EOF", 422), (1500, b"", 422), (1500, b"bad", 422),
    (1500, b"x" * (10 * 1024 * 1024 + 1), 413)])
def test_invalid_boq_inputs_are_rejected(signed_client, area, data, status):
    assert signed_client.post("/api/loans/1001/boq", data={"built_up_sqft": area},
        files={"file": ("test.pdf", data, "application/pdf")}).status_code == status


def test_boq_artifact_survives_success(signed_client, instant_pipeline):
    data = (Path(__file__).resolve().parents[3] / "fixtures/sample_boq.pdf").read_bytes()
    response = signed_client.post("/api/loans/1001/boq",
        files={"file": ("test.pdf", data, "application/pdf")})
    job = response.json()["job_id"]
    signed_client.get(f"/api/jobs/{job}/events")
    assert signed_client.get(f"/api/jobs/{job}").json()["status"] == "done"
    with SessionLocal() as db:
        revision = db.scalars(select(models.BoqRevision).order_by(models.BoqRevision.id.desc())).first()
        assert Path(revision.source_artifact).read_bytes() == data


def test_job_status_and_stream_enforce_owner_loan(client):
    from app.services.jobs import Job, registry
    registry._jobs["boundary-test"] = Job(id="boundary-test", loan_id="1002", status="done")
    try:
        client.post("/api/auth/session", json=OWNER_LOGIN)
        for path in ("/api/jobs/boundary-test", "/api/jobs/boundary-test/events"):
            assert client.get(path).status_code == 403
    finally:
        registry._jobs.pop("boundary-test")


def test_openapi_generator_refuses_unknown_shapes_and_tracks_current_schema():
    from scripts.export_openapi import ts_type, artifacts
    assert ts_type({"anyOf": [{"type": "number"}, {"type": "null"}]}) == "(number | null)"
    with pytest.raises(ValueError):
        ts_type({"not": {"type": "number"}})
    for path, content in artifacts().items():
        assert path.read_text() == content


def test_legacy_migration_is_repeatable_and_preserves_questions():
    from sqlalchemy import create_engine, text
    from app.db.migrations import upgrade

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE boq_revisions (id INTEGER PRIMARY KEY, loan_id TEXT)"))
        connection.execute(text("CREATE TABLE questions (id INTEGER PRIMARY KEY, loan_id TEXT, text TEXT)"))
        connection.execute(text("CREATE TABLE tranches (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO boq_revisions VALUES (1, '1001'), (2, '1001')"))
        connection.execute(text("INSERT INTO questions VALUES (1, '1001', 'Keep original question')"))
    upgrade(engine)
    upgrade(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT text, revision_id FROM questions")).one() == (
            "Keep original question", 1)
        assert connection.execute(text("SELECT COUNT(*) FROM boq_revisions")).scalar() == 2
    engine.dispose()

async def test_a_quiet_stream_writes_a_heartbeat():
    """A live run goes quiet for a long time, and a silent socket gets closed.

    The last three agents all fire after the final tool call — 93 seconds of
    silence on a measured run — so the stream writes an SSE comment rather than
    nothing. Fixture mode never pauses this long, which is why nothing needed
    it until the pipeline ran for real.
    """
    import asyncio

    from app.schemas.events import DoneEvent, PhaseEvent
    from app.services.jobs import Job, registry

    job = Job(id="heartbeat-test", loan_id="1001", status="running")
    registry._jobs[job.id] = job
    try:
        seen: list[object] = []
        heartbeats = 0

        async def read():
            nonlocal heartbeats
            async for event in registry.stream(job.id, heartbeat_s=0.02):
                if event is None:
                    heartbeats += 1
                    # Enough to prove the socket is being written to.
                    if heartbeats == 3:
                        job.publish(DoneEvent(redirect="/owner/loans/1001/boq"))
                    continue
                seen.append(event)

        job.publish(PhaseEvent(index=0, status="running", name="Reading the document"))
        await asyncio.wait_for(read(), timeout=5)

        assert heartbeats >= 3, "a quiet stream must keep writing"
        # And the heartbeats never displace real events, terminal one included.
        assert [type(e).__name__ for e in seen] == ["PhaseEvent", "DoneEvent"]
    finally:
        registry._jobs.pop(job.id, None)
