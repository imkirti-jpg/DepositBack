import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


from app.api.v1.user_routes import router as me_router
from app.api.v1.preferences import router as pref_router
from app.api.v1.property_routes import router as properties
from app.api.v1.leases import router as lease
from app.api.v1.evidence_router import router as evidence
from app.api.v1.disputes_routes import notices_router , claims_router
from app.api.v1.document_router import router as document
from app.api.v1.dashboard import router as dashboard

from contextlib import asynccontextmanager
from app.db.database import SessionLocal
from app.models.lease import Lease, LeaseStatus
from app.models.dispute import DeductionNotice, NoticeStatus
from sqlalchemy import update, select

from app.models.documents import GeneratedDocument, DocStatus

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cleanup stale processing statuses on startup
    async with SessionLocal() as db:
        try:
            # Clean leases
            lease_res = await db.execute(
                select(Lease).where(Lease.status == LeaseStatus.processing)
            )
            for lease in lease_res.scalars().all():
                logger.info("Lease %s status transition: processing -> failed (stale startup cleanup)", lease.id)
                lease.status = LeaseStatus.failed
                db.add(lease)

            # Clean notices
            notice_res = await db.execute(
                select(DeductionNotice).where(DeductionNotice.status == NoticeStatus.processing)
            )
            for notice in notice_res.scalars().all():
                logger.info("DeductionNotice %s status transition: processing -> failed (stale startup cleanup)", notice.id)
                notice.status = NoticeStatus.failed
                db.add(notice)

            # Clean generated documents
            doc_res = await db.execute(
                select(GeneratedDocument).where(GeneratedDocument.status == DocStatus.processing)
            )
            for doc in doc_res.scalars().all():
                logger.info("GeneratedDocument %s status transition: processing -> failed (stale startup cleanup)", doc.id)
                doc.status = DocStatus.failed
                doc.error_message = "Server reloaded while document was processing."
                db.add(doc)

            await db.commit()
            logger.info("Startup cleanup: Successfully recovered stale processing jobs.")
        except Exception as e:
            logger.error("Startup cleanup failed: %s", e)
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me_router)
app.include_router(pref_router)
app.include_router(properties)
app.include_router(lease)
app.include_router(evidence)
app.include_router(notices_router)
app.include_router(claims_router)
app.include_router(document)
app.include_router(dashboard)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

@app.get("/")
async def root():
    return {"message": "running"}