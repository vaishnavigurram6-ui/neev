"""Owner-facing HTTP surface: auth, the loan, the BoQ, and the analysis stream.

Two properties get pinned everywhere: an unknown id is a 404 rather than a 500
or an empty object, and money arrives as a number rather than a formatted
string. The socket-blocking fixture in conftest.py is autouse, so any route that
reached the network would fail these tests instead of costing money.
"""

import json

# `client`, `seeded_db` and `instant_pipeline` come from tests/conftest.py.

OWNER_LOGIN = {"role": "owner", "phone": "9999999999", "loan_id": "1001"}
BANK_LOGIN = {"role": "bank", "phone": "9812345678"}


def _login(client, payload=None):
    response = client.post("/api/auth/session", json=payload or OWNER_LOGIN)
    assert response.status_code == 200, response.text
    return response


# ---------------------------------------------------------------- auth


def test_posting_a_session_sets_the_cookie_the_frontend_parses(client):
    response = _login(client)
    body = response.json()
    assert body == {"role": "owner", "loan_id": "1001", "name": "Ravi Kumar"}

    # The frontend's readSession() splits on ":" — role:loanId:name. Keeping
    # this exact shape is what lets Next.js middleware read the session.
    raw = client.cookies["neev_session"]
    role, loan_id, name = raw.split(":")
    assert (role, loan_id) == ("owner", "1001")
    assert name == "Ravi%20Kumar"


def test_me_is_401_without_a_session(client):
    assert client.get("/api/me").status_code == 401


def test_me_returns_the_profile_chip_fields(client):
    _login(client)
    body = client.get("/api/me").json()
    assert body["role"] == "owner"
    assert body["loan_id"] == "1001"
    assert body["name"] == "Ravi Kumar"
    assert body["sub"] == "Owner · Plot 47, Kompally"


def test_a_bank_session_gets_the_officer_chip(client):
    _login(client, BANK_LOGIN)
    body = client.get("/api/me").json()
    assert body["role"] == "bank"
    assert body["sub"].startswith("Credit officer")


def test_deleting_the_session_clears_it(client):
    _login(client)
    assert client.delete("/api/auth/session").status_code == 204
    assert client.get("/api/me").status_code == 401


def test_a_malformed_cookie_is_no_session_not_a_crash(client):
    client.cookies.set("neev_session", "wizard:1001:Ravi")
    assert client.get("/api/me").status_code == 401


def test_a_bad_phone_is_rejected(client):
    response = client.post("/api/auth/session", json={"role": "owner", "phone": "12"})
    assert response.status_code == 422


def test_an_owner_session_for_an_unknown_loan_is_rejected(client):
    response = client.post("/api/auth/session", json={"role": "owner", "phone": "9999999999", "loan_id": "9999"})
    assert response.status_code == 404


# ---------------------------------------------------------------- the loan


def test_loan_summary_returns_numbers(client):
    body = client.get("/api/loans/1001").json()
    assert body["loan_id"] == "1001"
    assert body["borrower"] == "Ravi Kumar"
    assert body["sanctioned"] == 2800000
    assert body["disbursed"] == 1800000
    assert body["contractor"] == "Sri Sai Constructions"
    assert body["latest_rev"] == 1


def test_an_unknown_loan_is_404(client):
    assert client.get("/api/loans/9999").status_code == 404


def test_an_owner_cannot_read_another_borrowers_loan(client):
    _login(client)
    assert client.get("/api/loans/1002").status_code == 403


def test_a_bank_session_may_read_any_loan(client):
    _login(client, BANK_LOGIN)
    assert client.get("/api/loans/1002").status_code == 200


# ---------------------------------------------------------------- BoQ review


def test_boq_latest_carries_the_mockups_figures(client):
    body = client.get("/api/loans/1001/boq/latest").json()
    assert body["loan_id"] == "1001"
    assert body["contractor"] == "Sri Sai Constructions"
    assert body["received_on"] == "2026-08-12"
    assert body["item_count"] == 40
    assert body["cards"][0]["value"] == 3200000
    assert body["cards"][1]["value"] == 9
    assert body["cards"][2]["value"] == 154000
    assert body["pct_before_slab"] == 0.45
    assert body["amount_before_slab"] == 1440000
    assert len(body["questions"]) == 4
    assert sum(len(group["items"]) for group in body["groups"]) == 9


def test_no_money_crosses_the_api_as_a_formatted_string(client):
    body = client.get("/api/loans/1001/boq/latest").json()
    for card in body["cards"]:
        if card["value_kind"] != "text":
            assert isinstance(card["value"], (int, float)), card


def test_boq_latest_for_an_unknown_loan_is_404(client):
    assert client.get("/api/loans/9999/boq/latest").status_code == 404


def test_boq_latest_for_a_loan_with_no_analysis_is_404(client):
    # Loan 1003 is in the book but has no BoQ revision yet. An empty object
    # would render a blank screen; a 404 renders the real not-found page.
    assert client.get("/api/loans/1003/boq/latest").status_code == 404


def test_boq_by_revision_matches_latest(client):
    latest = client.get("/api/loans/1001/boq/latest").json()
    rev1 = client.get("/api/loans/1001/boq/rev/1").json()
    assert rev1 == latest
    assert client.get("/api/loans/1001/boq/rev/7").status_code == 404


def test_sanction_check_bars_and_shortfall(client):
    body = client.get("/api/loans/1001/sanction-check").json()
    assert [bar["value"] for bar in body["bars"]] == [3200000, 3500000, 2800000]
    assert body["shortfall"] == 700000
    assert len(body["options"]) == 3
    assert client.get("/api/loans/9999/sanction-check").status_code == 404


