import os

import dotenv
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """postgres_database: str
    postgres_host: str
    postgres_password: str
    postgres_port: str
    postgres_username: str"""

    @property
    def db_url(self):
        url = os.getenv("DATABASE_URL")
        url = "postgresql+asyncpg"+ url[9::]
        return
       # return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

    echo: bool = True



#dotenv.load_dotenv()
settings = Settings()
