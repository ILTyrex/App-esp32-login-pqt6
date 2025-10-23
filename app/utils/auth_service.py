"""Password helpers for the desktop app.

By default the server uses Werkzeug's generate_password_hash (PBKDF2), so to
be compatible we generate hashes with Werkzeug too. For legacy Argon2 hashes
we keep a verification fallback.
"""
from werkzeug.security import generate_password_hash, check_password_hash
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Return a password hash compatible with the server (Werkzeug/PBKDF2).

    We use Werkzeug's generate_password_hash so passwords created in the
    desktop app can be validated by the web backend (which uses the same
    function).
    """
    return generate_password_hash(password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify a plain password against a stored hash.

    First try Werkzeug's check_password_hash (server format). If that fails
    (invalid format or mismatch) we try Argon2 verification to support old
    desktop-only accounts migrated previously.
    """
    # Try Werkzeug/PBKDF2-style hashes first (this is what the server uses)
    try:
        return check_password_hash(hashed_password, plain_password)
    except Exception:
        # If Werkzeug can't verify (invalid format) or it's a mismatch, fall
        # back to Argon2 verification for legacy hashes created by older
        # desktop versions.
        try:
            return ph.verify(hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError, Exception):
            return False
