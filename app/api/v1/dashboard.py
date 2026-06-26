
from collections.abc import Sequence
from decimal import Decimal
import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.auths import get_current_user
from app.db.database import get_db
from app.models.dispute import Claim,ClaimLabel,DeductionNotice,NoticeStatus
from app.models.documents import DocStatus, GeneratedDocument
from app.models.evidence import Evidence,EvidencePhase
from app.models.lease import Lease,LeaseStatus
from app.models.users import User
from app.models.property import PropertyStatus
from app.api.v1.property_routes import get_owned_property
from app.schemas.dashboard import ClaimSummary,DashboardResponse,DocumentSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/properties",tags=["dashboard"])


@router.get("/{property_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a full case snapshot for one property.

    Designed to be the first screen a user sees after logging in.
    """

    prop = await get_owned_property(db,property_id, current_user)

    # Lease
    lease_result = await db.execute(
        select(Lease)
        .where(Lease.property_id == property_id)
        .order_by(Lease.created_at.desc())
        .limit(1)
    )
    lease: Lease | None = lease_result.scalar_one_or_none()

    # Evidence counts
    move_in_count = (
        await db.scalar(
            select(func.count(Evidence.id)).where(
                Evidence.property_id == property_id,
                Evidence.phase == EvidencePhase.move_in,
            )
        )
        or 0
    )

    move_out_count = (
        await db.scalar(
            select(func.count(Evidence.id)).where(
                Evidence.property_id == property_id,
                Evidence.phase == EvidencePhase.move_out,
            )
        )
        or 0
    )

    # Latest deduction notice
    notice_result = await db.execute(
        select(DeductionNotice)
        .where(DeductionNotice.property_id == property_id)
        .order_by(DeductionNotice.created_at.desc())
        .limit(1)
    )
    notice: DeductionNotice | None = notice_result.scalar_one_or_none()

    # Claims
    claims: list[Claim] = []

    if notice:
        claims_result = await db.execute(
            select(Claim)
            .where(Claim.deduction_notice_id == notice.id)
            .order_by(Claim.created_at.asc())
        )
        claims = list(claims_result.scalars().all())

    (
        claim_summaries,
        total_supported,
        total_disputed,
        unquantified,
    ) = _summarize_claims(claims)

    # Documents
    docs_result = await db.execute(
        select(GeneratedDocument)
        .where(GeneratedDocument.property_id == property_id)
        .order_by(GeneratedDocument.created_at.desc())
    )

    documents: list[GeneratedDocument] = list(docs_result.scalars().all())

    next_action = _derive_next_action(
        property_status=prop.status,
        lease=lease,
        notice=notice,
        claims=claims,
        documents=documents,
    )

    return DashboardResponse(
        property_id=prop.id,
        property_label=prop.label,
        property_status=prop.status,
        deposit_amount=prop.deposit_amount,
        lease_id=lease.id if lease else None,
        lease_status=lease.status if lease else None,
        move_in_evidence_count=move_in_count,
        move_out_evidence_count=move_out_count,
        notice_id=notice.id if notice else None,
        notice_status=notice.status if notice else None,
        claims=claim_summaries,
        total_supported_amount=total_supported,
        total_disputed_amount=total_disputed,
        total_unquantified_count=unquantified,
        documents=[
            DocumentSummary(
                id=d.id,
                doc_type=d.doc_type,
                status=d.status,
                sent_at=d.sent_at,
            )
            for d in documents
        ],
        next_action=next_action,
    )


def _summarize_claims(
    claims: Sequence[Claim],
) -> tuple[list[ClaimSummary], Decimal, Decimal, int]:
    """
    Returns:
        summaries,
        total_supported,
        total_disputed,
        unquantified_count
    """

    summaries: list[ClaimSummary] = []
    total_supported = Decimal("0")
    total_disputed = Decimal("0")
    unquantified = 0

    for claim in claims:
        effective = claim.user_override_label or claim.label

        amount = (
            Decimal(str(claim.claimed_amount))
            if claim.claimed_amount is not None
            else None
        )

        summaries.append(
            ClaimSummary(
                id=claim.id,
                item_description=claim.item_description,
                claimed_amount=amount,
                effective_label=effective,
            )
        )

        if effective == ClaimLabel.supported:
            if amount is not None:
                total_supported += amount
        else:
            if amount is not None:
                total_disputed += amount
            else:
                unquantified += 1

    return (
        summaries,
        total_supported,
        total_disputed,
        unquantified,
    )


def _derive_next_action(
    *,
    property_status: PropertyStatus,
    lease: Lease | None,
    notice: DeductionNotice | None,
    claims: Sequence[Claim],
    documents: Sequence[GeneratedDocument],
) -> str:
    """
    Derive the single most important next action.
    """

    if property_status == PropertyStatus.resolved:
        return "Case marked as resolved. Hope you got your deposit back."

    if lease and lease.status == LeaseStatus.processing:
        return "Reading your lease — refresh in a moment to see the extracted fields."

    if notice and notice.status == NoticeStatus.processing:
        return "Analysing your deduction notice — refresh in a moment for the claim breakdown."

    if any(d.status == DocStatus.processing for d in documents):
        return "Generating your document — refresh in a moment."

    if any(d.status == DocStatus.draft for d in documents):
        return (
            "Your draft is ready. Review it, make any edits, "
            "then send it to your landlord."
        )

    disputed_claims = [
        claim
        for claim in claims
        if (claim.user_override_label or claim.label)
        != ClaimLabel.supported
    ]

    if claims and disputed_claims:
        count = len(disputed_claims)
        return (
            f"{count} deduction{'s' if count > 1 else ''} found to be weak or unsupported. "
            "Generate a dispute message or formal letter to send to your landlord."
        )

    if claims:
        return (
            "All deductions appear supported by the lease. "
            "If you disagree, you can override individual claim labels "
            "and regenerate."
        )

    if notice and notice.status == NoticeStatus.failed:
        return "Analysis failed. Check your notice file and resubmit it."

    if lease and lease.status in (
        LeaseStatus.confirmed,
        LeaseStatus.needs_review,
    ):
        if lease.status == LeaseStatus.needs_review:
            return (
                "Some lease fields need your confirmation. "
                "Review them, then upload your landlord's deduction notice."
            )

        return (
            "Lease confirmed. Upload your landlord's deduction notice "
            "when you receive it."
        )

    if lease and lease.status == LeaseStatus.failed:
        return (
            "Lease extraction failed. Try uploading a clearer photo or PDF "
            "and rerun extraction."
        )

    return (
        "Upload your lease to get started. "
        "You can also add move-in photos while you wait for a deduction notice."
    )

"""
dashboard.py — single GET /properties/{id}/dashboard endpoint.

Assembles a complete case snapshot from the seven tables built in phases 1-6.
Nothing is stored here — everything is computed on read.

next_action is the most important field for the frontend:
it tells the user exactly what to do next in one sentence,
derived from the current state of their case.
"""
