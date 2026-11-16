import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import SECRET_KEY, TOKEN_HOURS, get_db

# Without a configured key, tokens are signed with a per-process random key
# (valid until the server restarts) rather than a guessable default.
_KEY = SECRET_KEY or secrets.token_urlsafe(32)
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        candidate = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest))
    except ValueError:
        return False


def create_token(admin: models.Admin) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(admin.id), "exp": exp}, _KEY, algorithm="HS256")


def require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.Admin:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if creds is None:
        raise unauthorized
    try:
        payload = jwt.decode(creds.credentials, _KEY, algorithms=["HS256"])
        admin = db.get(models.Admin, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    if admin is None:
        raise unauthorized
    return admin
