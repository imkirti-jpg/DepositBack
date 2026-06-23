from fastapi import Depends, FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "running"}

from fastapi import FastAPI

from app.api.v1.user_routes import router as me_router
from app.api.v1.preferences import router as pref_router


app = FastAPI()

app.include_router(me_router)

app.include_router(pref_router)

