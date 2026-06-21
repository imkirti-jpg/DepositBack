from supabase import create_async_client, AsyncClient
import os
from app.core.config import settings

_supabase_client: AsyncClient | None = None

async def get_supabase_client() -> AsyncClient:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = await create_async_client(
            settings.DATABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY  # server-side only
        )
    return _supabase_client