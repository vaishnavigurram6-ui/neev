"""Owner-facing HTTP surface: auth, the loan, the BoQ, and the analysis stream.

Two properties get pinned everywhere: an unknown id is a 404 rather than a 500
or an empty object, and money arrives as a number rather than a formatted
string. The socket-blocking fixture in conftest.py is autouse, so any route that
reached the network would fail these tests instead of costing money.
"""

import json

import pytest

def captured(loan_id: str = "1001"):
    """The captured run's own figures, read rather than transcribed.

    These assertions used to carry numbers from the mockups. The fixtures are
    now recorded live runs, so a literal here would break on every re-capture
    while proving nothing -- what these tests exist to check is that the API
    surfaces what the pipeline produced, not that the pipeline produced a
    particular number.
    """
    from app.fixtures.loader import load_pipeline_output

    return load_pipeline_output(loan_id)



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


def test_a_forged_name_in_the_cookie_does_not_become_the_borrowers(client):
    # The cookie is client input. /api/me answers from the loan record, so a
    # doctored cookie cannot make the console greet someone else's name.
    client.cookies.set("neev_session", "owner:1001:Mallory")
    assert client.get("/api/me").json()["name"] == "Ravi Kumar"


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


def test_boq_latest_carries_the_captured_figures(client):
    body = client.get("/api/loans/1001/boq/latest").json()
    assert body["loan_id"] == "1001"
    assert body["contractor"] == "Sri Sai Constructions"
    assert body["received_on"] == "2026-08-12"
    assert body["item_count"] == 40
    out = captured()
    assert body["cards"][0]["value"] == out.boq_findings.boq_total
    assert body["cards"][1]["value"] == len(out.boq_findings.flags)
    assert body["pct_before_slab"] == out.boq_findings.payment_pct_before_slab
    # Derived, not stored: the rail needs the rupee figure and the fraction.
    out = captured()
    assert body["amount_before_slab"] == pytest.approx(
        out.boq_findings.boq_total * out.boq_findings.payment_pct_before_slab
    )
    assert len(body["questions"]) == 4
    # Every flag must reach a group; none may be dropped on the way to a screen.
    assert sum(len(group["items"]) for group in body["groups"]) == len(
        captured().boq_findings.flags
    )


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
    out = captured()
    quoted, fair = out.boq_findings.boq_total, out.cost_estimate.expected_total_cost
    assert [bar["value"] for bar in body["bars"]] == [quoted, fair, 2800000]
    # The shortfall IS the fair price minus what was sanctioned.
    assert body["shortfall"] == pytest.approx(fair - 2800000)
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
    # Loan 1001's ladder: T1-T3 paid, T4 held pending the decision the bank
    # console is looking at. The mockup's five-row ladder is illustrative; the
    # seeded schedule is the data.
    assert [t["number"] for t in body["tranches"]] == [1, 2, 3, 4]
    assert [t["status_label"] for t in body["tranches"]] == ["Paid", "Paid", "Paid", "On hold"]
    assert [t["amount"] for t in body["tranches"]] == [600000, 600000, 600000, 440000]
    assert body["tranches"][2]["name"] == "Roof slab"
    assert body["paused"] is True
    assert body["current_stage"] == "slab"
    assert body["last_verified_on"] == "2026-08-10"
    standing = {row["label"]: row["value"] for row in body["standing"]}
    risk = captured().risk_assessment
    assert standing["Paid to your contractor"] == 1800000
    assert standing["Work standing on site"] == risk.verified_value
    assert standing["Left in your sanction"] == 1000000
    # cost_to_complete is optional and this run did not report one, so the row
    # renders an em dash rather than a fabricated figure.
    assert standing["Needed to finish"] == (risk.cost_to_complete or "—")
    assert body["shortfall"] == risk.cost_to_complete_gap
    assert len(body["steps"]) == 3


