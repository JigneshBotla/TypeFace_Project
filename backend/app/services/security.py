# app/services/security.py
"""Password hashing + JWT helpers.

We use passlib pbkdf2_sha256 (pure-python) to avoid Windows bcrypt issues.
JWT encode/decode uses python-jose for consistency with other modules.
"""
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.core.config import settings

# Use pbkdf2_sha256 to avoid bcrypt backend problems on some Windows setups.
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60))
SECRET_KEY = getattr(settings, "SECRET_KEY", "change-me-in-prod")  # ensure it's present in env in prod


def hash_password(password: str) -> str:
    """Hash a plaintext password (never store plaintext)."""
    if password is None:
        raise ValueError("password cannot be None")
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against hashed. Returns False on any error."""
    if plain is None or hashed is None:
        return False
    try:
        return pwd_ctx.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token with subject (user id usually).
    - subject is stored under 'sub' as a string
    - 'iat' and 'exp' included (exp as int timestamp)
    """
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT. Raises JWTError on invalid token.
    Returns the payload dict (contains 'sub', 'exp', etc).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # token is valid; return payload
        return payload
    except JWTError:
        # re-raise so caller/deps can convert to HTTPException
        raise
