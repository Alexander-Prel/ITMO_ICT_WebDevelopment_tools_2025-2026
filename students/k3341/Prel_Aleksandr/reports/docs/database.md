# Подключение и миграции

Финальная версия кода. Пути указаны от папки `Lr1`.

## `app/core/config.py`

```python
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "BookCrossing API"
    # Без локальных настроек запуск прекращается: общего пароля и JWT-ключа нет.
    database_url: str = os.environ["DB_URL"]
    secret_key: str = os.environ["SECRET_KEY"]
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    sql_echo: bool = os.getenv("SQL_ECHO", "false").lower() == "true"


settings = Settings()
```

## `app/db/session.py`

```python
from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings


engine = create_engine(settings.database_url, echo=settings.sql_echo)


def init_db() -> None:
    # create_all создаёт отсутствующие таблицы, но не обновляет существующие; в API используем Alembic.
    SQLModel.metadata.create_all(engine)


def get_session():
    # FastAPI получает сессию через yield; после запроса with закроет её даже при ошибке.
    with Session(engine) as session:
        yield session
```

## `alembic.ini`

```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .
path_separator = os
# URL is supplied by migrations/env.py from DB_URL.

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

## `migrations/env.py`

```python
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app.core.config import settings
from app.models import Book, BookGenreLink, ExchangeRequest, Genre, LibraryItem, User  # noqa: F401


config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Practices can supply a connection with an isolated PostgreSQL search_path.
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## `migrations/versions/0001_initial.py`

```python
"""Initial bookcrossing schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("contact_info", sa.String(), nullable=True),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_genres_name"), "genres", ["name"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("isbn", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_isbn"), "books", ["isbn"], unique=True)

    op.create_table(
        "book_genre_links",
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("genre_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"]),
        sa.PrimaryKeyConstraint("book_id", "genre_id"),
    )

    op.create_table(
        "library_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column(
            "condition",
            sa.Enum("new", "good", "worn", "damaged", name="bookcondition"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("available", "reserved", "exchanged", name="libraryitemstatus"),
            nullable=False,
        ),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "exchange_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("requested_item_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "declined",
                "cancelled",
                name="exchangerequeststatus",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requested_item_id"], ["library_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exchange_requests")
    op.drop_table("library_items")
    op.drop_table("book_genre_links")
    op.drop_index(op.f("ix_books_isbn"), table_name="books")
    op.drop_table("books")
    op.drop_index(op.f("ix_genres_name"), table_name="genres")
    op.drop_table("genres")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS exchangerequeststatus")
    op.execute("DROP TYPE IF EXISTS libraryitemstatus")
    op.execute("DROP TYPE IF EXISTS bookcondition")
```

## `migrations/versions/0002_parsed_pages.py`

```python
"""Track parser source pages without changing existing book records."""

from alembic import op
import sqlalchemy as sa

revision = "0002_parsed_pages"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parsed_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_host", sa.String(), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_parsed_pages_url", "parsed_pages", ["url"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_parsed_pages_url", table_name="parsed_pages")
    op.drop_table("parsed_pages")
```

## `migrations/versions/0003_user_last_name.py`

```python
"""Add an optional last name without replacing existing users."""

from alembic import op
import sqlalchemy as sa

revision = "0003_user_last_name"
down_revision = "0002_parsed_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_name")
```

## `migrations/versions/0004_timezone_aware_dates.py`

```python
"""Preserve legacy UTC instants while adding explicit time zones."""

from alembic import op
import sqlalchemy as sa

revision = "0004_timezone_aware_dates"
down_revision = "0003_user_last_name"
branch_labels = None
depends_on = None

DATE_COLUMNS = (
    ("users", "created_at", False),
    ("books", "created_at", False),
    ("library_items", "added_at", False),
    ("exchange_requests", "created_at", False),
    ("exchange_requests", "resolved_at", True),
    ("parsed_pages", "fetched_at", False),
)


def upgrade() -> None:
    for table, column, nullable in DATE_COLUMNS:
        # Старые числа означали UTC: добавляем этот пояс явно, не сдвигая сами события.
        op.alter_column(
            table, column,
            existing_type=sa.DateTime(timezone=False),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    # При откате возвращаем прежние UTC-даты без пояса, независимо от настроек подключения.
    for table, column, nullable in reversed(DATE_COLUMNS):
        op.alter_column(
            table, column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(timezone=False),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
```
