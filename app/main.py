from fastapi import Depends, FastAPI
from app.core.config import settings


from app.api.v1.user_routes import router as me_router
from app.api.v1.preferences import router as pref_router
from app.api.v1.property_routes import router as properties
from app.api.v1.leases import router as lease
from app.api.v1.evidence_router import router as evidence
from app.api.v1.disputes_routes import notices_router , claims_router
from app.api.v1.document_router import router as document
from app.api.v1.dashboard import router as dashboard
app = FastAPI()

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