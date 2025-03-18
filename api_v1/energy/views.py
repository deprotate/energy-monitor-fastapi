from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api_v1.core.DbHelper import db_helper
from api_v1.energy import crud
from api_v1.energy.schemas import CreateEnergy, PredictIn

from api_v1.core.config import settings
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
    start_date: str  = "2025-02-14",
    end_date: str = "2025-03-14",
    group_by: Annotated[Literal["day", "month", "year"] | None, Query(title="Group periods by day/month/year" )] = None,

    session: AsyncSession = Depends(db_helper.session_dependency)
):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = end_date.strip("/")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    if group_by is None:
        return await crud.get_report_by_range(session, start_date, end_date)
    else:
        return await crud.get_report_by_date(session, start_date, end_date, group_by)


@energy_router.get("/predict_report/")
async def predict_report(
        predict_in: Annotated[PredictIn, Query()],
        session: AsyncSession = Depends(db_helper.session_dependency)
):
    start_date = datetime.strptime(predict_in.start_date, "%Y-%m-%d")
    end_date = predict_in.end_date.strip("/")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    if predict_in.group_by is None:
        return await crud.predict_report_by_range(session=session, start_date=start_date, end_date=end_date,
                                                  solar_coefficient=settings.solar_coefficient,
                                                  average_consumption_by_months=settings.average_consumption_by_months,
                                                  longitude=predict_in.longitude, latitude=predict_in.latitude)
    else:
        return await crud.predict_report_by_date(session=session, start_date=start_date, end_date=end_date,
                                                 group_by=predict_in.group_by,
                                                 solar_coefficient=settings.solar_coefficient,
                                                 average_consumption_by_months=settings.average_consumption_by_months,
                                                 longitude=predict_in.longitude, latitude=predict_in.latitude)
