"""Sign in, sign out, and who am I.

No passwords anywhere, by design (spec §6.6): a role, a phone number, and the
loan the link was sent for. The OTP step is a screen concern in this phase; the
backend accepts the phone and issues the session cookie.
"""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

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

# With no OTP and no phone column, a phone number cannot identify a loan, so an
# owner signing in without one lands on the golden case. This is a demo
# affordance and disappears the moment real auth resolves phone -> borrower.
DEMO_OWNER_LOAN_ID = "1001"


class LoginRequest(BaseModel):
    role: Role
    # Indian mobile numbers are ten digits. Validated because the login screen's
    # inline validation must have something real to agree with.
    phone: str = Field(pattern=r"^\d{10}$")
    loan_id: str | None = None


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


@router.post("/auth/session", response_model=LoginResponse)
def create_session(body: LoginRequest, response: Response, db: DbSession) -> LoginResponse:
    if not get_settings().neev_demo_auth:
        raise HTTPException(403, "Demo sign-in is disabled. A verified identity provider is required.")
    if body.role == "bank":
        loan_id, name = BANK_LOAN_SLOT, BANK_NAME
    else:
        # An owner signs in against a specific loan — the one the bank's link
        # named. Signing in for a loan that does not exist is a 404, not a
        # session that 404s on every subsequent request.
        loan_id = body.loan_id or DEMO_OWNER_LOAN_ID
        loan = db.get(models.Loan, loan_id)
        if loan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No loan {loan_id}."
            )
        name = loan.borrower_name

    response.set_cookie(
        SESSION_COOKIE,
        encode_cookie(body.role, loan_id, name),
        max_age=SESSION_MAX_AGE_S,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return LoginResponse(role=body.role, loan_id=loan_id, name=name)


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
