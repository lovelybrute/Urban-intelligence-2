"""
Urban Intelligence Platform - Auth API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, get_current_user, require_admin, decode_token
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role.value,
        username=user.username,
        full_name=user.full_name,
    )


@router.post("/register", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def register(request: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user (admin only in production)."""
    # Check if username exists
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if email exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile."""
    result = await db.execute(select(User).where(User.id == int(current_user["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account unavailable")
    return user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str | None = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an access token.

    Accepts the refresh token either as a query parameter or in a JSON body so
    clients can follow the standard bearer-token contract without breaking
    compatibility with existing callers.
    """
    token = refresh_token
    if token is None and request is not None:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        token = payload.get("refresh_token") if isinstance(payload, dict) else None
    if not token:
        raise HTTPException(status_code=400, detail="Refresh token is required")

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account unavailable")

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role.value}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        role=user.role.value,
        username=user.username,
        full_name=user.full_name,
    )
