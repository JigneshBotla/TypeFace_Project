# app/api/v1/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import Generator, Optional
from app.db.session import get_db
from app.db import models
from app.services.security import decode_access_token
from app.core.config import settings
from jose import JWTError, jwt

oauth2_scheme = HTTPBearer()
security = HTTPBearer()  # re-uses the "Authorization: Bearer <token>" header


def get_db_dep() -> Generator[Session, None, None]:
    # get_db is a generator-yielding dependency in your project, use it directly
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme), db: Session = Depends(get_db_dep)) -> models.User:
    token = credentials.credentials
    # try your local helper decode first (it will raise on invalid tokens as appropriate)
    try:
        payload = decode_access_token(token)
    except Exception:
        # fallback to direct decode using secret if decode_access_token not present/valid
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token (no sub)")

    try:
        user_id = int(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user_from_bearer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_dep),
) -> models.User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token (no sub)")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    # convert to int safely
    try:
        uid = int(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
