"""The whole demo, end to end, in fixture mode with no credentials and no network.

This is the acceptance test for the build: it walks the four demo beats in order
through the real HTTP surface, and it asserts the dry run structurally rather
than trusting it -- there is no `google` namespace in this venv at all, so no
billed call is reachable from here.
"""

import importlib.util
import json

def captured(loan_id: str = "1001"):
    """The captured run's own figures, read rather than transcribed.

    These used to be numbers from the mockups. The fixtures are recorded live
    runs now, so a literal would break on every re-capture and prove nothing.
    """
    from app.fixtures.loader import load_pipeline_output

    return load_pipeline_output(loan_id)



import pytest
from sqlalchemy import select

from app.db import models
from app.db.session import SessionLocal


def test_the_backend_cannot_make_a_billed_call():
    """The strongest available proof, and the reason it is first.

    The backend declares no Google dependency, so the libraries that would talk
    to Gemini or BigQuery are not installed. This is not a policy check that
    could be forgotten -- it is an absence.
    """
    for module in ("google", "google.adk", "google.genai", "google.cloud.bigquery"):
        try:
            found = importlib.util.find_spec(module) is not None
        except ModuleNotFoundError:
            found = False
        assert not found, f"{module} is importable in the backend venv"


def test_fixture_mode_is_what_you_get_without_asking():
    from app.core.settings import Settings
    from app.services.fixture_runner import FixtureRunner
    from app.services.runner import get_runner

    assert Settings().neev_mode == "fixture"
    assert isinstance(get_runner(Settings()), FixtureRunner)


@pytest.mark.parametrize("beat", ["all"])
def test_the_golden_path(client, beat):
    # ---- Beat 1: the owner uploads a BoQ and watches it being read -----------
    session = client.post(
        "/api/auth/session",
        json={"role": "owner", "phone": "9999999999", "loan_id": "1001"},
    )
    assert session.status_code == 200, session.text

    me = client.get("/api/me").json()
    assert me["role"] == "owner" and me["loan_id"] == "1001"

    with open("../../fixtures/sample_boq.pdf", "rb") as handle:
        upload = client.post(
            "/api/loans/1001/boq",
            files={"file": ("sample_boq.pdf", handle.read(), "application/pdf")},
        )
    assert upload.status_code == 200, upload.text
    job_id = upload.json()["job_id"]

    events = _drain(client, job_id)
    kinds = [e["type"] for e in events]
    assert kinds[-1] == "done", kinds
    assert "error" not in kinds
    assert kinds.count("phase") == 10, "five phases, each running then done"
    assert kinds.count("finding") == 4
    assert events[-1]["redirect"] == "/owner/loans/1001/boq"

    # ---- Beat 2: the contract, checked line by line --------------------------
    boq = client.get("/api/loans/1001/boq/latest").json()
    out = captured()
    assert boq["boq_total"] == out.boq_findings.boq_total
    # Every flag is accounted for: a finding lands in a group, and an
    # UNBENCHMARKED gap in our own benchmark table is counted instead of listed.
    # Nothing is dropped on the way to a screen.
    assert (
        sum(len(g["items"]) for g in boq["groups"]) + boq["unbenchmarked_count"]
        == len(out.boq_findings.flags)
    )
    assert boq["groups"], "a flagged BoQ must render at least one group"
    assert boq["pct_before_slab"] == out.boq_findings.payment_pct_before_slab
    # The run that just finished was stored, so the redirect above resolves.
    assert boq["rev"] >= 2, "a completed analysis must leave a revision behind"

    sent = client.post("/api/loans/1001/questions/send")
    assert sent.status_code == 200 and sent.json()["sent"] == len(boq["questions"])

    # ---- Beat 3: will the sanction actually finish the house? ----------------
    sanction = client.get("/api/loans/1001/sanction-check").json()
    assert sanction["shortfall"] == pytest.approx(
        captured().cost_estimate.expected_total_cost - 2800000
    )
    assert [round(b["value"]) for b in sanction["bars"]] == [
        round(out.boq_findings.boq_total),
        round(out.cost_estimate.expected_total_cost),
        2800000,
    ]
    assert len(sanction["sections"]) == 5
    # Two rows have no quoted figure and must say so rather than print zero.
    notes = [s["quoted_note"] for s in sanction["sections"] if s["quoted"] is None]
    assert "not stated" in notes

    # ---- Beat 4: the bank holds a tranche, with evidence ---------------------
    assert client.post(
        "/api/auth/session", json={"role": "bank", "phone": "8888888888", "loan_id": "1001"}
    ).status_code == 200

    portfolio = client.get("/api/portfolio").json()
    assert len(portfolio["rows"]) == 10
    assert [r["loan_id"] for r in portfolio["rows"]][:3] == ["1003", "1004", "1001"]
    # Every row drills in somewhere real, and to its own loan.
    assert len({r["href"] for r in portfolio["rows"]}) == 10
    assert all(r["loan_id"] in r["href"] for r in portfolio["rows"])

    golden = next(r for r in portfolio["rows"] if r["loan_id"] == "1001")
    tranche_no = int(golden["tranche"])
    assert tranche_no == 4, "the decision is pending on T4, not the already-paid T3"

    decision_view = client.get(f"/api/loans/1001/tranches/{tranche_no}").json()
    assert decision_view["exposure"] == captured().risk_assessment.exposure_ratio
    assert decision_view["exposure_undefined"] is False
    assert decision_view["recommendation"] == "HOLD"
    assert decision_view["request_amount"] == 440000
    risk = captured().risk_assessment
    math = {row["label"]: row["result"] for row in decision_view["math"]}
    assert math["Disbursed so far"] == 1800000
    assert math["Verified value in place"] == risk.verified_value
    assert math["Cost to complete"] == (risk.cost_to_complete or "—")
    assert math["Cost-to-complete gap"] == risk.cost_to_complete_gap
    assert decision_view["photos"], "a verified tranche must show its evidence"
    assert decision_view["owner_view"] and decision_view["officer_view"]

    held = client.post(
        f"/api/loans/1001/tranches/{tranche_no}/decision",
        json={"action": "HOLD", "note": "Exposure over 1.0; questions still open."},
    )
    assert held.status_code == 200, held.text

    # ---- The evidence trail the designs promise is actually written ----------
    with SessionLocal() as db:
        row = db.scalar(
            select(models.Decision)
            .join(models.Tranche)
            .where(models.Tranche.loan_id == "1001", models.Tranche.number == tranche_no)
        )
        assert row is not None
        assert row.action == "HOLD"
        assert row.evidence_snapshot, "a decision with no evidence trail is not auditable"
        snapshot = json.loads(row.evidence_snapshot)
        assert snapshot, "the snapshot must carry the state the decision was made on"


def test_a_second_decision_updates_rather_than_duplicating(client):
    client.post(
        "/api/auth/session", json={"role": "bank", "phone": "8888888888", "loan_id": "1001"}
    )
    for action in ("HOLD", "ESCALATE"):
        assert client.post(
            f"/api/loans/1001/tranches/4/decision", json={"action": action}
        ).status_code == 200

    with SessionLocal() as db:
        rows = db.scalars(
            select(models.Decision)
            .join(models.Tranche)
            .where(models.Tranche.loan_id == "1001", models.Tranche.number == 4)
        ).all()
    assert len(rows) == 1
    assert rows[0].action == "ESCALATE"


def test_an_owner_cannot_release_their_own_tranche(client):
    """The premise of the product is that the bank verifies before money moves."""
    client.post(
        "/api/auth/session", json={"role": "owner", "phone": "9999999999", "loan_id": "1001"}
    )
    refused = client.post("/api/loans/1001/tranches/4/decision", json={"action": "RELEASE"})
    assert refused.status_code == 403, refused.text


def _drain(client, job_id: str) -> list[dict]:
    """Read the SSE stream to its terminal event."""
    events: list[dict] = []
    with client.stream("GET", f"/api/jobs/{job_id}/events") as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: ") :])
            events.append(event)
            if event["type"] == "done":
                break
    return events
