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


# Nueva función: convertir valor del sensor a etiqueta en español
def sensor_label(sensor_value) -> str:
    """Convertir el valor del sensor a etiqueta en español.

    - True / "ON" / "1"  -> "Bloqueado"
    - False / "OFF" / "0" -> "Libre"
    - None / desconocido  -> "Desconocido"
    """
    if sensor_value is None:
        return "Desconocido"
    # booleano
    if isinstance(sensor_value, bool):
        return "Bloqueado" if sensor_value else "Libre"
    # string / num
    s = str(sensor_value).strip().lower()
    if s in ("on", "1", "true", "bloqueado"):
        return "Bloqueado"
    if s in ("off", "0", "false", "libre"):
        return "Libre"
    return "Desconocido"
