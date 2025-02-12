from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from api_v1.core.DbHelper import db_helper
from api_v1.energy import crud
from api_v1.energy.schemas import CreateEnergy

energy_router = APIRouter()


@energy_router.get("/energy/")
async def get_energy_list(session: AsyncSession = Depends(db_helper.session_dependency)):
    return await crud.get_energy_list(session=session)


@energy_router.get("/energy/{energy_id}/")
async def get_energy(energy_id: int, session: AsyncSession = Depends(db_helper.session_dependency)):
    return await crud.get_energy(session=session, energy_id=energy_id)


@energy_router.post("/create_energy/")
async def create_energy(
        session: AsyncSession = Depends(db_helper.session_dependency),
        energy_data: CreateEnergy = Body(...)
):
    return await crud.create_energy(session=session, energy_data=energy_data)


@energy_router.get("/report/")
async def report(session: AsyncSession = Depends(db_helper.session_dependency)):
    return await crud.report(session=session)
