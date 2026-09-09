"""Password hashing for accounts a visitor creates.

The three provisioned accounts share one password from the environment, checked
with `compare_digest` -- a gate on a public demo URL, never a secret, and it is
printed in the runbook. Accounts created through sign-up are different: the
person choosing the password did not consent to it being readable, so these are
hashed even though the same demo will be thrown away.

`hashlib.scrypt` rather than a dependency: it is in the standard library, it is
memory-hard, and adding a password library to a backend that ships in a
container is a supply-chain decision this does not need. Parameters are
OWASP's interactive-login baseline (N=2^15, r=8, p=1) -- about 60ms here, which
is the point.

The stored form carries its own parameters, so raising the cost later does not
invalidate rows written today: verification reads N, r and p from the string it
is checking, not from this module.
"""

import hmac
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from hashlib import scrypt

# 2**14 is the exponent, stored rather than the derived N, so the string stays
# short and cannot express a value scrypt would refuse.
_LOG_N = 14
_R = 8
_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32
_SCHEME = "scrypt"


def _maxmem(n: int, r: int) -> int:
    """scrypt needs 128*N*r bytes, and OpenSSL refuses more than 32 MiB unless
    told otherwise -- which it does by raising "memory limit exceeded", not by
    picking safer parameters. Deriving the ceiling from the parameters being
    used, with headroom, keeps this working when the cost is raised and keeps
    verification working for rows written under the old cost.
    """
    return 2 * 128 * n * r


def _b64(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """`scrypt$logN$r$p$salt$key`, all base64url, no padding."""
    salt = secrets.token_bytes(_SALT_BYTES)
    n = 2**_LOG_N
    key = scrypt(
        password.encode(), salt=salt, n=n, r=_R, p=_P, dklen=_KEY_BYTES,
        maxmem=_maxmem(n, _R),
    )
    return f"{_SCHEME}${_LOG_N}${_R}${_P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> bool:
    """False for a wrong password AND for anything malformed.

    A stored value this cannot parse is a row written by a version that no
    longer exists, or a corrupted one. Either way the answer is no -- raising
    here would turn a bad row into a 500 on the login screen, which tells an
    attacker that the username exists.
    """
    try:
        scheme, log_n, r, p, salt, key = stored.split("$")
        if scheme != _SCHEME:
            return False
        n, r_int = 2 ** int(log_n), int(r)
        computed = scrypt(
            password.encode(),
            salt=_unb64(salt),
            n=n,
            r=r_int,
            p=int(p),
            dklen=len(_unb64(key)),
            maxmem=_maxmem(n, r_int),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(computed, _unb64(key))