# ---------------------------------------------------------------- questions


def test_sending_the_questions_marks_them_sent_and_is_idempotent(client):
    first = client.post("/api/loans/1001/questions/send")
    assert first.status_code == 200
    assert first.json()["sent"] == 4

    second = client.post("/api/loans/1001/questions/send")
    assert second.json()["sent"] == 4

    statuses = {q["status"] for q in client.get("/api/loans/1001/boq/latest").json()["questions"]}
    assert statuses == {"sent"}


def test_sending_questions_for_an_unknown_loan_is_404(client):
    assert client.post("/api/loans/9999/questions/send").status_code == 404


# ---------------------------------------------------------------- progress


def test_progress_reports_the_payment_ladder_and_where_you_stand(client):
    body = client.get("/api/loans/1001/progress").json()
    assert body["sanctioned"] == 2800000
    assert body["disbursed"] == 1800000
    # The draw schedule gives loan 1001 three tranches, with T3 held pending
    # the decision the bank console is looking at. The mockup's five-row ladder
    # is illustrative; the seeded schedule is the data.
    assert [t["number"] for t in body["tranches"]] == [1, 2, 3]
    assert [t["status_label"] for t in body["tranches"]] == ["Paid", "Paid", "On hold"]
    assert [t["amount"] for t in body["tranches"]] == [600000, 600000, 600000]
    assert body["tranches"][2]["name"] == "Roof slab"
    assert body["paused"] is True
    assert body["current_stage"] == "slab"
    assert body["last_verified_on"] == "2026-08-10"
    standing = {row["label"]: row["value"] for row in body["standing"]}
    assert standing["Paid to your contractor"] == 1800000
    assert standing["Work standing on site"] == 1390000
    assert standing["Left in your sanction"] == 1000000
    assert standing["Needed to finish"] == 1580000
    assert body["shortfall"] == -580000
    assert len(body["steps"]) == 3


def test_progress_for_an_unknown_loan_is_404(client):
    assert client.get("/api/loans/9999/progress").status_code == 404


def test_reporting_a_milestone_stores_the_photos(client):
    files = [
        ("photos", ("front.jpg", b"\xff\xd8\xff-not-really-a-jpeg", "image/jpeg")),
        ("photos", ("slab.jpg", b"\xff\xd8\xff-nor-is-this", "image/jpeg")),
    ]
    response = client.post("/api/loans/1001/milestones", files=files, data={"stage": "slab"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tranche"] == 3
    assert body["photos"] == 2

    photos = client.get("/api/loans/1001/tranches/3").json()["photos"]
    assert len([p for p in photos if p["slot_key"].startswith("1001-t3-upload")]) == 2


def test_reporting_a_milestone_needs_at_least_one_photo(client):
    assert client.post("/api/loans/1001/milestones", data={"stage": "slab"}).status_code == 422


# ---------------------------------------------------------------- upload + SSE


def _sse_events(client, job_id):
    with client.stream("GET", f"/api/jobs/{job_id}/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        raw = "".join(response.iter_text())
    return [
        json.loads(line[len("data: ") :])
        for line in raw.splitlines()
        if line.startswith("data: ")
    ]


def test_uploading_a_boq_returns_a_job_whose_stream_ends_in_done(client, instant_pipeline):
    response = client.post(
        "/api/loans/1001/boq",
        files={"file": ("sample_boq.pdf", b"%PDF-1.4 pretend", "application/pdf")},
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]

    events = _sse_events(client, job_id)
    kinds = [event["type"] for event in events]
    assert "phase" in kinds
    assert "finding" in kinds
    assert "progress" in kinds
    assert kinds[-1] == "done"
    assert events[-1]["redirect"] == "/owner/loans/1001/boq"


def test_uploading_to_an_unknown_loan_is_404(client, instant_pipeline):
    response = client.post(
        "/api/loans/9999/boq",
        files={"file": ("sample_boq.pdf", b"%PDF-1.4 pretend", "application/pdf")},
    )
    assert response.status_code == 404


def test_an_unknown_job_still_terminates_the_stream(client):
    # A page reloaded after a restart must not spin forever; it gets a done
    # event pointing somewhere real.
    events = _sse_events(client, "nosuchjob")
    assert events[-1]["type"] == "done"


def test_a_crashed_run_emits_an_error_event_before_done(client, monkeypatch):
    import app.services.jobs as jobs_module

    class Boom:
        async def run(self, req):
            raise RuntimeError("pipeline exploded")
            yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(jobs_module, "get_runner", lambda *a, **k: Boom())

    job_id = client.post(
        "/api/loans/1001/boq",
        files={"file": ("sample_boq.pdf", b"%PDF-1.4 pretend", "application/pdf")},
    ).json()["job_id"]

    events = _sse_events(client, job_id)
    assert [event["type"] for event in events] == ["error", "done"]
    assert "exploded" in events[0]["message"]

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "error"
    assert "exploded" in status["error"]


def test_job_status_for_an_unknown_job_is_404(client):
    assert client.get("/api/jobs/nosuchjob").status_code == 404


# ---------------------------------------------------------------- fences


def test_no_route_is_screen_shaped(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in paths:
        assert "page" not in path, f"{path} looks screen-shaped"


def test_the_backend_never_imports_the_adk_pipeline():
    import sys

    import app.main  # noqa: F401

    assert not [name for name in sys.modules if name.startswith("neev_pipeline")]
    assert not [name for name in sys.modules if name == "google" or name.startswith("google.")]
