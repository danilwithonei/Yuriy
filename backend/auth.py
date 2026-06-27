from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
import os
import re

from database import engine
from models import Lawyer

security = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_token(lawyer_id: int) -> str:
    expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=EXPIRE_MINUTES)
    to_encode = {"sub": str(lawyer_id), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return int(sub)
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_lawyer_or_none(token: str) -> int | None:
    try:
        return decode_token(token)
    except HTTPException:
        return None

async def get_optional_lawyer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int | None:
    if credentials is None:
        return None
    return decode_token(credentials.credentials)

async def get_current_lawyer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    return decode_token(credentials.credentials)

def get_lawyer_by_email(session: Session, email: str) -> Lawyer | None:
    return session.exec(select(Lawyer).where(Lawyer.email == email)).first()

def validate_email(email: str) -> str | None:
    if not re.match(EMAIL_REGEX, email):
        return "Invalid email format"
    return None
