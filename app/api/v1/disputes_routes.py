import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependency.auths import get_current_user
from app.db.database import SessionLocal, get_db
from app.models.dispute import Claim, ClaimLabel, DeductionNotice, NoticeStatus
from app.models.evidence import Evidence
from app.models.lease import Lease
from app.models.users import User
from app.models.property import Property
from app.api.v1.property_routes import get_owned_property
from app.schemas.disputes import ClaimOverride, ClaimResponse, NoticeResponse
from app.services.ai_client import AIClientError, ai_client
from app.services.analytics import track
from app.services.dispute_service import DisputeService

logger = logging.getLogger(__name__)

# Two separate routers — mounted at different prefixes in main.py
notices_router = APIRouter(prefix="/deduction-notices", tags=["disputes"])
claims_router = APIRouter( prefix="/claims", tags=["claims"])


#  Notice routes 

@notices_router.post("", response_model=NoticeResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_deduction_notice(
    background_tasks: BackgroundTasks,
    property_id: uuid.UUID = Form(...),
    file: UploadFile | None = File(None),
    raw_text: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file and not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a file upload or raw_text (or both).",
        )

    await get_owned_property(db, property_id, current_user)

    notice = await DisputeService.create_notice(property_id, file, raw_text, background_tasks, db)

    await track(
        db,
        "deduction_notice_uploaded",
        user_id=current_user.id,
        properties={
            "notice_id": str(notice.id),
            "property_id": str(property_id),
            "has_file": file is not None,
            "has_text": raw_text is not None,
        },
    )
    return notice


@notices_router.post("/{notice_id}/reanalyze", response_model=NoticeResponse, status_code=status.HTTP_202_ACCEPTED)
async def reanalyze_notice(
    notice_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_notice(notice_id, current_user, db)
    return await DisputeService.reanalyze_notice(notice_id, background_tasks, db)


@notices_router.get("/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_owned_notice(notice_id, current_user, db)


@notices_router.get("/{notice_id}/claims", response_model=list[ClaimResponse])
async def list_claims(
    notice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notice = await _get_owned_notice(notice_id, current_user, db)

    result = await db.execute(
        select(Claim)
        .where(Claim.deduction_notice_id == notice_id, Claim.is_active == True)
        .order_by(Claim.created_at.asc())
    )
    claims = result.scalars().all()

    # Load all evidence for the property
    ev_res = await db.execute(
        select(Evidence).where(Evidence.property_id == notice.property_id)
    )
    ev_map = {str(ev.id): ev.display_name for ev in ev_res.scalars().all()}

    response_claims = []
    for c in claims:
        # copy dict and inject evidence_names
        refs = dict(c.evidence_refs) if c.evidence_refs else {}
        ev_ids = refs.get("evidence_ids", [])
        refs["evidence_names"] = [ev_map[eid] for eid in ev_ids if eid in ev_map]
        
        c.evidence_refs = refs
        response_claims.append(ClaimResponse.from_orm_with_effective(c))

    return response_claims


#  Claim routes 

@claims_router.put("/{claim_id}", response_model=ClaimResponse)
async def override_claim_label(
    claim_id: uuid.UUID,
    body: ClaimOverride,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    claim = await _get_owned_claim(claim_id, current_user, db)
    claim.user_override_label = body.user_override_label
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return ClaimResponse.from_orm_with_effective(claim)


#  Ownership gates 

async def _get_owned_notice(
    notice_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> DeductionNotice:
    result = await db.execute(
        select(DeductionNotice)
        .join(Property, DeductionNotice.property_id == Property.id)
        .where(DeductionNotice.id == notice_id, Property.user_id == current_user.id)
    )
    notice = result.scalar_one_or_none()
    if notice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")
    return notice


async def _get_owned_claim(
    claim_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Claim:
    result = await db.execute(
        select(Claim)
        .join(DeductionNotice, Claim.deduction_notice_id == DeductionNotice.id)
        .join(Property, DeductionNotice.property_id == Property.id)
        .where(Claim.id == claim_id, Property.user_id == current_user.id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim