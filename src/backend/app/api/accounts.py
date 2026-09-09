"""The demo accounts a visitor can sign in as.

Replaces a phone number and a six-digit code that accepted any six digits. That
flow was hard to narrate — "type any number, then any code" — and it mapped
every owner onto the same loan however they signed in, so two people in a demo
overwrote each other's work without knowing it.

Named accounts fix both. A username picks an identity, and the identity picks a
loan, so `ravi` and `prasad` are two borrowers with two contracts and cannot
collide. It also makes the deployed URL harder to walk into: a crawler that
found it could previously sign in with any ten digits and start analyses that
cost money.

This is still NOT identity verification. There is one shared password, it is
printed in the runbook, and it is a gate rather than a secret. Real identity
means a phone column on `Loan` and an OTP provider, and the seam for it is
`GET /api/me`: every screen reads who it is talking to from there, so a provider
drops in without a screen changing.
"""

from dataclasses import dataclass

from app.api.deps import BANK_LOAN_SLOT, Role


@dataclass(frozen=True)
class DemoAccount:
    username: str
    role: Role
    # The loan this identity holds. `BANK_LOAN_SLOT` for a lender, who reads the
    # whole book rather than one contract.
    loan_id: str
    # What the login screen offers as a hint, so a judge does not have to be
    # told which account shows what.
    label: str


# Only 1001 and 1002 have a recorded pipeline run behind them, so those are the
# only two borrowers worth signing in as: any other loan would land a visitor on
# a contract screen with nothing to show.
DEMO_ACCOUNTS: tuple[DemoAccount, ...] = (
    DemoAccount(
        username="ravi",
        role="owner",
        loan_id="1001",
        label="Ravi Kumar — the flagged contract (Plot 47, Kompally)",
    ),
    DemoAccount(
        username="prasad",
        role="owner",
        loan_id="1002",
        label="D. Prasad — the clean contract (Kukatpally)",
    ),
    DemoAccount(
        username="officer",
        role="bank",
        loan_id=BANK_LOAN_SLOT,
        label="Credit officer — the whole book",
    ),
)

ACCOUNTS_BY_USERNAME = {account.username: account for account in DEMO_ACCOUNTS}


def find(username: str) -> DemoAccount | None:
    """Case- and space-insensitive, because people type their own name loosely
    and a demo should not fail on a capital letter."""
    return ACCOUNTS_BY_USERNAME.get(username.strip().lower())
