"""Bank-facing HTTP surface: the hotlist, one tranche decision, and contractors.

The hotlist's row order is the design's, not the SQL's, so it is asserted
literally. Decisions are asserted idempotent because a credit officer
double-clicking "Hold" must not write two entries into the loan file.
"""

# `client` and `seeded_db` come from tests/conftest.py.
import pytest
from tests.conftest import BANK_LOGIN, OWNER_LOGIN


@pytest.fixture(autouse=True)
def _authenticated_reads(client):
    _as_officer(client)

BANK_LOGIN = BANK_LOGIN


def _as_officer(client):
    """Deciding a tranche needs a real lender session; reading does not."""
    assert client.post("/api/auth/session", json=BANK_LOGIN).status_code == 200


WORST_FIRST = ["1004", "1009", "1001"]  # the three over-exposed loans, in order


# ---------------------------------------------------------------- portfolio


def test_portfolio_returns_the_whole_book_worst_first(client):
    """Was the design's authored order, which recorded runs made untrue. The
    top of the book is what a lender opens on, so that much is pinned; the rest
    is covered by test_the_book_is_ranked_worst_first as a property."""
    body = client.get("/api/portfolio").json()
    ids = [row["loan_id"] for row in body["rows"]]
    assert len(ids) == 10
    assert ids[:3] == WORST_FIRST
    assert body["cards"][0]["value"] == 10


def test_every_row_links_to_its_own_loan(client):
    rows = client.get("/api/portfolio").json()["rows"]
    hrefs = [row["href"] for row in rows]
    assert len(set(hrefs)) == len(hrefs)
    for row in rows:
        assert row["loan_id"] in row["href"]
        assert row["href"] != "#"


def test_needs_action_selects_everything_that_is_not_on_track(client):
    body = client.get("/api/portfolio", params={"filter": "needs_action"}).json()
    labels = {row["action_label"] for row in body["rows"]}
    assert labels == {"ESCALATE", "HOLD", "INSPECT"}
    assert "ON TRACK" not in labels
    # The cards describe the whole book, so filtering rows must not move them.
    assert body["cards"][0]["value"] == 10
    # Asserted as a property rather than a list of ids: every loan carries a
    # recorded run now, so the labels follow what the agents concluded and a
    # re-record would rewrite a hardcoded list without changing the rule.
    everything = client.get("/api/portfolio").json()["rows"]
    assert len(body["rows"]) == sum(
        1 for row in everything if row["action_label"] != "ON TRACK"
    )


def test_the_book_is_ranked_worst_first(client):
    """The table is headed "ranked by disbursement exposure", so it has to be.

    The order used to be preserved from the design's own authored sequence,
    which stopped agreeing with the column the moment recorded runs replaced
    the authored exposures: 1003 sat at the top with 0.87 and ON TRACK, above
    1004 at 1.71 and ESCALATE.
    """
    rows = client.get("/api/portfolio").json()["rows"]
    measured = [row["exposure"] for row in rows if row["exposure"] is not None]
    assert measured == sorted(measured, reverse=True)
    # A loan with no exposure measured nothing, which is not the same as being
    # the safest — it sorts last, not first.
    unmeasured_from = next(
        i for i, row in enumerate(rows) if row["exposure"] is None
    )
    assert all(row["exposure"] is None for row in rows[unmeasured_from:])


def test_on_track_is_the_complement(client):
    rows = client.get("/api/portfolio", params={"filter": "on_track"}).json()["rows"]
    assert rows, "the book cannot be entirely in trouble"
    assert {row["action_label"] for row in rows} == {"ON TRACK"}
    needs = client.get("/api/portfolio", params={"filter": "needs_action"}).json()["rows"]
    everything = client.get("/api/portfolio").json()["rows"]
    assert len(rows) + len(needs) == len(everything)


def test_an_unknown_filter_is_rejected(client):
    assert client.get("/api/portfolio", params={"filter": "spicy"}).status_code == 422


def test_portfolio_money_is_numeric(client):
    for row in client.get("/api/portfolio").json()["rows"]:
        assert isinstance(row["disbursed"], (int, float))
        assert row["gap"] is None or isinstance(row["gap"], (int, float))


# ---------------------------------------------------------------- tranche


