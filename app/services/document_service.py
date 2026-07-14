import uuid
import logging
from datetime import datetime, timezone
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.database import SessionLocal
from app.models.documents import GeneratedDocument, DocStatus
from app.models.dispute import Claim, DeductionNotice
from app.models.property import Property
from app.models.lease import Lease
from app.models.evidence import Evidence
from app.services.ai_client import ai_client
from app.services.analytics import track
from app.services.document_generator import generate_document

logger = logging.getLogger(__name__)

class DocumentService:
    @staticmethod
    async def create_document(
        property_id: uuid.UUID,
        deduction_notice_id: uuid.UUID,
        doc_type: str,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> GeneratedDocument:
        # Check if an active document of the same type already exists for this notice
        existing_res = await db.execute(
            select(GeneratedDocument)
            .where(
                GeneratedDocument.property_id == property_id,
                GeneratedDocument.deduction_notice_id == deduction_notice_id,
                GeneratedDocument.doc_type == doc_type,
                GeneratedDocument.is_active == True,
            )
            .order_by(GeneratedDocument.created_at.desc())
            .limit(1)
        )
        existing_doc = existing_res.scalar_one_or_none()
        
        if existing_doc:
            if existing_doc.status in (DocStatus.processing, DocStatus.draft, DocStatus.sent):
                logger.info(
                    "DocumentService.create_document: Found existing active document %s (status: %s). Reusing.",
                    existing_doc.id,
                    existing_doc.status.value,
                )
                return existing_doc
                
        # Create a new generated document record
        doc = GeneratedDocument(
            property_id=property_id,
            deduction_notice_id=deduction_notice_id,
            doc_type=doc_type,
            status=DocStatus.processing,
            is_active=True,
        )
        logger.info("GeneratedDocument %s status transition: initialized -> processing", doc.id)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        background_tasks.add_task(DocumentService.run_generation, doc.id)
        return doc

    @staticmethod
    async def regenerate_document(
        doc_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> GeneratedDocument:
        # Load the existing document
        result = await db.execute(select(GeneratedDocument).where(GeneratedDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
            
        if doc.status == DocStatus.processing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document generation is already in progress.",
            )
            
        logger.info("DocumentService.regenerate_document: Archiving document %s and triggering new draft.", doc.id)
        
        # Archive previous active document
        doc.is_active = False
        db.add(doc)
        await db.commit()
        
        # Create a fresh new document of the same type and notice
        return await DocumentService.create_document(
            property_id=doc.property_id,
            deduction_notice_id=doc.deduction_notice_id,
            doc_type=doc.doc_type.value,
            background_tasks=background_tasks,
            db=db,
        )

    @staticmethod
    async def run_generation(doc_id: uuid.UUID) -> None:
        async with SessionLocal() as db:
            result = await db.execute(select(GeneratedDocument).where(GeneratedDocument.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc is None:
                logger.error("run_generation: document %s not found", doc_id)
                return
                
            try:
                # Load property details
                prop_result = await db.execute(select(Property).where(Property.id == doc.property_id))
                prop = prop_result.scalar_one_or_none()
                if prop is None or prop.deleted_at is not None:
                    logger.info("run_generation: Property is soft-deleted, cancelling generation job.")
                    doc.status = DocStatus.failed
                    await db.commit()
                    return
                
                # Load lease
                lease_result = await db.execute(
                    select(Lease)
                    .where(Lease.property_id == doc.property_id)
                    .order_by(Lease.created_at.desc())
                    .limit(1)
                )
                lease = lease_result.scalar_one_or_none()
                
                # Load active claims
                claims_result = await db.execute(
                    select(Claim)
                    .where(Claim.deduction_notice_id == doc.deduction_notice_id, Claim.is_active == True)
                    .order_by(Claim.created_at.asc())
                )
                claims = claims_result.scalars().all()

                # Load all evidence for the property to map UUIDs -> display_name
                ev_res = await db.execute(
                    select(Evidence).where(Evidence.property_id == doc.property_id)
                )
                ev_map = {str(ev.id): ev.display_name for ev in ev_res.scalars().all()}

                claims_data = []
                for c in claims:
                    refs = dict(c.evidence_refs) if c.evidence_refs else {}
                    ev_ids = refs.get("evidence_ids", [])
                    # Translate database UUIDs to display names
                    friendly_names = [ev_map[eid] for eid in ev_ids if eid in ev_map]

                    claims_data.append({
                        "item_description": c.item_description,
                        "claimed_amount": float(c.claimed_amount) if c.claimed_amount else None,
                        "reasoning": c.reasoning,
                        "evidence_refs": {
                            "lease_clauses": refs.get("lease_clauses", []),
                            "evidence_ids": friendly_names,
                            "needed_evidence": refs.get("needed_evidence", []),
                        },
                        "effective_label": (c.user_override_label or c.label).value,
                    })
                
                result_data = await generate_document(
                    doc_type=doc.doc_type.value,
                    claims=claims_data,
                    lease_fields=lease.extracted_fields if lease else None,
                    deposit_amount=float(prop.deposit_amount) if prop else None,
                    property_label=prop.label if prop else "your property",
                    ai_client=ai_client,
                    doc_id=doc.id,
                )
                
                doc.ai_draft = result_data.get("draft", "")
                logger.info("GeneratedDocument %s status transition: processing -> draft", doc_id)
                doc.status = DocStatus.draft
                doc.error_message = None
                
            except Exception as exc:
                logger.error("Document generation failed for %s: %s", doc_id, exc, exc_info=True)
                logger.info("GeneratedDocument %s status transition: processing -> failed", doc_id)
                doc.status = DocStatus.failed
                doc.error_message = str(exc)
                
            db.add(doc)
            await db.commit()
