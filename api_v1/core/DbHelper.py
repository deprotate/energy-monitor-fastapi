from asyncio import current_task

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, async_scoped_session

from .config import settings


class DatabaseHelper:
    def __init__(self, url: str = settings.db_url, echo: bool = False):
        self.engine = create_async_engine(
            url=url,
            echo=echo,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def get_scopped_session(self) -> AsyncSession:
        session = async_scoped_session(
            session_factory=self.session_factory,
            scopefunc=current_task,
        )
        return session()

    async def session_dependency(self) -> AsyncSession:
        async with self.session_factory() as session:
            yield session


db_helper = DatabaseHelper(url=settings.db_url, echo=True)