def test_an_unverified_site_reads_as_unknown_not_as_zero(client):
    """"₹0 standing on site" would be a false statement to a borrower who has
    already paid a tranche. An em dash is the honest one, and value_kind says so.

    This used to lean on loan 1005 having no assessed tranche. Every loan now
    carries a verified value, so the unverified case is constructed directly --
    which is the more durable test anyway: a live run with no inspection yet
    produces exactly this state, and it should not depend on a loan being
    under-seeded.
    """
    from sqlalchemy import select

    from app.db import models
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        for tranche in db.scalars(
            select(models.Tranche).where(models.Tranche.loan_id == "1005")
        ):
            tranche.verified_value = None
        db.commit()

    standing = client.get("/api/loans/1005/progress").json()["standing"]
    unverified = next(row for row in standing if row["label"] == "Work standing on site")
    assert unverified["value"] == "—"
    assert unverified["value_kind"] == "text"


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
    # Photos are filed against the tranche awaiting a decision, which is T4.
    assert body["tranche"] == 4
    assert body["photos"] == 2

    photos = client.get("/api/loans/1001/tranches/4").json()["photos"]
    assert len([p for p in photos if p["slot_key"].startswith("1001-t4-upload")]) == 2


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


def test_ways_forward_are_the_loans_own_not_the_golden_cases(client):
    """Quoting a saving a borrower cannot make is worse than quoting none.

    This screen used to serve loan 1001's "≈ ₹1,60,000 / ≈ ₹2,40,000 / a
    ₹3,00,000 top-up" to every borrower, and cite four BoQ questions only 1001
    has.
    """
    golden = client.get("/api/loans/1001/sanction-check").json()["options"]
    # 1001's first route quotes a real figure, derived from the negative section
    # deltas its own captured cost estimate reports.
    assert golden[0]["saves_label"].startswith("≈ ₹")
    assert golden[-1]["saves_label"] == "closes the rest"

    clean = client.get("/api/loans/1002/sanction-check").json()["options"]
    labels = [o["saves_label"] for o in clean]
    titles = [o["title"] for o in clean]

    # 1002's captured BoQ does carry one vague spec, so offering a negotiation
    # is correct -- what must not happen is 1001's figures appearing on it.
    assert titles == [o["title"] for o in golden]
    assert labels != [o["saves_label"] for o in golden]
    # 1002 has no over-priced sections, so there is no rupee figure to quote and
    # the label must say what the route does instead of inventing one.
    assert labels[0] == "reduces the quote"
    assert "≈ ₹2,40,000" not in labels
    assert not any("3,00,000" in o["desc"] for o in clean)
    assert not any("four questions" in o["desc"] for o in clean)


def test_boq_review_exposes_the_quoted_total_directly(client):
    """The rail needs it twice. It used to be inverted out of
    amount_before_slab / pct_before_slab, which divides by zero on a schedule
    with nothing due before the slab."""
    body = client.get("/api/loans/1001/boq/latest").json()
    assert body["boq_total"] == captured().boq_findings.boq_total


def test_a_flag_in_an_unmapped_group_is_still_rendered(client):
    """GROUP_ORDER is the mockup's editorial order, not an allow-list.

    Filtering by it silently dropped rows while the FLAGS RAISED card went on
    counting every flag, so the table and the card disagreed with nothing on
    screen to say which was right.
    """
    from app.db import models
    from app.db.session import SessionLocal
    from app.mappers.boq import _group

    with SessionLocal() as db:
        loan = db.get(models.Loan, "1001")
        flags = list(loan.revisions[-1].flags)
        flags[0].group_name = "13. A SECTION THE MOCKUP NEVER NAMED"
        groups = _group(flags)

    rendered = sum(len(g.items) for g in groups)
    assert rendered == len(flags), "every flag must appear in some group"
    assert "13. A SECTION THE MOCKUP NEVER NAMED" in [g.name for g in groups]


def test_build_progress_carries_the_phase_history(client):
    phases = client.get("/api/loans/1001/progress").json()["phases"]
    risk = captured().risk_assessment
    assert [p["tranche_number"] for p in phases] == [1, 2, 3, 4]
    # Each phase recomputes exposure at that point rather than carrying today's,
    # so the series must end at the current figure and rise as cover thins.
    assert phases[2]["exposure"] == risk.exposure_ratio
    assert phases[2]["verified_value"] == risk.verified_value
    # Not monotonic, and it should not be: verified value jumps when a heavy
    # milestone lands (slab carries 0.25 of the build against plinth's 0.10), so
    # cover can improve. What matters is that the last drawn phase is today's.
    assert phases[2]["exposure"] == risk.exposure_ratio
