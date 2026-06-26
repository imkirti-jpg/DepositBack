import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependency.auths import get_current_user
from app.db.database import SessionLocal, get_db
from app.models.lease import Lease, LeaseStatus
from app.models.users import User
from app.api.v1.property_routes import get_owned_property
from app.models.property import Property
from app.schemas.lease import LeaseFieldsUpdate, LeaseResponse
from app.services.ai_client import AIClientError, ai_client
from app.services.analytics import track
from app.services.lease_extractor import extract_lease_fields
from app.services.storage_service import StorageError, download_file, upload_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lease", tags=["Lease"] )


#  Background task 

async def _run_extraction(lease_id: uuid.UUID, file_url: str) -> None:
    """
    Runs after the POST /leases response has already been sent.
    Downloads the file, calls the extractor, writes results back to the row.

    Status transitions:
      processing → needs_review   (extraction ok, ≥1 low-confidence field)
      processing → confirmed      (extraction ok, all fields high/medium confidence)
      processing → failed         (AIClientError or storage error)
    """
    async with SessionLocal() as db:
        result = await db.execute(select(Lease).where(Lease.id == lease_id))
        lease = result.scalar_one_or_none()
        if lease is None:
            logger.error("_run_extraction: lease %s not found", lease_id)
            return

        try:
            file_bytes, mime_type = download_file(file_url)
            extracted = await extract_lease_fields(file_bytes, mime_type, ai_client)

            low_confidence = extracted.get("low_confidence_fields", [])
            lease.extracted_fields = extracted
            lease.status = LeaseStatus.needs_review if low_confidence else LeaseStatus.confirmed

        except (AIClientError, StorageError) as exc:
            logger.error("Extraction failed for lease %s: %s", lease_id, exc)
            lease.status = LeaseStatus.failed

        lease.updated_at = datetime.now(timezone.utc)
        db.add(lease)
        await db.commit()

        await track(
            db,
            "lease_extraction_completed",
            properties={"lease_id": str(lease_id), "status": lease.status.value},
        )


# Routes 

@router.post("", response_model=LeaseResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_lease(
    background_tasks: BackgroundTasks,
    property_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    
    # Verify the property belongs to this user
    await get_owned_property(db ,property_id, current_user)

    try:
        file_url = await upload_file(file, property_id=str(property_id), category="leases")
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    lease = Lease(property_id=property_id, file_url=file_url)
    db.add(lease)
    await db.commit()
    await db.refresh(lease)

    background_tasks.add_task(_run_extraction, lease.id, file_url)

    await track(db, "lease_uploaded", user_id=current_user.id,
                properties={"lease_id": str(lease.id), "property_id": str(property_id)})

    return lease


@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(
    lease_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    lease = await _get_owned_lease(lease_id, current_user, db)
    return lease


@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease_fields(
    lease_id: uuid.UUID,
    body: LeaseFieldsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
   
    lease = await _get_owned_lease(lease_id, current_user, db)
    lease.extracted_fields = body.extracted_fields
    lease.status = LeaseStatus.confirmed
    lease.updated_at = datetime.now(timezone.utc)
    db.add(lease)
    await db.commit()
    await db.refresh(lease)
    return lease
    """
    Manually correct extracted fields.
    Overwrites whatever the AI produced and sets status = confirmed.
    Claims analysis always reads the current extracted_fields — it has no
    way to know whether a value is AI-original or user-corrected.
"""

@router.post("/{lease_id}/reextract", response_model=LeaseResponse, status_code=status.HTTP_202_ACCEPTED)
async def reextract_lease(
    lease_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    
    lease = await _get_owned_lease(lease_id, current_user, db)

    if lease.status == LeaseStatus.processing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Extraction is already in progress for this lease.",
        )

    lease.status = LeaseStatus.processing
    lease.updated_at = datetime.now(timezone.utc)
    db.add(lease)
    await db.commit()
    await db.refresh(lease)

    background_tasks.add_task(_run_extraction, lease.id, lease.file_url)
    return lease
    """
    Re-run AI extraction on the original uploaded file.
    Only overwrites extracted_fields if the new call succeeds.
    Use this when status = failed or the user wants a fresh pass.
    """

#  Shared ownership gate 

async def _get_owned_lease(
    lease_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Lease:
    """
    Load a lease and verify the current user owns the property it belongs to.
    Returns 404 (not 403) on unowned leases to avoid leaking existence.
    """
    result = await db.execute(
        select(Lease)
        .join(Property, Lease.property_id == Property.id)
        .where(Lease.id == lease_id, Property.user_id == current_user.id)
    )
    lease = result.scalar_one_or_none()
    if lease is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lease not found")
    return lease