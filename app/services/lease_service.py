import hashlib
import uuid
import logging
from datetime import datetime, timezone
from fastapi import UploadFile, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.lease import Lease, LeaseStatus
from app.services.storage_service import StorageError, upload_file, download_file
from app.services.lease_extractor import extract_lease_fields
from app.services.ai_client import ai_client
from app.services.analytics import track

logger = logging.getLogger(__name__)

class LeaseService:
    @staticmethod
    async def create_lease(
        property_id: uuid.UUID,
        file: UploadFile,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> Lease:
        # Read file bytes to compute SHA-256 hash
        file_bytes = await file.read()
        await file.seek(0)  # reset file pointer for storage service
        
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Check if an identical lease already exists for this property
        existing_res = await db.execute(
            select(Lease)
            .where(Lease.property_id == property_id, Lease.file_hash == file_hash)
            .order_by(Lease.created_at.desc())
            .limit(1)
        )
        existing_lease = existing_res.scalar_one_or_none()
        
        if existing_lease:
            # If the existing lease is in needs_review, confirmed, or processing, reuse it!
            if existing_lease.status in (LeaseStatus.processing, LeaseStatus.needs_review, LeaseStatus.confirmed):
                logger.info(
                    "LeaseService.create_lease: Found existing lease %s with identical file hash %s (status: %s). Reusing.",
                    existing_lease.id,
                    file_hash,
                    existing_lease.status.value,
                )
                return existing_lease
        
        # If no reusable lease exists, proceed with upload and new record creation
        try:
            file_url = await upload_file(file, property_id=str(property_id), category="leases")
        except StorageError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            
        lease = Lease(property_id=property_id, file_url=file_url, file_hash=file_hash, status=LeaseStatus.processing)
        db.add(lease)
        await db.commit()
        await db.refresh(lease)
        
        background_tasks.add_task(LeaseService.run_extraction, lease.id, file_url)
        return lease

    @staticmethod
    async def reextract_lease(
        lease_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> Lease:
        result = await db.execute(select(Lease).where(Lease.id == lease_id))
        lease = result.scalar_one_or_none()
        if lease is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found")
            
        if lease.status == LeaseStatus.processing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Extraction is already in progress for this lease.",
            )
            
        logger.info("Lease %s status transition: %s -> processing (re-extraction)", lease.id, lease.status.value)
        lease.status = LeaseStatus.processing
        lease.updated_at = datetime.now(timezone.utc)
        db.add(lease)
        await db.commit()
        await db.refresh(lease)
        
        background_tasks.add_task(LeaseService.run_extraction, lease.id, lease.file_url)
        return lease

    @staticmethod
    async def run_extraction(lease_id: uuid.UUID, file_url: str) -> None:
        async with SessionLocal() as db:
            result = await db.execute(select(Lease).where(Lease.id == lease_id))
            lease = result.scalar_one_or_none()
            if lease is None:
                logger.error("run_extraction: lease %s not found", lease_id)
                return
                
            # Check if property is deleted
            from app.models.property import Property
            prop_result = await db.execute(select(Property).where(Property.id == lease.property_id))
            prop = prop_result.scalar_one_or_none()
            if prop is None or prop.deleted_at is not None:
                logger.info("run_extraction: Property is soft-deleted, cancelling extraction job.")
                lease.status = LeaseStatus.failed
                await db.commit()
                return
                
            try:
                file_bytes, mime_type = download_file(file_url)
                extracted = await extract_lease_fields(file_bytes, mime_type, ai_client, lease_id=lease_id)
                
                lease.extracted_fields = extracted
                is_complete = all([
                    extracted.get("tenant_name") not in (None, "", "Not found in provided documents."),
                    extracted.get("landlord_name") not in (None, "", "Not found in provided documents."),
                    extracted.get("monthly_rent") not in (None, "", "Not found in provided documents."),
                    extracted.get("security_deposit") not in (None, "", "Not found in provided documents.")
                ])
                old_status = lease.status
                lease.status = LeaseStatus.confirmed if is_complete else LeaseStatus.needs_review
                logger.info("Lease %s status transition: %s -> %s", lease.id, old_status.value, lease.status.value)
                
            except Exception as exc:
                logger.error("Extraction failed for lease %s: %s", lease_id, exc, exc_info=True)
                logger.info("Lease %s status transition: processing -> failed", lease.id)
                lease.status = LeaseStatus.failed
                
            lease.updated_at = datetime.now(timezone.utc)
            db.add(lease)
            await db.commit()
            
            await track(
                db,
                "lease_extraction_completed",
                properties={"lease_id": str(lease_id), "status": lease.status.value},
            )
