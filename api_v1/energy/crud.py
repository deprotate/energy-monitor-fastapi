import calendar
import pickle
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api_v1.core.config import settings
from api_v1.core.models.Energy import Energy
from api_v1.energy.schemas import EnergyResponse
import prophet
import pandas as pd


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

    return {
        "1": sum_type_1,
        "2": sum_type_2,
        "3": max(sum_type_1 - sum_type_2, 0),
        "4": max(sum_type_2 - sum_type_1, 0),
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

    existing_periods = {
        period: {
            "1": consumption,
            "2": production,
            "3": max(consumption - production, 0),
            "4": max(production - consumption, 0),
        }
        for period, consumption, production in result.all()
    }

    def generate_periods(start_date, end_date, period_step, date_format_py):
        periods = []
        current_date = start_date.replace(day=1) if group_by == "month" else start_date
        while current_date <= end_date:
            period = current_date.strftime(date_format_py)
            periods.append(period)
            if group_by == "month":
                next_month = current_date.month % 12 + 1
                next_year = current_date.year + (1 if next_month == 1 else 0)
                current_date = current_date.replace(year=next_year, month=next_month, day=1)
            elif group_by == "year":
                current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                current_date += period_step
        return periods

    all_periods = generate_periods(start_date, end_date, period_step, date_format_py)

    # Заполняем отсутствующие периоды нулями
    report = {
        period: existing_periods.get(period, {"1": 0, "2": 0, "3": 0, "4": 0})
        for period in all_periods
    }

    return report


# мб города из енва получать, хотя так пизже выглядит
def get_nearest_city(longitude: float, latitude: float, cities_list: list = settings.cities):
    best = None
    best_diff = float('inf')
    for city in cities_list:
        city_lon, city_lat, city_name = city
        diff = abs(city_lat - latitude) + abs(city_lon - longitude)
        if diff < best_diff:
            best_diff = diff
            best = (city_lon, city_lat, city_name)
    return best


def get_model(longitude, latitude):
    city_info = get_nearest_city(longitude, latitude)
    if city_info is None:
        raise ValueError("Не удалось определить ближайший город.")
    city_lon, city_lat, city_name = city_info
    model_filename = f'api_v1/energy/ml_models/{round(city_lon, 2)}-{round(city_lat, 2)}-{city_name}_prophet_model.pkl'
    try:
        with open(model_filename, 'rb') as f:
            model = pickle.load(f)
    except Exception as e:
        raise ValueError(f"Ошибка загрузки модели для города {city_name}: {e}")
    return model


async def predict_report_by_range(
        session: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        solar_coefficient: float,
        average_consumption_by_months: dict,
        longitude: float,
        latitude: float
) -> dict:
    now_date = datetime.now().date()

    # Разбиваем период на прошлую (до сегодняшнего дня включительно) и будущую (после сегодняшнего дня)
    past_end_date = min(end_date, datetime.combine(now_date, datetime.min.time()))
    future_start_date = max(start_date, datetime.combine(now_date + timedelta(days=1), datetime.min.time()))

    query = select(
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 1), 0),
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 2), 0)
    ).where(
        Energy.created_at.between(start_date, past_end_date)
    )
    session.expire_all()
    result = await session.execute(query)
    past_consumption, past_production = result.one()

    future_consumption = 0
    future_production = 0

    # Если есть будущие даты
    if future_start_date <= end_date:
        future_days = []
        current = future_start_date
        while current <= end_date:
            future_days.append(current)
            current += timedelta(days=1)

        model = get_model(longitude=longitude, latitude=latitude)

        future_df = pd.DataFrame({'ds': future_days})
        forecast_future = model.predict(future_df)
        future_consumption = forecast_future['yhat'].sum() * solar_coefficient
        future_production = sum(average_consumption_by_months.get(day.month, 500) for day in future_days)

    total_consumption = int(past_consumption + future_consumption)
    total_production = int(past_production + future_production)

    return {
        "1": total_consumption,
        "2": total_production,
        "3": max(int(total_consumption - total_production), 0),
        "4": max(int(total_production - total_consumption), 0),
    }


def generate_period_ranges(start_date: datetime, end_date: datetime, group_by: str):
    ranges = []
    if group_by == "day":
        current = start_date.date()
        while current <= end_date.date():
            period_start = datetime.combine(current, datetime.min.time())
            period_end = datetime.combine(current, datetime.max.time())
            # Корректируем границы, если они выходят за запрошенный диапазон
            if period_start < start_date:
                period_start = start_date
            if period_end > end_date:
                period_end = end_date
            label = current.strftime("%d.%m.%Y")
            ranges.append((label, period_start, period_end))
            current += timedelta(days=1)
    elif group_by == "month":
        current = start_date.replace(day=1)
        while current <= end_date:
            year = current.year
            month = current.month
            last_day = calendar.monthrange(year, month)[1]
            full_start = current
            full_end = current.replace(day=last_day, hour=23, minute=59, second=59)
            period_start = full_start if full_start >= start_date else start_date
            period_end = full_end if full_end <= end_date else end_date
            label = current.strftime("%m.%Y")
            ranges.append((label, period_start, period_end))
            if month == 12:
                current = current.replace(year=year + 1, month=1, day=1)
            else:
                current = current.replace(month=month + 1, day=1)
    elif group_by == "year":
        # Начинаем с 1 января запрашиваемого года
        current = start_date.replace(month=1, day=1)
        while current <= end_date:
            year = current.year
            full_start = current
            full_end = current.replace(month=12, day=31, hour=23, minute=59, second=59)
            period_start = full_start if full_start >= start_date else start_date
            period_end = full_end if full_end <= end_date else end_date
            label = current.strftime("%Y")
            ranges.append((label, period_start, period_end))
            current = current.replace(year=year + 1, month=1, day=1)
    else:
        raise ValueError("Некорректное значение group_by")
    return ranges


