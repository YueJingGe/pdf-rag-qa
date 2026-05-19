"""Authentication and authorization utilities."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import get_db
from app.models.user import User, KnowledgeBasePermission

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user from JWT token. Returns None if no token."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub", 0))
        if not user_id:
            return None
    except JWTError:
        return None
    user = await db.get(User, user_id)
    if user and not user.is_active:
        return None
    return user


async def require_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authenticated user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: User = Depends(require_user),
) -> User:
    """Require admin user."""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


async def check_kb_permission(
    user_id: int,
    knowledge_base_id: int,
    required_role: str,
    db: AsyncSession,
) -> bool:
    """Check if user has the required role on a knowledge base.
    
    Role hierarchy: owner > member > viewer
    """
    role_levels = {"viewer": 1, "member": 2, "owner": 3}
    required_level = role_levels.get(required_role, 0)

    result = await db.execute(
        select(KnowledgeBasePermission)
        .where(
            KnowledgeBasePermission.user_id == user_id,
            KnowledgeBasePermission.knowledge_base_id == knowledge_base_id,
        )
    )
    permission = result.scalar_one_or_none()
    if not permission:
        return False
    return role_levels.get(permission.role, 0) >= required_level
