# app/utils/auth_service.py
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Configuración del hasher
ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Devuelve el hash Argon2 de la contraseña."""
    return ph.hash(password)

def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False
