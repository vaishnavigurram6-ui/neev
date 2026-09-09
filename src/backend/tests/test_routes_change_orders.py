"""Change orders: who may read them, who may answer them, and what the total says.

The running total is the point of the screen — an owner deciding whether to
accept a variation is deciding against one figure — so most of these pin the
arithmetic rather than the status string.
"""

from tests.conftest import BANK_LOGIN, OWNER_1002_LOGIN, OWNER_LOGIN


def _as(client, login):
    client.cookies.clear()
    assert client.post("/api/auth/session", json=login).status_code == 200


def _orders(client, loan_id="1001"):
    response = client.get(f"/api/loans/{loan_id}/change-orders")
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------- reading


def test_the_seeded_variations_arrive_priced_against_the_signed_boq(client):
    _as(client, OWNER_LOGIN)
    body = _orders(client)
    assert len(body["orders"]) == 2
    first = body["orders"][0]
    # Delta is computed once, in the mapper, so the rows and the total agree.
    assert first["delta"] == first["proposed_amount"] - first["signed_amount"]
    assert all(order["open"] for order in body["orders"])
    assert body["pending_total"] == sum(o["delta"] for o in body["orders"])
    assert body["accepted_total"] == 0
    assert body["if_accepted_total"] == body["signed_total"] + body["pending_total"]


def test_a_lender_reads_the_variations_but_may_not_answer_them(client):
    _as(client, BANK_LOGIN)
    body = _orders(client)
    order_id = body["orders"][0]["id"]
    refused = client.post(
        f"/api/loans/1001/change-orders/{order_id}/reply", json={"action": "accept"}
    )
    assert refused.status_code == 403
    assert "borrower" in refused.json()["detail"]


def test_an_owner_cannot_read_another_loans_variations(client):
    _as(client, OWNER_LOGIN)
    assert client.get("/api/loans/1002/change-orders").status_code == 403


def test_anonymous_readers_get_nothing(client):
    client.cookies.clear()
    assert client.get("/api/loans/1001/change-orders").status_code == 401


# ---------------------------------------------------------------- replying


def test_accepting_moves_the_delta_from_pending_to_accepted(client):
    _as(client, OWNER_LOGIN)
    before = _orders(client)
    target = before["orders"][0]

    replied = client.post(
        f"/api/loans/1001/change-orders/{target['id']}/reply",
        json={"action": "accept", "note": "Agreed on site."},
    )
    assert replied.status_code == 200, replied.text
    assert replied.json()["status"] == "accepted"
    assert replied.json()["open"] is False
    assert replied.json()["replied_at"] is not None

    after = _orders(client)
    assert after["accepted_total"] == target["delta"]
    assert after["pending_total"] == before["pending_total"] - target["delta"]
    # The figure the owner is deciding against does not move when they accept
    # something already counted as pending-if-accepted.
    assert after["if_accepted_total"] == before["if_accepted_total"]


def test_declining_costs_the_signed_amount_and_nothing_more(client):
    _as(client, OWNER_LOGIN)
    before = _orders(client)
    target = before["orders"][1]

    client.post(f"/api/loans/1001/change-orders/{target['id']}/reply", json={"action": "decline"})
    after = _orders(client)

    declined = next(o for o in after["orders"] if o["id"] == target["id"])
    assert declined["status"] == "declined" and declined["open"] is False
    assert after["if_accepted_total"] == before["if_accepted_total"] - target["delta"]


def test_a_counter_is_priced_at_the_counter_and_stays_open(client):
    _as(client, OWNER_LOGIN)
    before = _orders(client)
    target = before["orders"][0]
    counter = int(target["signed_amount"]) + 5000

    replied = client.post(
        f"/api/loans/1001/change-orders/{target['id']}/reply",
        json={"action": "counter", "counter_amount": counter, "note": "Signed rate holds."},
    )
    assert replied.status_code == 200, replied.text
    body = replied.json()
    assert (body["status"], body["open"], body["counter_amount"]) == ("countered", True, counter)

    after = _orders(client)
    assert after["pending_total"] == before["pending_total"] - target["delta"] + 5000


def test_a_counter_without_a_figure_is_refused(client):
    _as(client, OWNER_LOGIN)
    order_id = _orders(client)["orders"][0]["id"]
    assert client.post(
        f"/api/loans/1001/change-orders/{order_id}/reply", json={"action": "counter"}
    ).status_code == 422
    # And an amount on an accept is a caller confusing two different replies.
    assert client.post(
        f"/api/loans/1001/change-orders/{order_id}/reply",
        json={"action": "accept", "counter_amount": 1000},
    ).status_code == 422


def test_a_settled_order_cannot_be_answered_twice(client):
    _as(client, OWNER_LOGIN)
    order_id = _orders(client)["orders"][0]["id"]
    assert client.post(
        f"/api/loans/1001/change-orders/{order_id}/reply", json={"action": "accept"}
    ).status_code == 200
    again = client.post(
        f"/api/loans/1001/change-orders/{order_id}/reply", json={"action": "decline"}
    )
    assert again.status_code == 409
    # A countered order is an open offer, so it stays answerable.
    other = _orders(client)["orders"][1]["id"]
    client.post(
        f"/api/loans/1001/change-orders/{other}/reply",
        json={"action": "counter", "counter_amount": 50000},
    )
    assert client.post(
        f"/api/loans/1001/change-orders/{other}/reply", json={"action": "accept"}
    ).status_code == 200


def test_replying_to_a_change_order_that_does_not_exist_is_a_404(client):
    _as(client, OWNER_LOGIN)
    assert client.post(
        "/api/loans/1001/change-orders/9999/reply", json={"action": "accept"}
    ).status_code == 404


# ---------------------------------------------------------------- logging one


def test_an_owner_can_log_a_change_and_it_is_marked_unchecked(client):
    _as(client, OWNER_LOGIN)
    created = client.post(
        "/api/loans/1001/change-orders",
        json={
            "title": "Extra window in the stair landing",
            "signed_desc": "No window in the signed drawing",
            "signed_amount": 0,
            "proposed_desc": "1 no. UPVC window, 3 x 4 ft",
            "proposed_amount": 14500,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["delta"] == 14500
    # Never dressed as a checked finding: Neev did not price this one.
    assert body["tone"] == "neutral"
    assert "not yet checked" in body["neevs_read"]
    assert len(_orders(client)["orders"]) == 3


def test_a_lender_cannot_log_a_change_on_a_loan_it_does_not_hold(client):
    """A lender legitimately reads the book, so this one is about the owner's
    boundary: an owner signed in for 1001 cannot write against 1002."""
    _as(client, OWNER_LOGIN)
    assert client.post(
        "/api/loans/1002/change-orders",
        json={
            "title": "x",
            "signed_desc": "x",
            "signed_amount": 0,
            "proposed_desc": "y",
            "proposed_amount": 1,
        },
    ).status_code == 403
