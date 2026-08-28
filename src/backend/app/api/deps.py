"""Request-scoped dependencies: the database, the session, and the loan.

Auth is a mocked session with a real boundary. The cookie is fake — no OTP, no
signature — but the dependency, the 401, and the owner/loan check are real, so
dropping in genuine auth later means replacing `_parse_cookie` and nothing else.

The cookie's wire format is `role:loan_id:percent-encoded-name`, which is what
`src/frontend/lib/session.ts` and `src/frontend/proxy.ts` already parse. Any
change here is a change there.

TO RECONCILE (frontend side, Task 14): the two readers derive different text
from the same cookie. `readSession()` renders the officer's sub-line as
"Credit officer · Retail assets" and defaults an unnamed owner to "Ravi Kumar";
this module uses the Contractor Scorecard mockup's "Credit officer · Hyderabad"
and defaults to "Owner". The mockups are authoritative on copy, so the frontend
is the side to change. `decodeURIComponent` also throws on a lone "%" where
Python's `unquote` does not, so a mangled cookie is a session here and no
session there — harmless while the two agree on role and loan id, but the
divergence is worth closing when the cookie stops being a mock.
"""

from typing import Annotated, Iterator, Literal
from urllib.parse import quote, unquote

from fastapi import Depends, HTTPException, Path, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_session

SESSION_COOKIE = "neev_session"

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


def encode_cookie(role: Role, loan_id: str, name: str) -> str:
    """`role:loan_id:name`, with the name percent-encoded.

    The name is encoded because it is the only field that can contain a colon
    or a non-ASCII character, and the frontend splits on ":" before decoding.
    """
    return f"{role}:{loan_id}:{quote(name, safe='')}"


def _parse_cookie(raw: str | None) -> SessionUser | None:
    """A malformed cookie is "no session", never an exception.

    Every field is untrusted client input: an unknown role or a missing loan id
    means the caller is anonymous. `unquote` is lenient by design — it leaves a
    stray "%" alone rather than raising — so a mangled name degrades to a
    mangled name and never to a 500.
    """
    if not raw:
        return None
    role, _, rest = raw.partition(":")
    if role not in ("owner", "bank"):
        return None
    loan_id, _, encoded_name = rest.partition(":")
    if not loan_id:
        return None
    name = unquote(encoded_name)
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


def get_authorized_loan(loan: CurrentLoan, user: OptionalUser) -> models.Loan:
    """The owner/loan boundary, exercised even though the session is mocked.

    Role alone is not authorization: an owner signed in for loan 1001 must not
    read loan 1002. A bank officer legitimately reads any loan in the book, so
    the check is owner-side only. An anonymous request is allowed through to the
    same data the frontend's middleware already gates — the cookie is not a
    credential in this phase, and pretending otherwise would only mean the
    reader's own browser could forge it.
    """
    if user is not None and user.role == "owner" and user.loan_id != loan.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This session is signed in for loan {user.loan_id}.",
        )
    return loan


AuthorizedLoan = Annotated[models.Loan, Depends(get_authorized_loan)]


def require_bank_reader(user: OptionalUser) -> SessionUser | None:
    """The bank's own screens: the whole book, and the builders behind it.

    An owner session is refused outright — the hotlist names every borrower in
    the book, so letting one borrower's session read it would undo the
    owner/loan boundary `get_authorized_loan` enforces one loan at a time.
    Anonymous is allowed through, for the same reason loan reads are (see the
    module docstring in app/api/__init__.py).
    """
    if user is not None and user.role != "bank":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This view is for lenders. Your session is a borrower's.",
        )
    return user


BankReader = Annotated[SessionUser | None, Depends(require_bank_reader)]


def require_bank_officer(user: CurrentUser) -> SessionUser:
    """A real bank session, required. Used for writes, not reads.

    Reads are open in this phase because the cookie is not yet a credential.
    A write is different: a tranche decision goes into the loan file under
    somebody's name, so it needs a session to attribute it to and that session
    has to be a lender's. Without this an owner could release their own tranche
    and be recorded as the officer who approved it.
    """
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
