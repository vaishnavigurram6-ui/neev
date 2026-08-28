"""Bank-facing HTTP surface: the hotlist, one tranche decision, and contractors.

The hotlist's row order is the design's, not the SQL's, so it is asserted
literally. Decisions are asserted idempotent because a credit officer
double-clicking "Hold" must not write two entries into the loan file.
"""

# `client` and `seeded_db` come from tests/conftest.py.

BANK_LOGIN = {"role": "bank", "phone": "9812345678"}
OWNER_LOGIN = {"role": "owner", "phone": "9999999999", "loan_id": "1001"}


def _as_officer(client):
    """Deciding a tranche needs a real lender session; reading does not."""
    assert client.post("/api/auth/session", json=BANK_LOGIN).status_code == 200


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
    # The decision is pending on T4, not T3. T1-T3 are paid, which is the only
    # reading under which 18,00,000 disbursed adds up -- and it is what the
    # mockup's own gap row assumes: "(28,00,000 - 18,00,000) - 15,80,000".
    body = client.get("/api/loans/1001/tranches/4").json()
    assert body["borrower"] == "Ravi Kumar"
    assert body["tranche_number"] == 4
    assert body["request_amount"] == 440000  # 0.80 x 28,00,000 - 18,00,000
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
