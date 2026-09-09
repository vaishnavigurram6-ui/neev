"""Request-scoped dependencies: the database, the session, and the loan.

Sessions are signed, expiring sandbox sessions; login requires NEEV_DEMO_AUTH.
Every private API read/write requires a session and resource authorization.
This is NOT production identity verification: sandbox login still accepts a
chosen role and loan. A real identity provider remains a deployment gate.
Cookies contain role:loan:name:expiry:signature, and carry no "%" — see
`encode_cookie`. Next.js obtains verified identity from /api/me; its edge
cookie parsing is only a navigation hint.
"""

import hashlib
import hmac
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Annotated, Iterator, Literal

from fastapi import Depends, HTTPException, Path, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_session

SESSION_COOKIE = "neev_session"
_SESSION_KEY = secrets.token_bytes(32)  # single-process sandbox; restart signs everyone out

Role = Literal["owner", "bank"]

# The bank sees the whole book, so its cookie carries no single loan. The slot
# still has to be non-empty: the frontend treats an empty loan id as "no
# session" and redirects to /login.
BANK_LOAN_SLOT = "all"

BANK_NAME = "Anita Mehta"
BANK_SUB = "Credit officer · Hyderabad"


class SessionUser(BaseModel):
    """Who is calling. No `sub`: the profile chip's second line is derived from
    the loan, and GET /api/me is the one place that needs it — holding a
    placeholder here would let a second reader render "Owner" as if it were a
    real address."""

    role: Role
    loan_id: str
    name: str


def get_db() -> Iterator[Session]:
    yield from get_session()


DbSession = Annotated[Session, Depends(get_db)]


def _encode_name(name: str) -> str:
    """base64url, unpadded: the alphabet is `A-Za-z0-9-_`, so no "%" can appear."""
    return urlsafe_b64encode(name.encode()).decode().rstrip("=")


def _decode_name(encoded: str) -> str:
    """Lenient by design: a mangled name degrades to "" and never to a 500.

    The name is inside the signed payload, so anything that reaches here has
    already matched the signature — this only has to survive our own history
    of cookie formats without raising.
    """
    try:
        return urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
    except (ValueError, UnicodeDecodeError):
        return ""


def encode_cookie(role: Role, loan_id: str, name: str) -> str:
    """Signed `role:loan_id:name:expiry:signature`, the name in base64url.

    The name is encoded because it is the only field that can contain a colon
    or a non-ASCII character, and the frontend splits on ":" before decoding.

    It is base64url and *not* percent-encoded because the value must contain no
    "%": the frontend copies this cookie into Next's own jar, and the render
    Next performs in the same request after a server action's `redirect()`
    reads it back percent-decoded with no matching encode. "Ravi%20Kumar" came
    back as "Ravi Kumar" — a space, which both terminates a Cookie header value
    and is not what the signature covers — so every first login 401'd here and
    the owner layout bounced the visitor back to /login. A value with no "%" in
    it is unchanged by that extra decode. Pinned by
    `test_the_cookie_survives_a_percent_decode`.
    """
    payload = f"{role}:{loan_id}:{_encode_name(name)}:{int(time.time()) + 43200}"
    signature = hmac.new(_SESSION_KEY, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def _parse_cookie(raw: str | None) -> SessionUser | None:
    """A malformed cookie is "no session", never an exception.

    Every field is untrusted client input: an unknown role or a missing loan id
    means the caller is anonymous. `_decode_name` is lenient by design, so a
    mangled name degrades to the role's default and never to a 500.
    """
    if not raw:
        return None
    parts = raw.rsplit(":", 2)
    if len(parts) != 3:
        return None
    claims, expires, signature = parts
    expected = hmac.new(_SESSION_KEY, f"{claims}:{expires}".encode(), hashlib.sha256).hexdigest()
    if not signature.isascii() or not hmac.compare_digest(signature, expected):
        return None
    if not expires.isdigit() or int(expires) <= time.time():
        return None
    raw = claims
    role, _, rest = raw.partition(":")
    if role not in ("owner", "bank"):
        return None
    loan_id, _, encoded_name = rest.partition(":")
    if not loan_id:
        return None
    name = _decode_name(encoded_name)
    if role == "bank":
        return SessionUser(role="bank", loan_id=loan_id, name=name or BANK_NAME)
    return SessionUser(role="owner", loan_id=loan_id, name=name or "Owner")


def get_optional_user(request: Request) -> SessionUser | None:
    return _parse_cookie(request.cookies.get(SESSION_COOKIE))


OptionalUser = Annotated[SessionUser | None, Depends(get_optional_user)]


def get_current_user(request: Request) -> SessionUser:
    user = get_optional_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session. Sign in at POST /api/auth/session.",
        )
    return user


CurrentUser = Annotated[SessionUser, Depends(get_current_user)]

LoanId = Annotated[str, Path(description="The loan's id, e.g. 1001.")]


def get_loan(loan_id: LoanId, db: DbSession) -> models.Loan:
    """404 for an unknown loan — never a 500, never an empty object.

    An empty object would render a blank screen with a working header, which
    reads as "your loan has no data" rather than "no such loan".
    """
    loan = db.get(models.Loan, loan_id)
    if loan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No loan {loan_id}."
        )
    return loan


CurrentLoan = Annotated[models.Loan, Depends(get_loan)]


def get_authorized_loan(user: CurrentUser, loan: CurrentLoan) -> models.Loan:
    """Authenticated owners see only their loan; officers can read the book."""
    if user.role == "owner" and user.loan_id != loan.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This session is signed in for loan {user.loan_id}.",
        )
    return loan


AuthorizedLoan = Annotated[models.Loan, Depends(get_authorized_loan)]


def require_bank_reader(user: CurrentUser) -> SessionUser:
    """The lender-only book and builder screens reject owners and anonymous readers."""
    if user.role != "bank":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This view is for lenders. Your session is a borrower's.",
        )
    return user


BankReader = Annotated[SessionUser, Depends(require_bank_reader)]


def require_bank_officer(user: CurrentUser) -> SessionUser:
    """Only an authenticated lender can record a credit decision."""
    if user.role != "bank":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a lender may decide a tranche.",
        )
    return user


BankOfficer = Annotated[SessionUser, Depends(require_bank_officer)]


def get_tranche(
    tranche_number: Annotated[int, Path(ge=1, description="1-based tranche number.")],
    loan: AuthorizedLoan,
) -> models.Tranche:
    tranche = next((t for t in loan.tranches if t.number == tranche_number), None)
    if tranche is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan {loan.id} has no tranche {tranche_number}.",
        )
    return tranche


CurrentTranche = Annotated[models.Tranche, Depends(get_tranche)]
