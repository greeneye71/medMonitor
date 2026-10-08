"""Admin password (scrypt) and session check."""
import hashlib
import hmac
import os

from fastapi import Request

N, R, P = 2 ** 14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$")
    except (ValueError, AttributeError):
        return False
    if algo != "scrypt":
        return False
    h = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=N, r=R, p=P)
    return hmac.compare_digest(h.hex(), digest)


class NotAuthenticated(Exception):
    """Raised by require_admin; main.py turns it into a redirect to /login."""


def require_admin(request: Request) -> None:
    if not request.session.get("admin"):
        raise NotAuthenticated(request.url.path)