def test_the_golden_tranche_reports_the_mockups_figures(client):
    # The decision is pending on T4, not T3. T1-T3 are paid, which is the only
    # reading under which 18,00,000 disbursed adds up -- and it is what the
    # mockup's own gap row assumes: "(28,00,000 - 18,00,000) - 15,80,000".
    body = client.get("/api/loans/1001/tranches/4").json()
    assert body["borrower"] == "Ravi Kumar"
    assert body["tranche_number"] == 4
    assert body["request_amount"] == 440000  # 0.80 x 28,00,000 - 18,00,000
    risk = captured().risk_assessment
    assert body["exposure"] == risk.exposure_ratio
    assert body["recommendation"] == risk.recommendation
    assert body["recommendation_tone"] == "danger"
    math = {row["label"]: row["result"] for row in body["math"]}
    assert math["Disbursed so far"] == 1800000
    assert math["Verified value in place"] == risk.verified_value
    # cost_to_complete is optional and this run reported none, so the row shows
    # an em dash rather than a figure nobody computed.
    assert math["Cost to complete"] == (risk.cost_to_complete or "—")
    assert math["Cost-to-complete gap"] == risk.cost_to_complete_gap
    # One slot per evidence note the inspection reported; the captured run
    # wrote fewer notes than the mockup's three-photo grid assumed.
    assert body["photos"], "a verified tranche must show its evidence"
    assert body["owner_view"] and body["officer_view"]


def test_an_unknown_tranche_is_404(client):
    assert client.get("/api/loans/1001/tranches/99").status_code == 404


def test_a_tranche_on_an_unknown_loan_is_404(client):
    assert client.get("/api/loans/9999/tranches/1").status_code == 404


# ---------------------------------------------------------------- decision


def test_a_decision_persists_with_its_evidence_snapshot(client):
    _as_officer(client)
    response = client.post(
        "/api/loans/1001/tranches/3/decision",
        json={"action": "HOLD", "note": "Re-scope first."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action"] == "HOLD"
    assert body["decided_at"]

    from app.db import models
    from app.db.session import SessionLocal

def captured(loan_id: str = "1001"):
    """The captured run's own figures, read rather than transcribed."""
    from app.fixtures.loader import load_pipeline_output

    return load_pipeline_output(loan_id)



    with SessionLocal() as db:
        tranche = next(t for t in db.get(models.Loan, "1001").tranches if t.number == 3)
        decision = tranche.decision
        assert decision is not None
        assert decision.action == "HOLD"
        assert decision.note == "Re-scope first."
        snapshot = decision.evidence_snapshot
        assert snapshot and "exposure" in snapshot


def test_a_second_decision_updates_rather_than_duplicating(client):
    _as_officer(client)
    client.post("/api/loans/1001/tranches/3/decision", json={"action": "HOLD"})
    second = client.post(
        "/api/loans/1001/tranches/3/decision",
        json={"action": "ESCALATE", "note": "To committee."},
    )
    assert second.status_code == 200

    from sqlalchemy import func, select

    from app.db import models
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(models.Decision))
        assert count == 1
        decision = db.scalars(select(models.Decision)).one()
        assert decision.action == "ESCALATE"
        assert decision.note == "To committee."


def test_the_decision_response_reflects_the_latest_action(client):
    _as_officer(client)
    first = client.post("/api/loans/1001/tranches/3/decision", json={"action": "HOLD"})
    again = client.post("/api/loans/1001/tranches/3/decision", json={"action": "RELEASE"})
    assert first.json()["action"] == "HOLD"
    assert again.json()["action"] == "RELEASE"


def test_who_decided_comes_from_the_session_not_the_body(client):
    _as_officer(client)
    client.post(
        "/api/loans/1001/tranches/3/decision",
        json={"action": "HOLD", "decided_by": "Someone Else"},
    )

    from sqlalchemy import select

    from app.db import models
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        decision = db.scalars(select(models.Decision)).one()
        assert decision.decided_by == "Anita Mehta"


def test_an_unknown_action_is_rejected(client):
    _as_officer(client)
    response = client.post("/api/loans/1001/tranches/3/decision", json={"action": "YOLO"})
    assert response.status_code == 422


def test_a_decision_on_an_unknown_tranche_is_404(client):
    _as_officer(client)
    response = client.post("/api/loans/1001/tranches/99/decision", json={"action": "HOLD"})
    assert response.status_code == 404


# ---------------------------------------------------------------- contractors


def test_contractors_returns_the_scorecard(client):
    body = client.get("/api/contractors").json()
    assert len(body["rows"]) == 3
    watch = next(row for row in body["rows"] if row["name"] == "Sri Sai Constructions")
    assert watch["tier"] == "WATCH"
    assert watch["tone"] == "danger"
    assert watch["flags_per_boq"] == 7.2
    assert watch["sites_gone_quiet"] == 1
    assert watch["sites"] == 4
    assert "Kompally" in watch["meta"]
    # Worst tier first: the screen exists to surface the risky builders.
    assert [row["tier"] for row in body["rows"]] == ["WATCH", "REVIEW", "RELIABLE"]


# ---------------------------------------------------------------- the boundary


def test_deciding_a_tranche_needs_a_session(client):
    client.cookies.clear()
    # A decision goes into the loan file under somebody's name. Without a
    # session there is nobody to attribute it to.
    response = client.post("/api/loans/1001/tranches/3/decision", json={"action": "HOLD"})
    assert response.status_code == 401


def test_a_borrower_cannot_decide_their_own_tranche(client):
    client.post("/api/auth/session", json=OWNER_LOGIN)
    response = client.post("/api/loans/1001/tranches/3/decision", json={"action": "RELEASE"})
    assert response.status_code == 403

    from sqlalchemy import func, select

    from app.db import models
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(models.Decision)) == 0


