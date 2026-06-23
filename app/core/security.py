import httpx
import jwt

from app.core.config import settings


_jwks_cache = None


async def get_jwks():

    global _jwks_cache

    if _jwks_cache:
        return _jwks_cache

    async with httpx.AsyncClient() as client:

        response = await client.get(
            settings.SUPABASE_JWKS_URL
        )

        response.raise_for_status()

        _jwks_cache = response.json()

    return _jwks_cache


from functools import lru_cache

from jwt import PyJWKClient

from app.core.config import settings


@lru_cache
def get_jwks_client() -> PyJWKClient:
    return PyJWKClient(
        f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    )