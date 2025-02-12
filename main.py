from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from api_v1.core.DbHelper import db_helper
from api_v1.core.models.Base import Base
from api_v1.energy.views import energy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_helper.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(energy_router)


@app.get("/")
async def ping() -> str:
    return "OK"


if __name__ == '__main__':
    uvicorn.run(app)
