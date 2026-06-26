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
from app.services.dispute_engine import analyze_notice
from app.services.storage_service import StorageError, download_file, upload_file

logger = logging.getLogger(__name__)

# Two separate routers — mounted at different prefixes in main.py
notices_router = APIRouter(prefix="/deduction-notices", tags=["disputes"])
claims_router = APIRouter( prefix="/claims", tags=["claims"])


# ── Background task 

async def _run_analysis(notice_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(DeductionNotice).where(DeductionNotice.id == notice_id))
        notice = result.scalar_one_or_none()
        if notice is None:
            logger.error("_run_analysis: notice %s not found", notice_id)
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

            evidence_result = await db.execute(
                select(Evidence).where(Evidence.property_id == notice.property_id)
            )
            evidence_rows = [
                {
                    "id": str(ev.id),
                    "phase": ev.phase.value,
                    "room_label": ev.room_label,
                    "notes": ev.notes,
                }
                for ev in evidence_result.scalars().all()
            ]

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

                claim = Claim(
                    deduction_notice_id=notice.id,
                    item_description=item.get("item_description", ""),
                    claimed_amount=item.get("claimed_amount"),
                    label=label,
                    reasoning=item.get("reasoning", ""),
                    evidence_refs=item.get("evidence_refs", {}),
                )
                db.add(claim)

            notice.status = NoticeStatus.completed
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

        except (AIClientError, StorageError) as exc:
            logger.error("Analysis failed for notice %s: %s", notice_id, exc)
            notice.status = NoticeStatus.failed
            db.add(notice)
            await db.commit()


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

    await get_owned_property(db,property_id, current_user)

    file_url = None
    if file:
        try:
            file_url = await upload_file(file, property_id=str(property_id), category="notices")
        except StorageError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    notice = DeductionNotice(property_id=property_id, file_url=file_url, raw_text=raw_text)
    db.add(notice)
    await db.commit()
    await db.refresh(notice)

    background_tasks.add_task(_run_analysis, notice.id)

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
    await _get_owned_notice(notice_id, current_user, db)

    result = await db.execute(
        select(Claim)
        .where(Claim.deduction_notice_id == notice_id)
        .order_by(Claim.created_at.asc())
    )
    claims = result.scalars().all()
    return [ClaimResponse.from_orm_with_effective(c) for c in claims]


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