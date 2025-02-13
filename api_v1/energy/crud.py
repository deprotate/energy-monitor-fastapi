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


from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

async def get_report_by_date(session: AsyncSession, start_date: datetime, end_date: datetime, group_by: str):
    # Определяем формат группировки для SQLAlchemy и Python
    if group_by == "day":
        date_format_sql = "DD.MM.YYYY"
        date_format_py = "%d.%m.%Y"
        period_step = timedelta(days=1)
    elif group_by == "month":
        date_format_sql = "MM.YYYY"
        date_format_py = "%m.%Y"
        period_step = timedelta(days=31)  # Берём 31 день, чтобы двигаться по месяцам
    elif group_by == "year":
        date_format_sql = "YYYY"
        date_format_py = "%Y"
        period_step = timedelta(days=365)
    else:
        raise ValueError("Некорректное значение group_by")

    group_by_expr = func.to_char(Energy.created_at, date_format_sql)

    # Запрос к базе данных
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

    # Заполняем существующие данные
    existing_periods = {
        period: {
            "1": consumption,
            "2": production,
            "3": max(consumption - production, 0),
            "4": max(production - consumption, 0),
        }
        for period, consumption, production in result.all()
    }

    # Генерация всех возможных периодов
    def generate_periods(start_date, end_date, period_step, date_format_py):
        periods = []
        current_date = start_date.replace(day=1) if group_by == "month" else start_date
        while current_date <= end_date:
            period = current_date.strftime(date_format_py)
            periods.append(period)
            if group_by == "month":
                # Смещаемся к первому числу следующего месяца
                next_month = current_date.month % 12 + 1
                next_year = current_date.year + (1 if next_month == 1 else 0)
                current_date = current_date.replace(year=next_year, month=next_month, day=1)
            elif group_by == "year":
                # Смещаемся на 1 января следующего года
                current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                # По дням
                current_date += period_step
        return periods

    all_periods = generate_periods(start_date, end_date, period_step, date_format_py)

    # Заполняем отсутствующие периоды нулями
    report = {
        period: existing_periods.get(period, {"1": 0, "2": 0, "3": 0, "4": 0})
        for period in all_periods
    }

    return report