async def predict_report_by_date(
        session: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        group_by: str,
        solar_coefficient: float,
        average_consumption_by_months: dict,
        longitude: float,
        latitude: float
) -> dict:
    now_date = datetime.now().date()

    period_ranges = generate_period_ranges(start_date, end_date, group_by)

    # Разбиваем периоды на прошедшие и будущие (или смешанные)
    past_periods = []
    future_periods = []
    for label, p_start, p_end in period_ranges:
        if p_end.date() <= now_date:
            past_periods.append((label, p_start, p_end))
        elif p_start.date() > now_date:
            future_periods.append((label, p_start, p_end))
        else:
            # Если период пересекается с текущей датой:
            past_periods.append((label, p_start, datetime.combine(now_date, datetime.max.time())))
            future_periods.append((label, datetime.combine(now_date + timedelta(days=1), datetime.min.time()), p_end))

    past_data = {}
    if past_periods:
        past_start = min(p[1] for p in past_periods)
        past_end = max(p[2] for p in past_periods)

        if group_by == "day":
            date_format_sql = "DD.MM.YYYY"
        elif group_by == "month":
            date_format_sql = "MM.YYYY"
        elif group_by == "year":
            date_format_sql = "YYYY"
        # Для группировки одно и то же выражение:
        expr = func.to_char(Energy.created_at, date_format_sql)
        query = select(
            expr.label("period"),
            func.coalesce(func.sum(Energy.value).filter(Energy.type == 1), 0).label("consumption"),
            func.coalesce(func.sum(Energy.value).filter(Energy.type == 2), 0).label("production"),
        ).where(
            Energy.created_at.between(past_start, past_end)
        ).group_by(
            expr
        ).order_by(
            expr
        )
        result = await session.execute(query)
        past_data = {
            period: {
                "1": consumption,
                "2": production,
                "3": max(consumption - production, 0),
                "4": max(production - consumption, 0)
            }
            for period, consumption, production in result.all()
        }

    future_data = {}
    if future_periods:
        model = get_model(longitude, latitude)
        for label, p_start, p_end in future_periods:
            future_days = pd.date_range(start=p_start, end=p_end, freq='D')
            if len(future_days) == 0:
                future_production = 0
                future_consumption = 0
            else:
                future_df = pd.DataFrame({'ds': future_days})
                forecast = model.predict(future_df)
                future_production = forecast['yhat'].sum() * solar_coefficient
                future_consumption = sum(average_consumption_by_months.get(day.month, 500) for day in future_days)
            future_data[label] = {
                "1": future_consumption,
                "2": int(future_production),
                "3": max(future_consumption - int(future_production), 0),
                "4": max(int(future_production) - future_consumption, 0)
            }

    result_dict = {}
    for label, _, _ in period_ranges:
        if label in past_data and label in future_data:
            consumption = past_data[label]["1"] + future_data[label]["1"]
            production = past_data[label]["2"] + future_data[label]["2"]
        elif label in past_data:
            consumption = past_data[label]["1"]
            production = past_data[label]["2"]
        elif label in future_data:
            consumption = future_data[label]["1"]
            production = future_data[label]["2"]
        else:
            consumption = production = 0
        result_dict[label] = {
            "1": consumption,
            "2": production,
            "3": max(consumption - production, 0),
            "4": max(production - consumption, 0)
        }
    return result_dict

# if __name__ == "__main__":
#     future_start_date = "2025-01-01"
#     end_date = "2026-01-01"
#     solar_coefficient = 293.0
#     future_production = 0
#     future_consumption = 0
#     past_consumption = 0
#     past_production = 0
#     average_consumpion = 500
#     future_start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
#     end_date = "2026-01-01".strip("/")
#     end_date = datetime.strptime(end_date, "%Y-%m-%d")
#     if future_start_date <= end_date:
#         future_days = []
#         current = future_start_date
#         while current <= end_date:
#             future_days.append(current)
#             current += timedelta(days=1)
#
#         #model = get_model(longitude=37.13, latitude=55.15)
#
#         future_df = pd.DataFrame({'ds': future_days})
#         print(future_df)
#         forecast_future = model.predict(future_df)
#         print(forecast_future)
#         for idx, row in forecast_future.iterrows():
#             predicted_production = int(row['yhat'] * solar_coefficient)
#             future_production += predicted_production
#             future_consumption += average_consumpion
#
#     total_consumption = past_consumption + future_consumption
#     total_production = past_production + future_production
#
#     rez = {
#         "1": total_consumption,
#         "2": total_production,
#         "3": max(int(total_consumption - total_production), 0),
#         "4": max(int(total_production - total_consumption), 0),
#     }
#     print(rez)
