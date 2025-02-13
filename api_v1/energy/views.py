from datetime import datetime

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


@energy_router.get("/report_by_date/")
async def report_by_date(
    start_date: str,
    end_date: str,
    group_by: str = None,
    session: AsyncSession = Depends(db_helper.session_dependency)
):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = end_date.strip("/")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    print(end_date)


    if group_by is None:
        return await crud.get_report_by_range(session, start_date, end_date)
    else:
        return await crud.get_report_by_date(session, start_date, end_date, group_by)
