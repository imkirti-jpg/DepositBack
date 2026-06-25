from fastapi import Depends, FastAPI
from app.core.config import settings


from app.api.v1.user_routes import router as me_router
from app.api.v1.preferences import router as pref_router

app = FastAPI()

app.include_router(me_router)
app.include_router(pref_router)



@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

@app.get("/")
async def root():
    return {"message": "running"}