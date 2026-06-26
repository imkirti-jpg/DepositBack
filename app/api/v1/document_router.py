import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependency.auths import get_current_user
from app.db.database import SessionLocal, get_db
from app.models.dispute import Claim, DeductionNotice
from app.models.documents import DocStatus, GeneratedDocument
from app.models.lease import Lease
from app.models.users import User
from app.models.property import Property
from app.api.v1.property_routes import get_owned_property
from app.schemas.documents import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services.ai_client import AIClientError, ai_client
from app.services.analytics import track
from app.services.document_generator import generate_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generated-documents",  tags=["documents"])


#  Background task 

async def _run_generation(doc_id: uuid.UUID) -> None:
    """
    Runs after POST /generated-documents response is sent.

    Loads the claims breakdown, lease context, and property info,
    then calls the generator and writes the ai_draft back to the row.

    Status transitions:
      processing → draft    (generation succeeded)
      processing → failed   (AIClientError)
    """
    async with SessionLocal() as db:
        result = await db.execute(
            select(GeneratedDocument).where(GeneratedDocument.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            logger.error("_run_generation: document %s not found", doc_id)
            return

        try:
            # Load property for label and deposit amount
            prop_result = await db.execute(
                select(Property).where(Property.id == doc.property_id)
            )
            prop = prop_result.scalar_one_or_none()

            # Load lease fields (most recent with extracted data)
            lease_result = await db.execute(
                select(Lease)
                .where(
                    Lease.property_id == doc.property_id,
                    Lease.extracted_fields.isnot(None),
                )
                .order_by(Lease.created_at.desc())
                .limit(1)
            )
            lease = lease_result.scalar_one_or_none()

            # Load all claims for this notice with their effective labels
            claims_result = await db.execute(
                select(Claim).where(Claim.deduction_notice_id == doc.deduction_notice_id)
            )
            claims = [
                {
                    "item_description": c.item_description,
                    "claimed_amount": float(c.claimed_amount) if c.claimed_amount else None,
                    "reasoning": c.reasoning,
                    "evidence_refs": c.evidence_refs,
                    # effective_label: user override takes precedence
                    "effective_label": (c.user_override_label or c.label).value,
                }
                for c in claims_result.scalars().all()
            ]

            result_data = await generate_document(
                doc_type=doc.doc_type.value,
                claims=claims,
                lease_fields=lease.extracted_fields if lease else None,
                deposit_amount=float(prop.deposit_amount) if prop else None,
                property_label=prop.label if prop else "your property",
                ai_client=ai_client,
            )

            doc.ai_draft = result_data.get("draft", "")
            doc.status = DocStatus.draft

        except AIClientError as exc:
            logger.error("Document generation failed for %s: %s", doc_id, exc)
            doc.status = DocStatus.failed

        db.add(doc)
        await db.commit()

        await track(
            db,
            "document_generated",
            properties={
                "document_id": str(doc_id),
                "doc_type": doc.doc_type.value,
                "status": doc.status.value,
            },
        )


#  Routes 

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    body: DocumentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a recovery document from a completed claims analysis.

    doc_type:
      message       — WhatsApp/email draft (~200 words, copy-paste ready)
      formal_letter — full demand letter with lease clause references

    Returns 202 immediately. Poll GET /generated-documents/{id} until
    status leaves "processing".

    Regenerating creates a new row — history is always preserved.
    """
    await get_owned_property(db,body.property_id, current_user)

    # Verify the notice exists and belongs to this property
    notice_result = await db.execute(
        select(DeductionNotice).where(
            DeductionNotice.id == body.deduction_notice_id,
            DeductionNotice.property_id == body.property_id,
        )
    )
    if notice_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deduction notice not found for this property.",
        )

    doc = GeneratedDocument(
        property_id=body.property_id,
        deduction_notice_id=body.deduction_notice_id,
        doc_type=body.doc_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(_run_generation, doc.id)

    await track(
        db,
        "document_generation_started",
        user_id=current_user.id,
        properties={
            "document_id": str(doc.id),
            "doc_type": body.doc_type.value,
            "property_id": str(body.property_id),
        },
    )
    return doc


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Poll this after POST /generated-documents.
    When status = draft, display_content has the full AI-generated text.
    When status = failed, re-POST to try again.
    """
    return await _get_owned_document(doc_id, current_user, db)


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: uuid.UUID,
    body: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save the user's edited version of the document.
    ai_draft is never overwritten — only edited_content is updated.
    display_content will show edited_content from this point on.
    """
    doc = await _get_owned_document(doc_id, current_user, db)

    if doc.status == DocStatus.processing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is still being generated. Wait for status = draft.",
        )

    doc.edited_content = body.edited_content
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.post("/{doc_id}/mark-sent", response_model=DocumentResponse)
async def mark_sent(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a document as sent. The product never sends on the user's behalf —
    this is purely a status update for the user's own tracking.
    """
    doc = await _get_owned_document(doc_id, current_user, db)

    if doc.status not in (DocStatus.draft,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot mark a document with status '{doc.status.value}' as sent.",
        )

    doc.status = DocStatus.sent
    doc.sent_at = datetime.now(timezone.utc)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await track(
        db,
        "document_sent",
        user_id=current_user.id,
        properties={"document_id": str(doc_id), "doc_type": doc.doc_type.value},
    )
    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all generated documents for a property, newest first."""
    await get_owned_property(db,property_id, current_user)

    result = await db.execute(
        select(GeneratedDocument)
        .where(GeneratedDocument.property_id == property_id)
        .order_by(GeneratedDocument.created_at.desc())
    )
    return result.scalars().all()


#  Ownership gate 

async def _get_owned_document(
    doc_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> GeneratedDocument:
    result = await db.execute(
        select(GeneratedDocument)
        .join(Property, GeneratedDocument.property_id == Property.id)
        .where(GeneratedDocument.id == doc_id, Property.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc