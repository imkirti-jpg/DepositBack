import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependency.auths import get_current_user
from app.db.database import get_db
from app.models.evidence import Evidence, EvidencePhase
from app.models.users import User
from app.models.property import Property
from app.api.v1.property_routes import get_owned_property
from app.schemas.evidence import EvidenceResponse
from app.services.analytics import track
from app.services.storage_service import get_public_url, get_thumbnail_url
from app.services.evidence_service import EvidenceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evidence", tags=["evidence"])

def format_evidence_response(ev: Evidence) -> EvidenceResponse:
    data = {
        "id": ev.id,
        "property_id": ev.property_id,
        "phase": ev.phase,
        "room_label": ev.room_label,
        "file_url": ev.file_url,
        "file_hash": ev.file_hash,
        "display_name": ev.display_name,
        "category": ev.category,
        "sort_order": ev.sort_order,
        "notes": ev.notes,
        "mime_type": ev.mime_type,
        "file_size": ev.file_size,
        "width": ev.width,
        "height": ev.height,
        "captured_at": ev.captured_at,
        "deleted_at": ev.deleted_at,
        "deleted_by": ev.deleted_by,
        "created_at": ev.created_at,
        "uploaded_at": ev.created_at,
        "thumbnail_url": get_thumbnail_url(ev.file_url),
        "full_image_url": get_public_url(ev.file_url),
    }
    return EvidenceResponse.model_validate(data)

# Routes 

@router.post("", response_model=list[EvidenceResponse], status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    property_id: uuid.UUID = Form(...),
    category: str = Form(...),
    files: list[UploadFile] = File(...),
    room_label: str | None = Form(None),
    notes: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_property(db, property_id, current_user)

    uploaded_list = []
    for file in files:
        evidence = await EvidenceService.upload_evidence(
            property_id=property_id,
            category=category,
            file=file,
            room_label=room_label,
            notes=notes,
            db=db,
        )
        uploaded_list.append(format_evidence_response(evidence))

        await track(
            db,
            "evidence_uploaded",
            user_id=current_user.id,
            properties={
                "evidence_id": str(evidence.id),
                "property_id": str(property_id),
                "category": category,
                "room_label": room_label or "",
            },
        )
        
    return uploaded_list


@router.get("", response_model=list[EvidenceResponse])
async def list_evidence(
    property_id: uuid.UUID,
    category: str | None = None,
    room_label: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_property(db, property_id, current_user)

    query = (
        select(Evidence)
        .where(Evidence.property_id == property_id)
        .order_by(Evidence.sort_order.asc(), Evidence.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    
    if not include_deleted:
        query = query.where(Evidence.deleted_at.is_(None))
        
    if category is not None:
        query = query.where(Evidence.category == category)
        
    if room_label is not None:
        query = query.where(Evidence.room_label == room_label.strip())

    result = await db.execute(query)
    return [format_evidence_response(ev) for ev in result.scalars().all()]


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evidence = await _get_owned_evidence(evidence_id, current_user, db)
    return format_evidence_response(evidence)


@router.put("/{evidence_id}/replace", response_model=EvidenceResponse)
async def replace_evidence(
    evidence_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_evidence(evidence_id, current_user, db)
    evidence = await EvidenceService.replace_evidence(evidence_id, file, db)
    return format_evidence_response(evidence)


@router.post("/{evidence_id}/restore", response_model=EvidenceResponse)
async def restore_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_evidence(evidence_id, current_user, db, allow_deleted=True)
    evidence = await EvidenceService.restore_evidence(evidence_id, db)
    return format_evidence_response(evidence)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_evidence(evidence_id, current_user, db)
    await EvidenceService.soft_delete_evidence(evidence_id, current_user.id, db)


# Shared ownership gate 

async def _get_owned_evidence(
    evidence_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
    allow_deleted: bool = False,
) -> Evidence:
    query = (
        select(Evidence)
        .join(Property, Evidence.property_id == Property.id)
        .where(Evidence.id == evidence_id, Property.user_id == current_user.id)
    )
    if not allow_deleted:
        query = query.where(Evidence.deleted_at.is_(None))
        
    result = await db.execute(query)
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence