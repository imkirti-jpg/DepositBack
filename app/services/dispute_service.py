import hashlib
import uuid
import logging
from datetime import datetime, timezone
from fastapi import UploadFile, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.db.database import SessionLocal
from app.models.dispute import Claim, ClaimLabel, DeductionNotice, NoticeStatus
from app.models.lease import Lease
from app.models.evidence import Evidence
from app.services.storage_service import StorageError, upload_file, download_file
from app.services.dispute_engine import analyze_notice
from app.services.ai_client import ai_client
from app.services.analytics import track

logger = logging.getLogger(__name__)

class DisputeService:
    @staticmethod
    async def create_notice(
        property_id: uuid.UUID,
        file: UploadFile | None,
        raw_text: str | None,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> DeductionNotice:
        # Compute notice hash
        notice_hash = None
        file_bytes = None
        if file:
            file_bytes = await file.read()
            await file.seek(0)  # reset pointer
            notice_hash = hashlib.sha256(file_bytes).hexdigest()
        elif raw_text:
            notice_hash = hashlib.sha256(raw_text.strip().encode("utf-8")).hexdigest()
            
        if not notice_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either a file upload or raw_text (or both).",
            )
            
        # Check if notice already exists for this property
        existing_res = await db.execute(
            select(DeductionNotice)
            .where(DeductionNotice.property_id == property_id, DeductionNotice.notice_hash == notice_hash)
            .order_by(DeductionNotice.created_at.desc())
            .limit(1)
        )
        existing_notice = existing_res.scalar_one_or_none()
        
        if existing_notice:
            if existing_notice.status in (NoticeStatus.processing, NoticeStatus.completed):
                logger.info(
                    "DisputeService.create_notice: Found existing notice %s with identical hash %s (status: %s). Reusing.",
                    existing_notice.id,
                    notice_hash,
                    existing_notice.status.value,
                )
                return existing_notice
                
        # Proceed to upload notice
        file_url = None
        if file:
            try:
                file_url = await upload_file(file, property_id=str(property_id), category="notices")
            except StorageError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
                
        notice = DeductionNotice(
            property_id=property_id,
            file_url=file_url,
            raw_text=raw_text,
            notice_hash=notice_hash,
            status=NoticeStatus.processing,
        )
        db.add(notice)
        await db.commit()
        await db.refresh(notice)
        
        background_tasks.add_task(DisputeService.run_analysis, notice.id)
        return notice

    @staticmethod
    async def reanalyze_notice(
        notice_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> DeductionNotice:
        result = await db.execute(select(DeductionNotice).where(DeductionNotice.id == notice_id))
        notice = result.scalar_one_or_none()
        if notice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")
            
        if notice.status == NoticeStatus.processing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Notice analysis is already in progress.",
            )
            
        logger.info("Notice %s status transition: %s -> processing (re-analysis)", notice.id, notice.status.value)
        notice.status = NoticeStatus.processing
        
        # Archive existing claims instead of deleting
        await db.execute(
            update(Claim)
            .where(Claim.deduction_notice_id == notice_id)
            .values(is_active=False)
        )
        
        db.add(notice)
        await db.commit()
        await db.refresh(notice)
        
        background_tasks.add_task(DisputeService.run_analysis, notice.id)
        return notice

    @staticmethod
    async def run_analysis(notice_id: uuid.UUID) -> None:
        async with SessionLocal() as db:
            result = await db.execute(select(DeductionNotice).where(DeductionNotice.id == notice_id))
            notice = result.scalar_one_or_none()
            if notice is None:
                logger.error("run_analysis: notice %s not found", notice_id)
                return
                
            # Check if property is deleted
            from app.models.property import Property
            prop_result = await db.execute(select(Property).where(Property.id == notice.property_id))
            prop = prop_result.scalar_one_or_none()
            if prop is None or prop.deleted_at is not None:
                logger.info("run_analysis: Property is soft-deleted, cancelling analysis job.")
                notice.status = NoticeStatus.failed
                await db.commit()
                return
                
            try:
                lease_result = await db.execute(
                    select(Lease)
                    .where(
                        Lease.property_id == notice.property_id,
                        Lease.extracted_fields.isnot(None),
                    )
                    .order_by(Lease.created_at.desc())
                    .limit(1)
                )
                lease = lease_result.scalar_one_or_none()
                
                from app.services.evidence_reference_service import EvidenceReferenceService
                uuid_to_key, key_to_uuid, evidence_rows = await EvidenceReferenceService.get_stable_mapping(db, notice.property_id)
                
                notice_file_bytes = None
                notice_mime_type = None
                if notice.file_url:
                    notice_file_bytes, notice_mime_type = download_file(notice.file_url)
                    
                analyzed_claims = await analyze_notice(
                    notice_text=notice.raw_text,
                    notice_file_bytes=notice_file_bytes,
                    notice_mime_type=notice_mime_type,
                    lease_fields=lease.extracted_fields if lease else None,
                    evidence_rows=evidence_rows,
                    ai_client=ai_client,
                    notice_id=str(notice.id),
                )
                
                supported_count = 0
                for item in analyzed_claims:
                    label_str = item.get("label", "unclear")
                    try:
                        label = ClaimLabel(label_str)
                    except ValueError:
                        label = ClaimLabel.unclear
                        
                    if label == ClaimLabel.supported:
                        supported_count += 1
                        
                    # Translate prompt keys back to database UUID strings
                    prompt_keys = item.get("evidence_refs", {}).get("evidence_ids", [])
                    db_uuids = [key_to_uuid[k] for k in prompt_keys if k in key_to_uuid]
                    
                    claim = Claim(
                        deduction_notice_id=notice.id,
                        item_description=item.get("item_description", ""),
                        claimed_amount=item.get("claimed_amount"),
                        label=label,
                        reasoning=item.get("reasoning", ""),
                        evidence_refs={
                            "lease_clauses": item.get("evidence_refs", {}).get("lease_clauses", []),
                            "evidence_ids": db_uuids,
                            "needed_evidence": item.get("evidence_refs", {}).get("needed_evidence", []),
                            "landlord_evidence": item.get("evidence_refs", {}).get("landlord_evidence", []),
                            "contract_status": item.get("evidence_refs", {}).get("contract_status", "not_allowed"),
                            "evidence_status": item.get("evidence_refs", {}).get("evidence_status", "missing"),
                        },
                        is_active=True,
                    )
                    db.add(claim)
                    
                old_status = notice.status
                notice.status = NoticeStatus.completed
                logger.info("Notice %s status transition: %s -> %s", notice.id, old_status.value, notice.status.value)
                await db.commit()
                
                await track(
                    db,
                    "claims_analyzed",
                    properties={
                        "notice_id": str(notice.id),
                        "claim_count": len(analyzed_claims),
                        "supported_count": supported_count,
                    },
                )
                
            except Exception as exc:
                logger.error("Analysis failed for notice %s: %s", notice_id, exc, exc_info=True)
                logger.info("Notice %s status transition: processing -> failed", notice.id)
                notice.status = NoticeStatus.failed
                db.add(notice)
                await db.commit()
