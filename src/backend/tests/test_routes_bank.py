"""Bank-facing HTTP surface: the hotlist, one tranche decision, and contractors.

The hotlist's row order is the design's, not the SQL's, so it is asserted
literally. Decisions are asserted idempotent because a credit officer
double-clicking "Hold" must not write two entries into the loan file.
"""

# `client` and `seeded_db` come from tests/conftest.py.

DESIGN_ORDER = ["1003", "1004", "1001", "1009", "1006", "1010", "1002", "1007", "1008", "1005"]


# ---------------------------------------------------------------- portfolio


def test_portfolio_returns_the_whole_book_in_the_designs_order(client):
    body = client.get("/api/portfolio").json()
    assert [row["loan_id"] for row in body["rows"]] == DESIGN_ORDER
    assert body["cards"][0]["value"] == 10


def test_every_row_links_to_its_own_loan(client):
    rows = client.get("/api/portfolio").json()["rows"]
    hrefs = [row["href"] for row in rows]
    assert len(set(hrefs)) == len(hrefs)
    for row in rows:
        assert row["loan_id"] in row["href"]
        assert row["href"] != "#"


def test_needs_action_selects_hold_and_inspect(client):
    body = client.get("/api/portfolio", params={"filter": "needs_action"}).json()
    assert [row["loan_id"] for row in body["rows"]] == ["1003", "1004", "1001", "1009", "1006"]
    assert {row["action_label"] for row in body["rows"]} == {"HOLD", "INSPECT"}
    # The cards describe the whole book, so filtering rows must not move them.
    assert body["cards"][0]["value"] == 10


def test_on_track_is_the_complement(client):
    rows = client.get("/api/portfolio", params={"filter": "on_track"}).json()["rows"]
    assert len(rows) == 5
    assert {row["action_label"] for row in rows} == {"ON TRACK"}


def test_an_unknown_filter_is_rejected(client):
    assert client.get("/api/portfolio", params={"filter": "spicy"}).status_code == 422


def test_portfolio_money_is_numeric(client):
    for row in client.get("/api/portfolio").json()["rows"]:
        assert isinstance(row["disbursed"], (int, float))
        assert row["gap"] is None or isinstance(row["gap"], (int, float))


# ---------------------------------------------------------------- tranche


def test_the_golden_tranche_reports_the_mockups_figures(client):
    body = client.get("/api/loans/1001/tranches/3").json()
    assert body["borrower"] == "Ravi Kumar"
    assert body["tranche_number"] == 3
    assert body["request_amount"] == 600000
    assert body["exposure"] == 1.29
    assert body["recommendation"] == "HOLD"
    assert body["recommendation_tone"] == "danger"
    math = {row["label"]: row["result"] for row in body["math"]}
    assert math["Disbursed so far"] == 1800000
    assert math["Verified value in place"] == 1390000
    assert math["Cost to complete"] == 1580000
    assert math["Cost-to-complete gap"] == -580000
    assert len(body["photos"]) == 3
    assert body["owner_view"] and body["officer_view"]


def test_an_unknown_tranche_is_404(client):
    assert client.get("/api/loans/1001/tranches/99").status_code == 404


def test_a_tranche_on_an_unknown_loan_is_404(client):
    assert client.get("/api/loans/9999/tranches/1").status_code == 404


# ---------------------------------------------------------------- decision


def test_a_decision_persists_with_its_evidence_snapshot(client):
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

    with SessionLocal() as db:
        tranche = next(t for t in db.get(models.Loan, "1001").tranches if t.number == 3)
        decision = tranche.decision
        assert decision is not None
        assert decision.action == "HOLD"
        assert decision.note == "Re-scope first."
        snapshot = decision.evidence_snapshot
        assert snapshot and "exposure" in snapshot


def test_a_second_decision_updates_rather_than_duplicating(client):
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
    first = client.post("/api/loans/1001/tranches/3/decision", json={"action": "HOLD"})
    again = client.post("/api/loans/1001/tranches/3/decision", json={"action": "RELEASE"})
    assert first.json()["action"] == "HOLD"
    assert again.json()["action"] == "RELEASE"


def test_an_unknown_action_is_rejected(client):
    response = client.post("/api/loans/1001/tranches/3/decision", json={"action": "YOLO"})
    assert response.status_code == 422


def test_a_decision_on_an_unknown_tranche_is_404(client):
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
