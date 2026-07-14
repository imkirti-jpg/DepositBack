import hashlib
import uuid
import logging
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.evidence import Evidence, EvidencePhase
from app.services.storage_service import upload_file, delete_file, StorageError
from app.services.analytics import track

logger = logging.getLogger(__name__)

class EvidenceService:
    _VALID_CATEGORIES = {"move_in", "move_out", "damage", "receipt"}

    @staticmethod
    async def generate_display_name(db: AsyncSession, property_id: uuid.UUID, category: str, room_label: str | None) -> str:
        # Count existing items of same category and room in this property
        query = select(func.count(Evidence.id)).where(
            Evidence.property_id == property_id,
            Evidence.category == category,
            Evidence.deleted_at.is_(None)
        )
        if room_label:
            query = query.where(Evidence.room_label == room_label.strip())
            
        count = await db.scalar(query) or 0
        index = count + 1
        
        # Format name
        if category in ("move_in", "move_out"):
            phase_str = "Move-in" if category == "move_in" else "Move-out"
            if room_label:
                return f"{phase_str} {room_label.strip().title()} Photo {index}"
            else:
                return f"{phase_str} Photo {index}"
        elif category == "damage":
            if room_label:
                return f"Damage {room_label.strip().title()} Photo {index}"
            return f"Damage Photo {index}"
        elif category == "receipt":
            return f"Receipt {index}"
        else:
            raise ValueError(f"Unsupported evidence category: {category}")

    @staticmethod
    async def upload_evidence(
        property_id: uuid.UUID,
        category: str,
        file: UploadFile,
        room_label: str | None,
        notes: str | None,
        db: AsyncSession,
    ) -> Evidence:
        if category not in EvidenceService._VALID_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid evidence category. Must be one of: {', '.join(EvidenceService._VALID_CATEGORIES)}."
            )
            
        # Read file bytes to check duplicate hash
        file_bytes = await file.read()
        file_size = len(file_bytes)
        await file.seek(0)  # reset pointer for storage service
        
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Check if identical evidence already exists for this property
        existing_res = await db.execute(
            select(Evidence)
            .where(Evidence.property_id == property_id, Evidence.file_hash == file_hash)
            .order_by(Evidence.created_at.desc())
            .limit(1)
        )
        existing = existing_res.scalar_one_or_none()
        
        if existing:
            if existing.deleted_at is not None:
                # Restore the soft-deleted evidence record!
                existing.deleted_at = None
                existing.deleted_by = None
                existing.category = category
                existing.room_label = room_label.strip() if room_label else None
                existing.notes = notes
                existing.display_name = await EvidenceService.generate_display_name(db, property_id, category, room_label)
                db.add(existing)
                await db.commit()
                await db.refresh(existing)
                logger.info("EvidenceService.upload_evidence: Restored soft-deleted duplicate evidence %s.", existing.id)
                return existing
            else:
                logger.info("EvidenceService.upload_evidence: Found duplicate evidence %s. Reusing.", existing.id)
                return existing
                
        # Determine phase based on category for backwards compatibility
        phase = EvidencePhase.move_in
        if category == "move_out":
            phase = EvidencePhase.move_out
            
        mime_type = file.content_type
        
        # Upload
        try:
            storage_category = f"evidence/{category}"
            file_url = await upload_file(file, property_id=str(property_id), category=storage_category)
        except StorageError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            
        # Get next sort order value
        order_query = select(func.max(Evidence.sort_order)).where(
            Evidence.property_id == property_id,
            Evidence.category == category,
            Evidence.deleted_at.is_(None)
        )
        max_order = await db.scalar(order_query) or 0
        sort_order = max_order + 1
        
        # Generate display name
        display_name = await EvidenceService.generate_display_name(db, property_id, category, room_label)
        
        evidence = Evidence(
            property_id=property_id,
            phase=phase,
            room_label=room_label.strip() if room_label else None,
            file_url=file_url,
            file_hash=file_hash,
            notes=notes,
            display_name=display_name,
            category=category,
            sort_order=sort_order,
            mime_type=mime_type,
            file_size=file_size,
        )
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)
        return evidence

    @staticmethod
    async def replace_evidence(
        evidence_id: uuid.UUID,
        file: UploadFile,
        db: AsyncSession,
    ) -> Evidence:
        result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
        evidence = result.scalar_one_or_none()
        if not evidence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
            
        # Read file bytes to check duplicate hash
        file_bytes = await file.read()
        file_size = len(file_bytes)
        await file.seek(0)
        
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        old_file_url = evidence.file_url
        
        # Upload new file
        try:
            storage_category = f"evidence/{evidence.category}"
            new_file_url = await upload_file(file, property_id=str(evidence.property_id), category=storage_category)
        except StorageError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            
        # Update record details
        evidence.file_url = new_file_url
        evidence.file_hash = file_hash
        evidence.mime_type = file.content_type
        evidence.file_size = file_size
        evidence.created_at = datetime.now(timezone.utc)
        
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)
        
        # Clean up Supabase storage
        try:
            delete_file(old_file_url)
        except Exception as exc:
            logger.warning("Failed to delete replaced storage file %s: %s", old_file_url, exc)
            
        return evidence

    @staticmethod
    async def soft_delete_evidence(
        evidence_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
        evidence = result.scalar_one_or_none()
        if not evidence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
            
        evidence.deleted_at = datetime.now(timezone.utc)
        evidence.deleted_by = user_id
        db.add(evidence)
        await db.commit()

    @staticmethod
    async def restore_evidence(
        evidence_id: uuid.UUID,
        db: AsyncSession,
    ) -> Evidence:
        result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
        evidence = result.scalar_one_or_none()
        if not evidence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
            
        evidence.deleted_at = None
        evidence.deleted_by = None
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)
        return evidence
