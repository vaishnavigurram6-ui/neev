"""Sign in, sign up, sign out, and who am I.

Two ways to hold an account, and they are not the same mechanism:

  * The three provisioned accounts in `app.api.accounts` -- two borrowers and a
    credit officer -- share one password read from the environment. A gate on a
    public demo URL, printed in the runbook, never a secret.
  * An account created through `POST /auth/signup`, whose password the person
    chose and which is therefore hashed (`app.services.passwords`).

Sign-up creates BORROWERS only, each with their own loan. Staff access to the
whole book is never self-served, which is also what keeps the role in the
`users` table a lookup key rather than something a request can ask to be.
"""

import hmac
import re

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select

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
from app.services.passwords import hash_password, verify_password

router = APIRouter(prefix="/api", tags=["auth"])

# A demo session, not a credential. Long enough that a demo never expires
# mid-walkthrough, short enough that a shared laptop forgets by tomorrow.
SESSION_MAX_AGE_S = 12 * 60 * 60

class LoginRequest(BaseModel):
    """A username and a password, resolved against either mechanism.

    Either one of the three provisioned accounts plus the shared demo password,
    or an account somebody created through sign-up plus their own. The caller
    does not say which, and cannot: the answer decides the role.
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


USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")

# Sign-up must not be able to mint one of the provisioned names, or a visitor
# could create `officer` with a password of their choosing and then be resolved
# by the branch above it.
RESERVED_USERNAMES = frozenset(accounts.ACCOUNTS_BY_USERNAME) | {
    "admin", "root", "neev", "support", "bank", "officer", "owner",
}


class SignupRequest(BaseModel):
    """Everything needed to open an account and the loan behind it.

    The loan fields are here rather than on a later screen because a borrower
    with no loan has nothing to be shown: every owner screen reads
    `/api/loans/{id}`. A brand-new loan answers 200 with no tranches and no
    revisions, and the screens render that as "nothing checked yet".
    """

    name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=200)
    locality: str = Field(min_length=2, max_length=80)
    sanctioned: int = Field(gt=0, le=100_000_000)
    built_up_sqft: int | None = Field(default=None, gt=0, le=100_000)


def _normalize_username(raw: str) -> str:
    return raw.strip().lower()


def _next_loan_id(db: DbSession) -> str:
    """One past the highest numeric loan id.

    The seeded book is 1001-1010, so the first account created lands on 1011.
    Ids that are not numbers are ignored rather than crashing the signup: they
    are not something this repo creates, but a hand-edited database should not
    make the endpoint 500.
    """
    numeric = [
        int(row) for (row,) in db.execute(select(models.Loan.id)).all() if str(row).isdigit()
    ]
    return str(max(numeric, default=1000) + 1)


@router.post(
    "/auth/signup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
def create_account(body: SignupRequest, response: Response, db: DbSession) -> LoginResponse:
    settings = get_settings()
    if not settings.neev_demo_auth:
        raise HTTPException(403, "Sign-up is disabled. A verified identity provider is required.")

    username = _normalize_username(body.username)
    if not USERNAME_RE.match(username):
        raise HTTPException(
            422,
            "A username is 3-40 characters: lowercase letters, numbers, dot, "
            "dash or underscore, starting with a letter or number.",
        )
    # One message for reserved and taken alike. Which of the two it is would
    # tell a visitor that `officer` exists.
    taken = db.scalar(
        select(models.User).where(
            models.User.role == "owner", models.User.username == username
        )
    )
    if username in RESERVED_USERNAMES or taken is not None:
        raise HTTPException(409, "That username is not available. Please choose another.")

    loan_id = _next_loan_id(db)
    db.add(
        models.Loan(
            id=loan_id,
            borrower_name=body.name.strip(),
            locality=body.locality.strip(),
            built_up_sqft=body.built_up_sqft,
            sanctioned=body.sanctioned,
            disbursed=0,
            # Last on the officer's hotlist: nothing has been checked, so it has
            # no exposure to rank. A 0 here would put a brand-new loan at the
            # top of a list ordered worst-first.
            hotlist_rank=1_000,
        )
    )
    db.add(
        models.User(
            username=username,
            role="owner",
            loan_id=loan_id,
            password_hash=hash_password(body.password),
        )
    )
    db.commit()

    name = body.name.strip()
    response.set_cookie(
        SESSION_COOKIE,
        encode_cookie("owner", loan_id, name),
        max_age=SESSION_MAX_AGE_S,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return LoginResponse(role="owner", loan_id=loan_id, name=name)


@router.post("/auth/session", response_model=LoginResponse)
def create_session(body: LoginRequest, response: Response, db: DbSession) -> LoginResponse:
    settings = get_settings()
    if not settings.neev_demo_auth:
        raise HTTPException(403, "Demo sign-in is disabled. A verified identity provider is required.")

    username = _normalize_username(body.username)
    resolved: tuple[Role, str] | None = None

    # A provisioned account, against the shared gate. `compare_digest` because
    # comparing a secret with `==` leaks its length and prefix through timing.
    account = accounts.find(username)
    if account is not None and hmac.compare_digest(body.password, settings.neev_demo_password):
        resolved = (account.role, account.loan_id)
    else:
        # A self-created account. Scoped to the borrower book: sign-up makes
        # borrowers only, so the role is the key this lookup uses, never
        # something the request was allowed to ask for.
        user = db.scalar(
            select(models.User).where(
                models.User.role == "owner", models.User.username == username
            )
        )
        if user is not None and verify_password(body.password, user.password_hash):
            resolved = ("owner", user.loan_id)

    # One message for a wrong username, a wrong password, and either mechanism:
    # a login that says "no such user" tells anyone who asks which usernames
    # exist. It is a demo, but the habit is the point.
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That username and password do not match an account.",
        )
    role, account_loan_id = resolved

    if role == "bank":
        loan_id, name = BANK_LOAN_SLOT, BANK_NAME
    else:
        # The account names the loan, so a borrower signing in cannot land on
        # somebody else's contract. A loan the seed does not have is a 404
        # rather than a session that 404s on every request it makes.
        loan_id = account_loan_id
        loan = db.get(models.Loan, loan_id)
        if loan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No loan {loan_id}."
            )
        name = loan.borrower_name

    response.set_cookie(
        SESSION_COOKIE,
        encode_cookie(role, loan_id, name),
        max_age=SESSION_MAX_AGE_S,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return LoginResponse(role=role, loan_id=loan_id, name=name)


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
