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
        url = os.getenv("DATABASE_URL", "postgresql://postgres:bvLdusGmHleiyfhjsgGnPzMyTTGRzWll@postgres.railway.internal:5432/railway")

        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        if "?" not in url:
            url += "?ssl=true"
        else:
            url += "&ssl=true"
        return url

        print("_____________________________\n",
              "_____________________________\n",
              url, "Here is my async url"
              "_____________________________\n",
              "_____________________________\n",)
        return url

    # return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
    #db_url: str = "postgresql+asyncpg://postgres:utehLuQWFgzYMkDkynqqwpqyNHrGdNjr@postgres.railway.internal:5432/railway?sslmode=require"
    echo: bool = True



#dotenv.load_dotenv()
settings = Settings()
