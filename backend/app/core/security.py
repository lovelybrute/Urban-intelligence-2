"""
Urban Intelligence Platform - Security & Authentication
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy import select
from app.db.session import get_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# Bearer token scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db=Depends(get_db)) -> Dict[str, Any]:
    """Dependency to get the current authenticated user from JWT."""
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    from app.models.models import User
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account unavailable")
    payload["role"] = user.role.value
    return payload


async def require_write(request: Request, user=Depends(get_current_user)):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and user.get("role") not in {
        "admin", "command_center", "transport_authority", "road_maintenance"
    }:
        raise HTTPException(status_code=403, detail="This account has read-only access")


class RoleChecker:
    """Dependency for role-based access control."""

    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Dict[str, Any] = Depends(get_current_user)):
        if user.get("role") not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user


# Role constants
ROLES = {
    "ADMIN": "admin",
    "COMMAND_CENTER": "command_center",
    "TRANSPORT_AUTHORITY": "transport_authority",
    "ROAD_MAINTENANCE": "road_maintenance",
    "ANALYST": "analyst",
    "VIEWER": "viewer",
}

# Permission presets
require_admin = RoleChecker([ROLES["ADMIN"]])
require_operator = RoleChecker([ROLES["ADMIN"], ROLES["COMMAND_CENTER"]])
require_authority = RoleChecker([ROLES["ADMIN"], ROLES["COMMAND_CENTER"], ROLES["TRANSPORT_AUTHORITY"]])
require_analyst = RoleChecker([ROLES["ADMIN"], ROLES["ANALYST"], ROLES["COMMAND_CENTER"]])
require_authenticated = RoleChecker(list(ROLES.values()))
