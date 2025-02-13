import os


from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    host: str = "0.0.0.0"
    port: str = "8000"


    @property
    def db_url(self):
        url = os.getenv("DATABASE_URL", "postgresql://postgres:bvLdusGmHleiyfhjsgGnPzMyTTGRzWll@postgres.railway.internal:5432/railway")

        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return url

    # return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
    echo: bool = False




settings = Settings()

"""postgres_database: str
postgres_host: str
postgres_password: str
postgres_port: str
postgres_username: str"""

#dotenv.load_dotenv()