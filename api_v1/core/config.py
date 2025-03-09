import os


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    deploy: str = "local"
    host: str = "0.0.0.0"
    port: str = "8000"

    @property
    def db_url(self):
        ### ____________________________
        deploy: str = "local" # УЛЬТРАКОСТЫЛЬ НАДО ИСПРАВИТЬ
        ### _____________________________
        if deploy == "external":
            url = os.getenv("DATABASE_URL",
                            "postgresql://postgres:bvLdusGmHleiyfhjsgGnPzMyTTGRzWll@postgres.railway.internal:5432/railway")

            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

            return url
        else:
            return "postgresql+asyncpg://postgres:admin@localhost:5432/energy_fastapi"

    # return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
    echo: bool = False
    solar_coefficient: float = 3.5
    average_consumption: float = 500.0
    model_config = SettingsConfigDict(env_file=".env")




settings = Settings()

"""postgres_database: str
postgres_host: str
postgres_password: str
postgres_port: str
postgres_username: str"""

#dotenv.load_dotenv()