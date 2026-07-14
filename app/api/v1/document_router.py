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
from app.services.document_service import DocumentService
from app.services.analytics import track

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generated-documents",  tags=["documents"])


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
    """
    await get_owned_property(db, body.property_id, current_user)

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

    doc = await DocumentService.create_document(
        property_id=body.property_id,
        deduction_notice_id=body.deduction_notice_id,
        doc_type=body.doc_type.value,
        background_tasks=background_tasks,
        db=db,
    )

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


@router.post("/{doc_id}/regenerate", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def regenerate_document(
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Explicitly request regeneration of an existing document, archiving the old version.
    """
    await _get_owned_document(doc_id, current_user, db)
    return await DocumentService.regenerate_document(doc_id, background_tasks, db)


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
    """List all active generated documents for a property, newest first."""
    await get_owned_property(db, property_id, current_user)

    result = await db.execute(
        select(GeneratedDocument)
        .where(
            GeneratedDocument.property_id == property_id,
            GeneratedDocument.is_active == True,
            GeneratedDocument.status.in_([DocStatus.draft, DocStatus.sent])
        )
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