def test_a_borrower_cannot_read_the_whole_book(client):
    # The hotlist names every borrower in the book, so one borrower's session
    # reading it would undo the owner/loan boundary a loan at a time.
    client.post("/api/auth/session", json=OWNER_LOGIN)
    assert client.get("/api/portfolio").status_code == 403
    assert client.get("/api/contractors").status_code == 403
    assert client.get("/api/loans/1001/tranches/3").status_code == 403


def test_a_lender_reads_all_three(client):
    _as_officer(client)
    assert client.get("/api/portfolio").status_code == 200
    assert client.get("/api/contractors").status_code == 200
    assert client.get("/api/loans/1001/tranches/3").status_code == 200


def test_the_slab_tranche_is_paid_and_carries_no_pending_decision(client):
    """The contradiction this replaced: T3 was marked on_hold while the frozen
    figures counted its 6,00,000 as disbursed. Money cannot be both."""
    body = client.get("/api/loans/1001/tranches/3").json()
    assert body["tranche_number"] == 3
    assert body["exposure"] is None, "the risk assessment belongs to the pending tranche"
    math = {row["label"]: row["result"] for row in body["math"]}
    assert math["Disbursed so far"] == 1800000, "T3's own cumulative is the drawn figure"


def test_every_portfolio_row_agrees_with_the_screen_it_links_to(client):
    """A row reading "HOLD, 1.42" must not drill into "INSPECT, exposure
    undefined" with an em dash in every math line.

    All ten loans carry a recorded run now, and the row quotes the tranche the
    assessment was written to — which is what `_assessed_tranche` exists to
    get right. It was wrong for 1004: the run wrote ESCALATE onto T3 while the
    row pointed at T4, drawn and unassessed, so the screen answered INSPECT to
    somebody who had just read ESCALATE.

    Agreement includes agreeing that a figure is not there. Four loans have no
    exposure because no photograph was assessed, and the row and the screen
    both have to say so."""
    # Every label the portfolio can show, mapped to the recommendation the
    # screen behind it must carry. ESCALATE arrived when the eight derived
    # loans were re-analysed — two of them had photographs that disagreed with
    # the claimed stage — and a label with no entry here fails as a KeyError,
    # which is the right way for this test to notice a new one.
    expected = {
        "HOLD": "HOLD",
        "INSPECT": "INSPECT",
        "ESCALATE": "ESCALATE",
        "ON TRACK": "RELEASE",
    }

    for row in client.get("/api/portfolio").json()["rows"]:
        # The row links to the borrower's file; the draw its figures describe is
        # carried in `tranche` rather than parsed back out of the href.
        assert row["href"] == f"/bank/loans/{row['loan_id']}"
        screen = client.get(
            f"/api/loans/{row['loan_id']}/tranches/{row['tranche']}"
        ).json()
        assert screen["recommendation"] == expected[row["action_label"]], row["loan_id"]
        assert screen["exposure"] == row["exposure"], row["loan_id"]
        assert screen["exposure_undefined"] is (row["exposure"] is None), row["loan_id"]


def test_every_loan_now_carries_its_own_rationale(client):
    """It used to be that only 1001 and 1002 had a narrative, and the other
    eight showed an honest empty state rather than prose invented for them.

    All ten were recorded on 2026-09-10, so the explainer wrote for each of
    them — and the point that survives is the one that mattered then: the
    rationale a screen shows is one an agent actually produced for that loan,
    never text borrowed from another.
    """
    seen: set[str] = set()
    for loan_id, tranche in (("1001", 4), ("1003", 3), ("1009", 3)):
        body = client.get(f"/api/loans/{loan_id}/tranches/{tranche}").json()
        assert body["officer_view"], loan_id
        assert body["owner_view"], loan_id
        # Not another loan's prose.
        assert body["officer_view"] not in seen, f"{loan_id} reuses a rationale"
        seen.add(body["officer_view"])


def test_the_tranche_decision_carries_the_whole_record(client):
    """A decision is taken against the loan's history, not one tranche alone."""
    phases = client.get("/api/loans/1001/tranches/4").json()["phases"]
    assert len(phases) == 4
    # Exposure was worse before this request than it is now; a screen showing
    # only today's figure would hide the peak.
    exposures = [p["exposure"] for p in phases if p["exposure"]]
    assert max(exposures) > captured().risk_assessment.exposure_ratio
