from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api_v1.core.models.Energy import Energy
from api_v1.energy.schemas import EnergyResponse


# 1 - потрачено, 2 - получено 3 -в сеть 4 - из сети

async def create_energy(session: AsyncSession, energy_data) -> Energy:
    energy = Energy(**energy_data.dict())
    session.add(energy)
    await session.commit()
    await session.refresh(energy)
    return energy


async def get_energy_list(session: AsyncSession) -> list:
    query = select(Energy)
    result = await session.execute(query)
    energy_list = result.scalars().all()
    return [EnergyResponse(**e.__dict__) for e in energy_list]


async def get_energy(session: AsyncSession, energy_id: int) -> EnergyResponse | None:
    query = select(Energy).where(Energy.id == energy_id)
    result = await session.execute(query)
    energy = result.scalars().first()

    if energy:
        return EnergyResponse(**energy.__dict__)

    return None


async def report(session: AsyncSession):
    query = select(
        func.sum(Energy.value).filter(Energy.type == 1),
        func.sum(Energy.value).filter(Energy.type == 2)
    )
    result = await session.execute(query)
    sum_type_1, sum_type_2 = result.fetchone()
    if sum_type_1 or 0 > sum_type_2 or 0:
        return {
            "1": sum_type_1 or 0,
            "2": sum_type_2 or 0,
            "3": sum_type_1 - sum_type_2,
            "4": 0

        }
    else:
        return {
            "1": sum_type_1 or 0,
            "2": sum_type_2 or 0,
            "3": 0,
            "4": sum_type_2 - sum_type_1

        }


async def get_report_by_range(session: AsyncSession, start_date: datetime, end_date: datetime):

    query = select(
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 1), 0),
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 2), 0)
    ).where(Energy.created_at.between(start_date, end_date))
    session.expire_all()

    result = await session.execute(query)

    sum_type_1, sum_type_2 = result.one()

    return {
        "1": sum_type_1,
        "2": sum_type_2,
        "3": max(sum_type_1 - sum_type_2, 0),
        "4": max(sum_type_2 - sum_type_1, 0),
    }


async def get_report_by_date(session: AsyncSession, start_date: datetime, end_date: datetime, group_by: str):
    if group_by == "day":
        date_format = "DD.MM.YYYY"
        period_step = timedelta(days=1)
    elif group_by == "month":
        date_format = "MM.YYYY"
        period_step = timedelta(days=30)
    elif group_by == "year":
        date_format = "YYYY"
        period_step = timedelta(days=365)
    else:
        raise ValueError("Некорректное значение group_by")

    group_by_expr = func.to_char(Energy.created_at, date_format)


    query = select(
        group_by_expr.label("period"),
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 1), 0).label("consumption"),
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 2), 0).label("production"),
    ).where(
        Energy.created_at.between(start_date, end_date)
    ).group_by(
        group_by_expr
    ).order_by(
        group_by_expr
    )

    result = await session.execute(query)


    existing_periods = {period: {"1": consumption, "2": production, "3": max(consumption - production, 0), "4": max(production - consumption, 0)}
                        for period, consumption, production in result.all()}

    # Функция для генерации всех периодов в нужном диапазоне
    def generate_periods(start_date, end_date, period_step):
        periods = []
        current_date = start_date
        while current_date <= end_date:
            period = current_date.strftime(date_format)
            periods.append(period)
            current_date += period_step
        return periods


    all_periods = generate_periods(start_date, end_date, period_step)

    # Объединяем существующие и пустые периоды
    report = defaultdict(lambda: {"1": 0, "2": 0, "3": 0, "4": 0})
    for period in all_periods:
        report[period] = existing_periods.get(period, {"1": 0, "2": 0, "3": 0, "4": 0})

    return dict(report)