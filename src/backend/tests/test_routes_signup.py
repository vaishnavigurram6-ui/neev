"""Sign-up creates a borrower and the loan behind them, and nothing more.

The rule these hold to: the role in `users` is a lookup key, never a claim.
Sign-up writes `owner` and only `owner`, so no request can talk its way into
the whole book, and the provisioned names cannot be minted by a visitor.
"""

import pytest
from sqlalchemy import select

from app.db import models
from app.db.session import SessionLocal

NEW = {
    "name": "Lakshmi Reddy",
    "username": "lakshmi",
    "password": "a-long-enough-secret",
    "locality": "Miyapur",
    "sanctioned": 3_200_000,
    "built_up_sqft": 1450,
}


def signup(client, **overrides):
    return client.post("/api/auth/signup", json={**NEW, **overrides})


def test_signup_opens_an_account_and_a_loan(client):
    response = signup(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "owner"
    assert body["name"] == "Lakshmi Reddy"
    # The seeded book is 1001-1010, so the first created loan is 1011.
    assert body["loan_id"] == "1011"

    with SessionLocal() as db:
        loan = db.get(models.Loan, "1011")
        assert loan is not None
        assert (loan.borrower_name, loan.locality, loan.sanctioned) == (
            "Lakshmi Reddy",
            "Miyapur",
            3_200_000,
        )
        assert loan.disbursed == 0
        # Nothing has been checked, so it has no exposure to rank. Ranked 0 it
        # would head a list ordered worst-first.
        assert loan.hotlist_rank == 1_000
        assert loan.tranches == [] and loan.revisions == []


def test_signup_signs_you_in(client):
    assert signup(client).status_code == 201
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["role"] == "owner"
    assert me.json()["loan_id"] == "1011"


def test_the_new_account_can_sign_in_again(client):
    assert signup(client).status_code == 201
    client.delete("/api/auth/session")
    again = client.post(
        "/api/auth/session", json={"username": "lakshmi", "password": NEW["password"]}
    )
    assert again.status_code == 200
    assert again.json()["loan_id"] == "1011"


def test_the_password_is_hashed_not_stored(client):
    assert signup(client).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(models.User).where(models.User.username == "lakshmi"))
        assert user is not None
        assert NEW["password"] not in user.password_hash
        assert user.password_hash.startswith("scrypt$")
        assert user.role == "owner"


def test_the_wrong_password_is_refused(client):
    assert signup(client).status_code == 201
    client.delete("/api/auth/session")
    refused = client.post(
        "/api/auth/session", json={"username": "lakshmi", "password": "not-the-secret"}
    )
    assert refused.status_code == 401


def test_a_username_is_case_and_space_insensitive(client):
    assert signup(client, username="  LAKSHMI  ").status_code == 201
    client.delete("/api/auth/session")
    assert (
        client.post(
            "/api/auth/session", json={"username": "Lakshmi", "password": NEW["password"]}
        ).status_code
        == 200
    )


def test_a_taken_username_is_refused(client):
    assert signup(client).status_code == 201
    client.delete("/api/auth/session")
    again = signup(client, name="Someone Else")
    assert again.status_code == 409
    assert "not available" in again.json()["detail"]


@pytest.mark.parametrize("name", ["officer", "ravi", "prasad", "admin", "OFFICER"])
def test_a_provisioned_name_cannot_be_minted(client, name):
    """Otherwise a visitor creates `officer` with a password of their choosing.
    The provisioned branch is tried first, so the account they made would be
    unreachable -- but the row would exist, and the next person to widen the
    lookup would hand it the whole book."""
    assert signup(client, username=name).status_code == 409


@pytest.mark.parametrize(
    "bad", ["ab", "-leading", "has space", "has/slash", "Ünicode", "a" * 41]
)
def test_a_malformed_username_is_refused(client, bad):
    assert signup(client, username=bad).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("password", "short"),
        ("name", "L"),
        ("sanctioned", 0),
        ("sanctioned", -1),
        ("locality", "M"),
        ("built_up_sqft", 0),
    ],
)
def test_the_loan_fields_are_validated(client, field, value):
    assert signup(client, **{field: value}).status_code == 422


def test_signup_never_creates_a_lender(client):
    """There is no role field on the request, and there must not be one: staff
    access to the whole book is never self-served."""
    response = client.post(
        "/api/auth/signup", json={**NEW, "role": "bank", "loan_id": "all"}
    )
    assert response.status_code == 201
    assert response.json()["role"] == "owner"
    with SessionLocal() as db:
        assert db.scalar(select(models.User).where(models.User.role == "bank")) is None
