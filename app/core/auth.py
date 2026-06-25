import uuid
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.database import get_db
from app.models.users import User

logger = logging.getLogger(__name__)


_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    user_id = _verify_token(token)
    return await _get_or_create_profile(db, user_id)


def _verify_token(token: str) -> uuid.UUID:
    """Verify the Supabase JWT and return the user's UUID from the `sub` claim."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing sub")
        return uuid.UUID(sub)
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def _get_or_create_profile(db: AsyncSession, user_id: uuid.UUID) -> User:
    """
    Load the profile for this user, creating it if it doesn't exist yet.
    This handles the case where a user logs in for the first time via Supabase
    Auth (client-side) but hasn't hit any API route that would create their row.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = User(id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        logger.info("Created new profile for user %s", user_id)

    return profile



"""
auth.py — FastAPI dependency that verifies a Supabase JWT and returns the
caller's Profile row, lazily creating it on first login.

Supabase issues HS256 JWTs signed with the project's JWT secret.
We never expose /auth/* routes — login/OTP happens entirely on the client
via the Supabase JS SDK. FastAPI only needs to verify the token on protected routes.

Usage in any router:
    from app.core.auth import get_current_user
    from app.models.profile import Profile

    @router.get("/me")
    async def me(current_user: Profile = Depends(get_current_user)):
        ...
"""