import uuid
import logging

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
from app.services.storage_service import StorageError, upload_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evidence", tags=["evidence"])


#  Routes 

@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    property_id: uuid.UUID = Form(...),
    phase: EvidencePhase = Form(...),
    file: UploadFile = File(...),
    room_label: str | None = Form(None),
    notes: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_property(db,property_id, current_user)

    try:
        # Store under {property_id}/evidence/{move_in|move_out}/{uuid}.ext
        category = f"evidence/{phase.value}"
        file_url = await upload_file(file, property_id=str(property_id), category=category)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    evidence = Evidence(
        property_id=property_id,
        phase=phase,
        room_label=room_label.strip() if room_label else None,
        file_url=file_url,
        notes=notes,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)

    await track(
        db,
        "evidence_uploaded",
        user_id=current_user.id,
        properties={
            "evidence_id": str(evidence.id),
            "property_id": str(property_id),
            "phase": phase.value,
            "room_label": room_label or "",
        },
    )
    return evidence


@router.get("", response_model=list[EvidenceResponse])
async def list_evidence(
    property_id: uuid.UUID,
    phase: EvidencePhase | None = None,
    room_label: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Ownership check first
    await get_owned_property(db,property_id, current_user)

    query = (
        select(Evidence)
        .where(Evidence.property_id == property_id)
        .order_by(Evidence.created_at.asc())
    )
    if phase is not None:
        query = query.where(Evidence.phase == phase)
    if room_label is not None:
        query = query.where(Evidence.room_label == room_label.strip())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evidence = await _get_owned_evidence(evidence_id, current_user, db)
    return evidence


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hard delete , no recovery path at MVP.
    The file stays in Supabase Storage (cheap, and avoids accidental data loss
    while the user base is small enough to manually restore if ever needed).
    """
    evidence = await _get_owned_evidence(evidence_id, current_user, db)
    await db.delete(evidence)
    await db.commit()


#  Shared ownership gate 

async def _get_owned_evidence(
    evidence_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Evidence:
    
    result = await db.execute(
        select(Evidence)
        .join(Property, Evidence.property_id == Property.id)
        .where(Evidence.id == evidence_id, Property.user_id == current_user.id)
    )
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence
    """
    Load an evidence row and verify the current user owns the property
    it belongs to. Returns 404 on unowned rows to avoid leaking existence.
    """