"""Sign in, sign out, and who am I.

No passwords anywhere, by design (spec §6.6): a role, a phone number, and the
loan the link was sent for. The OTP step is a screen concern in this phase; the
backend accepts the phone and issues the session cookie.
"""

import hmac

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api import accounts
from app.api.deps import (
    BANK_LOAN_SLOT,
    BANK_NAME,
    BANK_SUB,
    SESSION_COOKIE,
    CurrentUser,
    DbSession,
    Role,
    encode_cookie,
)
from app.db import models
from app.core.settings import get_settings

router = APIRouter(prefix="/api", tags=["auth"])

# A demo session, not a credential. Long enough that a demo never expires
# mid-walkthrough, short enough that a shared laptop forgets by tomorrow.
SESSION_MAX_AGE_S = 12 * 60 * 60

class LoginRequest(BaseModel):
    """A named demo account and the shared demo password.

    Was a phone number and a six-digit code that accepted any six digits — a
    flow nobody could narrate honestly, and one that mapped every owner onto
    loan 1001 however they signed in. See `app.api.accounts`.
    """

    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class AccountView(BaseModel):
    """One account the login screen can offer, so a visitor does not have to be
    told which username shows what."""

    username: str
    role: Role
    label: str


class LoginResponse(BaseModel):
    role: Role
    loan_id: str
    name: str


class MeResponse(BaseModel):
    role: Role
    loan_id: str
    name: str
    sub: str


def owner_sub(loan: models.Loan | None) -> str:
    """"Owner · Plot 47, Kompally" — the profile chip's second line."""
    if loan is None:
        return "Owner"
    return f"Owner · {loan.plot_label or loan.locality}"


@router.get("/auth/accounts", response_model=list[AccountView])
def list_accounts() -> list[AccountView]:
    """Which accounts exist, for the login screen's own hint list.

    Usernames only. No password, and nothing about the loans behind them beyond
    the label a visitor needs to choose.
    """
    if not get_settings().neev_demo_auth:
        return []
    return [
        AccountView(username=a.username, role=a.role, label=a.label)
        for a in accounts.DEMO_ACCOUNTS
    ]


@router.post("/auth/session", response_model=LoginResponse)
def create_session(body: LoginRequest, response: Response, db: DbSession) -> LoginResponse:
    settings = get_settings()
    if not settings.neev_demo_auth:
        raise HTTPException(403, "Demo sign-in is disabled. A verified identity provider is required.")

    account = accounts.find(body.username)
    # `compare_digest` on the password, and one message for both failures: a
    # login that says "no such user" tells anyone who asks which usernames
    # exist. It is a demo, but the habit is the point.
    password_ok = hmac.compare_digest(body.password, settings.neev_demo_password)
    if account is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That username and password do not match a demo account.",
        )

    if account.role == "bank":
        loan_id, name = BANK_LOAN_SLOT, BANK_NAME
    else:
        # The account names the loan, so a borrower signing in cannot land on
        # somebody else's contract. A loan the seed does not have is a 404
        # rather than a session that 404s on every request it makes.
        loan_id = account.loan_id
        loan = db.get(models.Loan, loan_id)
        if loan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No loan {loan_id}."
            )
        name = loan.borrower_name

    response.set_cookie(
        SESSION_COOKIE,
        encode_cookie(account.role, loan_id, name),
        max_age=SESSION_MAX_AGE_S,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return LoginResponse(role=account.role, loan_id=loan_id, name=name)


@router.delete("/auth/session", status_code=status.HTTP_204_NO_CONTENT)
def delete_session() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    # Same path the cookie was set on, or the browser keeps the old one.
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, db: DbSession) -> MeResponse:
    if user.role == "bank":
        return MeResponse(role="bank", loan_id=user.loan_id, name=user.name, sub=BANK_SUB)
    loan = db.get(models.Loan, user.loan_id)
    return MeResponse(
        role="owner",
        loan_id=user.loan_id,
        # The loan wins over the cookie: the cookie's name is client input and a
        # forged one must not be echoed back as the borrower's.
        name=loan.borrower_name if loan else user.name,
        sub=owner_sub(loan),
    )
