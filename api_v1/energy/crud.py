import pickle
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api_v1.core.models.Energy import Energy
from api_v1.energy.schemas import EnergyResponse
import prophet


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
    import pandas as pd
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

        # Создаём DataFrame с будущими датами для прогноза

        future_df = pd.DataFrame({'ds': future_days})
        forecast_future = model.predict(future_df)
        # Для каждого будущего дня суммируем прогнозы
        for idx, row in forecast_future.iterrows():
            # Получаем прогнозированное значение irradiance и умножаем на solar_coefficient
            predicted_production = int(row['yhat'] * solar_coefficient)
            future_production += predicted_production
            future_consumption += average_consumpion

    # Общие суммы
    total_consumption = past_consumption + future_consumption
    total_production = past_production + future_production

    return {
        "1": total_consumption,
        "2": total_production,
        "3": max(int(total_consumption - total_production), 0),
        "4": max(int(total_production - total_consumption), 0),
    }

    # Если group_by != None, действуем по принципу get_report_by_date,
    # но для будущих периодов подставляем прогнозные значения.
    # Здесь приведём схожий подход, как в get_report_by_date, с генерацией всех периодов.


async def predict_report_by_date(
        session: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        group_by: str | None,  # Если group_by is None, будем считать сумму как выше
        solar_coefficient: float,
        average_consumpion: int,
        longitude: float,
        latitude: float
) -> dict:
    now_date = datetime.now().date()
    if group_by == "day":
        date_format_sql = "DD.MM.YYYY"
        date_format_py = "%d.%m.%Y"
        period_step = timedelta(days=1)
    elif group_by == "month":
        date_format_sql = "MM.YYYY"
        date_format_py = "%m.%Y"
        period_step = timedelta(days=31)  # плюс минус, хотя мб подправить надо @Д
    elif group_by == "year":
        date_format_sql = "YYYY"
        date_format_py = "%Y"
        period_step = timedelta(days=365)
    else:
        raise ValueError("Некорректное значение group_by")

    if start_date > datetime.combine(now_date, datetime.min.time()):
        existing_periods = {}
    else:
        query = select(
            func.to_char(Energy.created_at, date_format_sql).label("period"),
            func.coalesce(func.sum(Energy.value).filter(Energy.type == 1), 0).label("consumption"),
            func.coalesce(func.sum(Energy.value).filter(Energy.type == 2), 0).label("production"),
        ).where(
            Energy.created_at.between(start_date, datetime.combine(now_date, datetime.min.time()))
        ).group_by(
            func.to_char(Energy.created_at, date_format_sql)
        ).order_by(
            func.to_char(Energy.created_at, date_format_sql)
        )
        result = await session.execute(query)
        existing_periods = {
            period: {"1": consumption,
                     "2": production,
                     "3": max(consumption - production, 0),
                     "4": max(production - consumption, 0)}
            for period, consumption, production in result.all()
        }

        # Генерируем все периоды в запрошенном диапазоне

    def generate_periods(start_date, end_date, period_step, date_format_py):
        periods = []
        current_date = start_date
        while current_date <= end_date:
            periods.append(current_date.strftime(date_format_py))
            current_date += period_step
        return periods

    all_periods = generate_periods(start_date, end_date, period_step, date_format_py)
    # Определяем будущие периоды (те, чья дата > сегодня)
    future_periods = []
    for period in all_periods:
        try:
            period_date = datetime.strptime(period, date_format_py).date()
        except Exception:
            continue
        if period_date > now_date:
            future_periods.append(period)

    # Загружаем модель для ближайшего города, как и ранее
    model = get_model(longitude, latitude)
    future_data = []
    # Здесь для упрощения считаем, что период соответствует одной дате, полученной как начало периода.
    for period in future_periods:
        try:
            period_date = datetime.strptime(period, date_format_py)
        except Exception:
            continue
        future_data.append(period_date)
    import pandas as pd
    if future_data:
        future_df = pd.DataFrame({'ds': future_data})
        forecast_future = model.predict(future_df)
        # Создаем словарь прогнозов: period_str -> прогнозированное значение * solar_coefficient
        forecast_dict = {
            dt.strftime(date_format_py): int(row['yhat'] * solar_coefficient)
            for dt, (_, row) in zip(future_data, forecast_future.iterrows())
        }
    else:
        forecast_dict = {}

    for period in all_periods:
        if period in forecast_dict:
            existing_periods[period] = {
                "1": average_consumpion,
                "2": forecast_dict[period],
                "3": max(int(average_consumpion - forecast_dict[period]), 0),
                "4": max(int(forecast_dict[period] - average_consumpion), 0),
            }
        else:
            if period not in existing_periods:
                existing_periods[period] = {"1": 0, "2": 0, "3": 0, "4": 0}

    return existing_periods
