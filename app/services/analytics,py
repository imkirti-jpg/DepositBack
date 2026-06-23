from __future__ import annotations
import logging
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analytics import AnalyticsEvent

logger = logging.getLogger(__name__)


async def track(
    db: AsyncSession,
    event_name: str,
    *,
    user_id: str | uuid.UUID | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    try:
        uid = uuid.UUID(str(user_id)) if user_id else None
        event = AnalyticsEvent(user_id=uid, event_name=event_name, properties=properties or {})
        db.add(event)
        await db.commit()
    except Exception:
        logger.exception("analytics.track failed for event '%s'", event_name)