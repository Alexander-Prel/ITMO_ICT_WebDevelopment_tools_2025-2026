from functools import lru_cache
import os
import re
import secrets

from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.core.time import utc_now
from app.models import Book, ParsedPage, User
from lab2.task2.common import Outcome, PageData

IMPORT_EMAIL = "bookcrossing-parser@example.invalid"


def schema_name() -> str:

    schema = os.getenv("LAB2_DB_SCHEMA", "public")
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
        raise ValueError("Invalid PostgreSQL schema")
    return schema


@lru_cache(maxsize=1)
def get_engine():


    return create_engine(settings.database_url, connect_args={"options": f"-csearch_path={schema_name()}"})


def async_engine():

    url = make_url(settings.database_url).set(drivername="postgresql+asyncpg")
    return create_async_engine(url, connect_args={"server_settings": {"search_path": schema_name()}})


def dispose_engine() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()


def importer_id(session: Session) -> int:
    user_id = session.execute(select(User.id).where(User.email == IMPORT_EMAIL)).scalar_one_or_none()
    if user_id is None:

        session.execute(insert(User).values(
            name="BookCrossing importer", email=IMPORT_EMAIL,
            hashed_password=hash_password(secrets.token_urlsafe(32)), created_at=utc_now(),
        ).on_conflict_do_nothing(index_elements=[User.email]))
        user_id = session.execute(select(User.id).where(User.email == IMPORT_EMAIL)).scalar_one()
    return user_id


def prepare_database() -> None:


    with Session(get_engine()) as session, session.begin():
        session.execute(select(ParsedPage.id).limit(1))
        importer_id(session)


def save_record(session: Session, data: PageData) -> Outcome:


    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:url, 0))"), {"url": data.url})
    page = session.execute(select(ParsedPage).where(ParsedPage.url == data.url)).scalar_one_or_none()
    if page is None:
        page = ParsedPage(url=data.url, title=data.title, source_host=data.source_host)
        session.add(page)
    page.title = data.title
    page.fetched_at = utc_now()


    if data.book_title and page.book_id is None:
        book = Book(title=data.book_title, author="Not specified by source",
                    description=f"Imported from {data.url}", created_by_id=importer_id(session))
        session.add(book)

        session.flush()
        page.book_id = book.id
    session.flush()
    return Outcome(url=data.url, ok=True, title=page.title, page_id=page.id, book_id=page.book_id)


def save_page(data: PageData) -> Outcome:


    with Session(get_engine()) as session, session.begin():
        return save_record(session, data)
