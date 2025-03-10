import calendar
import pickle
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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


cities = [
    [37.62, 55.75, "Moscow"],
    [30.32, 59.93, "Saint Petersburg"],
    [82.93, 55.04, "Novosibirsk"],
    [60.60, 56.84, "Yekaterinburg"],
    [43.93, 56.30, "Nizhny Novgorod"],
    [49.12, 55.79, "Kazan"],
    [61.40, 55.16, "Chelyabinsk"],
    [73.37, 54.99, "Omsk"],
    [50.15, 53.20, "Samara"],
    [39.70, 47.23, "Rostov-on-Don"],
    [55.95, 54.73, "Ufa"],
    [92.87, 56.01, "Krasnoyarsk"],
    [56.25, 58.01, "Perm"],
    [39.20, 51.67, "Voronezh"],
    [44.50, 48.70, "Volgograd"],
    [38.97, 45.05, "Krasnodar"],
    [46.02, 51.53, "Saratov"],
    [65.53, 57.15, "Tyumen"],
    [49.42, 53.52, "Tolyatti"],
    [53.22, 56.85, "Izhevsk"],
    [83.78, 53.35, "Barnaul"],
    [104.28, 52.29, "Irkutsk"],
    [135.07, 48.48, "Khabarovsk"],
    [131.92, 43.12, "Vladivostok"],
    [47.50, 42.98, "Makhachkala"],
    [48.39, 54.32, "Ulyanovsk"],
    [55.10, 51.77, "Orenburg"],
    [86.09, 55.36, "Kemerovo"],
    [87.11, 53.76, "Novokuznetsk"],
    [39.72, 54.62, "Ryazan"],
    [48.04, 46.35, "Astrakhan"],
    [45.00, 53.20, "Penza"],
    [49.66, 58.60, "Kirov"],
    [47.25, 56.13, "Cheboksary"],
    [37.62, 54.20, "Tula"],
    [20.52, 54.72, "Kaliningrad"],
    [34.37, 53.25, "Bryansk"],
    [36.19, 51.73, "Kursk"],
    [39.73, 43.59, "Sochi"],
    [41.97, 45.05, "Stavropol"]
]


# мб города из енва получать, хотя так пизже выглядит
def get_nearest_city(longitude: float, latitude: float, cities_list: list):
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
    global cities
    city_info = get_nearest_city(longitude, latitude, cities)
    if city_info is None:
        raise ValueError("Не удалось определить ближайший город.")
    city_lon, city_lat, city_name = city_info
    model_filename = f'api_v1/energy/ml_models/{city_lon:.2f}-{city_lat:.2f}-{city_name}_prophet_model.pkl'
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
        average_consumpion: int,
        longitude: float,
        latitude: float
) -> dict:
    now_date = datetime.now().date()

    # Разбиваем период на прошлую (до сегодняшнего дня включительно) и будущую (после сегодняшнего дня)
    past_end_date = min(end_date, datetime.combine(now_date, datetime.min.time()))
    future_start_date = max(start_date, datetime.combine(now_date + timedelta(days=1), datetime.min.time()))

    # Получаем  из бд для прошлой части
    query = select(
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 1), 0),
        func.coalesce(func.sum(Energy.value).filter(Energy.type == 2), 0)
    ).where(
        Energy.created_at.between(start_date, past_end_date)
    )
    session.expire_all()
    result = await session.execute(query)
    past_consumption, past_production = result.one()

    # Инициализируем будущие суммы
    future_consumption = 0
    future_production = 0

    # Если есть будущие даты
    if future_start_date <= end_date:
        # Определяем количество будущих дней и список дат
        future_days = []
        current = future_start_date
        while current <= end_date:
            future_days.append(current)
            current += timedelta(days=1)

        model = get_model(longitude=longitude, latitude=latitude)


        future_df = pd.DataFrame({'ds': future_days})
        forecast_future = model.predict(future_df)
        for idx, row in forecast_future.iterrows():
            predicted_production = int(row['yhat'] * solar_coefficient)
            future_production += predicted_production
            future_consumption += average_consumpion

    total_consumption = past_consumption + future_consumption
    total_production = past_production + future_production

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
            label = current.strftime("%d.%m.%Y")
            ranges.append((label, period_start, period_end))
            current += timedelta(days=1)
    elif group_by == "month":
        current = start_date.replace(day=1)
        while current <= end_date:
            year = current.year
            month = current.month
            last_day = calendar.monthrange(year, month)[1]
            period_start = current
            # Устанавливаем конец периода как последний день месяца (с макс. временем)
            period_end = current.replace(day=last_day, hour=23, minute=59, second=59)
            if period_end > end_date:
                period_end = end_date
            label = current.strftime("%m.%Y")
            ranges.append((label, period_start, period_end))
            # Переходим к первому числу следующего месяца
            if month == 12:
                current = current.replace(year=year+1, month=1, day=1)
            else:
                current = current.replace(month=month+1, day=1)
    elif group_by == "year":
        current = start_date.replace(month=1, day=1)
        while current <= end_date:
            year = current.year
            period_start = current
            period_end = current.replace(month=12, day=31, hour=23, minute=59, second=59)
            if period_end > end_date:
                period_end = end_date
            label = current.strftime("%Y")
            ranges.append((label, period_start, period_end))
            current = current.replace(year=year+1, month=1, day=1)
    else:
        raise ValueError("Некорректное значение group_by")
    return ranges

async def predict_report_by_date(
    session: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    group_by: str | None,
    solar_coefficient: float,
    average_consumpion: int,
    longitude: float,
    latitude: float
) -> dict:
    now_date = datetime.now().date()

    period_ranges = generate_period_ranges(start_date, end_date, group_by)


    past_periods = []
    future_periods = []
    for label, p_start, p_end in period_ranges:
        if p_end.date() <= now_date:
            past_periods.append((label, p_start, p_end))
        elif p_start.date() > now_date:
            future_periods.append((label, p_start, p_end))
        else:
            # Если период пересекается с текущей датой, разделяем его:
            past_periods.append((label, p_start, datetime.combine(now_date, datetime.max.time())))
            future_periods.append((label, datetime.combine(now_date + timedelta(days=1), datetime.min.time()), p_end))

    past_data = {}
    if past_periods:
        past_start = min(p[1] for p in past_periods)
        past_end = max(p[2] for p in past_periods)
        # Используем to_char для группировки по нужному формату:
        if group_by == "day":
            date_format_sql = "DD.MM.YYYY"
        elif group_by == "month":
            date_format_sql = "MM.YYYY"
        elif group_by == "year":
            date_format_sql = "YYYY"
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
            days = pd.date_range(start=p_start, end=p_end, freq='D')
            if len(days) == 0:
                forecast_sum = 0
            else:
                future_df = pd.DataFrame({'ds': days})
                forecast = model.predict(future_df)
                forecast_sum = forecast['yhat'].sum() * solar_coefficient
            # Потребление – среднее потребление умноженное на число дней
            consumption_value = average_consumpion * len(days)
            future_data[label] = {
                "1": consumption_value,
                "2": int(forecast_sum),
                "3": max(consumption_value - int(forecast_sum), 0),
                "4": max(int(forecast_sum) - consumption_value, 0)
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

