import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.evidence import Evidence

class EvidenceReferenceService:
    @staticmethod
    async def get_stable_mapping(db: AsyncSession, property_id: uuid.UUID) -> tuple[dict[str, str], dict[str, str], list[dict]]:
        """
        Loads all active (non-soft-deleted) evidence for a property, sorts them stably,
        and assigns a stable key like 'E1', 'E2', ...
        
        Returns:
            uuid_to_key: dict[str, str] mapping UUID string -> prompt key (e.g. 'E1')
            key_to_uuid: dict[str, str] mapping prompt key (e.g. 'E1') -> UUID string
            evidence_rows: list[dict] with 'id' (which is the stable key!), 'display_name', 'phase', 'room_label', 'notes'
        """
        result = await db.execute(
            select(Evidence)
            .where(Evidence.property_id == property_id, Evidence.deleted_at.is_(None))
            .order_by(Evidence.sort_order.asc(), Evidence.created_at.asc())
        )
        evidences = result.scalars().all()
        
        uuid_to_key = {}
        key_to_uuid = {}
        evidence_rows = []
        
        for idx, ev in enumerate(evidences, 1):
            key = f"E{idx}"
            ev_id_str = str(ev.id)
            
            uuid_to_key[ev_id_str] = key
            key_to_uuid[key] = ev_id_str
            
            evidence_rows.append({
                "id": key,  # Use stable key in prompt!
                "display_name": ev.display_name,
                "phase": ev.phase.value,
                "room_label": ev.room_label,
                "notes": ev.notes,
            })
            
        return uuid_to_key, key_to_uuid, evidence_rows
