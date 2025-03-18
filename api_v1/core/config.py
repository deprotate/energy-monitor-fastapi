import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ml_training.CycleTraining import training


class Settings(BaseSettings):
    deploy: str = "external"
    host: str = "0.0.0.0"
    port: str = "8000"

    @property
    def db_url(self):
        ### ____________________________
        # УЛЬТРАКОСТЫЛЬ НАДО ИСПРАВИТЬ
        ### _____________________________
        if self.deploy == "external":
            url = os.getenv("DATABASE_URL",
                            "postgresql://postgres:bvLdusGmHleiyfhjsgGnPzMyTTGRzWll@postgres.railway.internal:5432"
                            "/railway")

            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            print(url)
            return url
        else:
            return "postgresql+asyncpg://postgres:admin@localhost:5432/energy_fastapi"

    # return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
    echo: bool = False

    solar_coefficient: float = 293.5
    average_consumption: int = 500
    longitude: float | None = None
    latitude: float | None = None
    additional_city: str | None = None

    @property
    def cities(self):

        cities_list = [
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
            [41.97, 45.05, "Stavropol"],
            [-74.0060, 40.7128, "New York"],
            [-118.2437, 34.0522, "Los Angeles"],
            [-87.6298, 41.8781, "Chicago"],
            [-95.3698, 29.7604, "Houston"],
            [-112.0740, 33.4484, "Phoenix"],
            [-75.1652, 39.9526, "Philadelphia"],
            [-98.4936, 29.4241, "San Antonio"],
            [-117.1611, 32.7157, "San Diego"],
            [-96.7970, 32.7767, "Dallas"],
            [-121.8863, 37.3382, "San Jose"],
            [-0.1278, 51.5074, "London"],
            [2.3522, 48.8566, "Paris"],
            [13.4050, 52.5200, "Berlin"],
            [-3.7038, 40.4168, "Madrid"],
            [12.4964, 41.9028, "Rome"],
            [23.7275, 37.9838, "Athens"],
            [28.9784, 41.0082, "Istanbul"],
            [-9.1393, 38.7223, "Lisbon"],
            [139.6917, 35.6895, "Tokyo"],
            [135.5023, 34.6937, "Osaka"],
            [126.9780, 37.5665, "Seoul"],
            [116.4074, 39.9042, "Beijing"],
            [121.4737, 31.2304, "Shanghai"],
            [114.1095, 22.3964, "Hong Kong"],
            [103.8198, 1.3521, "Singapore"],
            [72.8777, 19.0760, "Mumbai"],
            [77.1025, 28.7041, "Delhi"],
            [77.5946, 12.9716, "Bangalore"],
            [18.4241, -33.9249, "Cape Town"],
            [28.0473, -26.2041, "Johannesburg"],
            [151.2093, -33.8688, "Sydney"],
            [144.9631, -37.8136, "Melbourne"],
            [174.7633, -36.8485, "Auckland"],
            [-79.3832, 43.6532, "Toronto"],
            [-123.1207, 49.2827, "Vancouver"],
            [-99.1332, 19.4326, "Mexico City"],
            [-58.3816, -34.6037, "Buenos Aires"],
            [-46.6333, -23.5505, "São Paulo"],
            [-43.1729, -22.9068, "Rio de Janeiro"],
            [-77.0428, -12.0464, "Lima"],
            [-70.6693, -33.4489, "Santiago"],
            [31.2357, 30.0444, "Cairo"],
            [36.8219, -1.2921, "Nairobi"],
            [55.2708, 25.2048, "Dubai"],
            [7.4474, 46.9480, "Bern"],
            [18.0686, 59.3293, "Stockholm"],
            [10.7522, 59.9139, "Oslo"]
        ]

        if self.longitude and self.latitude:
            cities_list.append(training(longitude=self.longitude, latitude=self.latitude, city=self.additional_city))
        return cities_list

    model_config = SettingsConfigDict(env_file=".env")
    average_consumption_in_jan: int = Field(700, description="Среднее потребление за один день в январе")
    average_consumption_in_feb: int = Field(650, description="Среднее потребление за один день в феврале")
    average_consumption_in_mar: int = Field(600, description="Среднее потребление за один день в марте")
    average_consumption_in_apr: int = Field(550, description="Среднее потребление за один день в апреле")
    average_consumption_in_may: int = Field(500, description="Среднее потребление за один день в мае")
    average_consumption_in_jun: int = Field(450, description="Среднее потребление за один день в июне")
    average_consumption_in_jul: int = Field(450, description="Среднее потребление за один день в июле")
    average_consumption_in_aug: int = Field(450, description="Среднее потребление за один день в августе")
    average_consumption_in_sep: int = Field(500, description="Среднее потребление за один день в сентябре")
    average_consumption_in_oct: int = Field(550, description="Среднее потребление за один день в октябре")
    average_consumption_in_nov: int = Field(600, description="Среднее потребление за один день в ноябре")
    average_consumption_in_dec: int = Field(650, description="Среднее потребление за один день в декабре")

    @property
    def average_consumption_by_months(self) -> dict:
        return {
            1: self.average_consumption_in_jan,
            2: self.average_consumption_in_feb,
            3: self.average_consumption_in_mar,
            4: self.average_consumption_in_apr,
            5: self.average_consumption_in_may,
            6: self.average_consumption_in_jun,
            7: self.average_consumption_in_jul,
            8: self.average_consumption_in_aug,
            9: self.average_consumption_in_sep,
            10: self.average_consumption_in_oct,
            11: self.average_consumption_in_nov,
            12: self.average_consumption_in_dec,
        }


settings = Settings()

"""postgres_database: str
postgres_host: str
postgres_password: str
postgres_port: str
postgres_username: str"""

# dotenv.load_dotenv()
