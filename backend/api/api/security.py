import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_ph = PasswordHasher()
_HASH_FITTIZIO = _ph.hash("password-fittizia-per-tempi-costanti")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verifica_password(password_hash: str | None, password: str) -> bool:
    """Verifica sempre un hash (anche fittizio) per non rivelare se l'utente esiste."""
    try:
        ok = _ph.verify(password_hash or _HASH_FITTIZIO, password)
    except (VerificationError, InvalidHashError):
        return False
    return ok and password_hash is not None


def nuovo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
