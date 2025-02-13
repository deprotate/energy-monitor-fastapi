from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_v1.core.DbHelper import db_helper
from api_v1.core.config import settings
from api_v1.core.models.Base import Base
from api_v1.energy.views import energy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_helper.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(energy_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def ping() -> str:
    return "OK"


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=int("8000"), reload=False)

