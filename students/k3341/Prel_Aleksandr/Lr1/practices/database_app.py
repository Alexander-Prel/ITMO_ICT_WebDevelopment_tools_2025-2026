"""Reuse the domain code while keeping each practice in its own PostgreSQL schema."""

from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import Engine, create_engine, text
from sqlmodel import SQLModel, Session

from app.api.routes import auth, books, exchange_requests, genres, library_items, users
from app.core.config import settings
from app.db.session import get_session


def create_practice_app(schema: str, migrations: bool, bind: Engine | None = None) -> FastAPI:
    if schema not in {"practice_1_2", "practice_1_3"}:
        raise ValueError("Unknown practice schema")
    engine = bind or create_engine(settings.database_url, connect_args={"options": f"-csearch_path={schema}"})

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if bind is None:
            with engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        with engine.begin() as connection:
            if migrations:
                config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            else:
                SQLModel.metadata.create_all(connection)
        yield
        if bind is None:
            engine.dispose()

    app = FastAPI(title=f"BookCrossing: {schema}", lifespan=lifespan)

    def session_dependency():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    for router in (auth.router, users.router, books.router, genres.router, library_items.router, exchange_requests.router):
        app.include_router(router)
    return app
