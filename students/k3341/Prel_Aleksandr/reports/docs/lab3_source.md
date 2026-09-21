# Исходный код ЛР3

Пути указаны от папки `Lr3`.

## `lab3/api.py`

```python
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from kombu.exceptions import OperationalError
from pydantic import BaseModel, ConfigDict
from redis.exceptions import RedisError
from sqlmodel import Session, select

from app.db.session import get_session
from app.main import app
from app.models import ParsedPage, User
from app.schemas.time import MoscowDatetime
from app.services.deps import get_current_user
from lab3.celery_app import celery_app, register_task, task_exists, unregister_task
from lab3.schemas import ParseRequest, ParseResult, TaskAccepted, TaskStatus
from lab3.service import ParseServiceError, parse_and_save
from lab3.tasks import parse_page_task


router = APIRouter(prefix="/parser", tags=["Parser — LR3"])


class ParsedPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str
    source_host: str
    book_id: int | None
    fetched_at: MoscowDatetime


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/parse", response_model=ParseResult)
def parse_sync(data: ParseRequest, current_user: User = Depends(get_current_user)) -> ParseResult:
    try:
        return parse_and_save(data.url)
    except ParseServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail="Could not save the parsed page") from error


@router.post("/parse/async", response_model=TaskAccepted, status_code=202)
def parse_async(data: ParseRequest, current_user: User = Depends(get_current_user)) -> TaskAccepted:
    task_id = str(uuid4())
    try:
        register_task(task_id)
        parse_page_task.apply_async(args=[data.url], task_id=task_id, retry=False)
    except (RedisError, OperationalError, OSError) as error:
        try:
            unregister_task(task_id)
        except (RedisError, OSError):
            pass
        raise HTTPException(status_code=503, detail="Task queue is unavailable") from error
    return TaskAccepted(task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: UUID, current_user: User = Depends(get_current_user)) -> TaskStatus:
    task_id = str(task_id)
    try:
        if not task_exists(task_id):
            raise HTTPException(status_code=404, detail="Task not found or expired")
        result = celery_app.AsyncResult(task_id)
        status = result.state
        if status == "SUCCESS":
            return TaskStatus(task_id=task_id, status=status, result=result.result)
        if status == "FAILURE":
            return TaskStatus(task_id=task_id, status=status, error=str(result.result))
        return TaskStatus(task_id=task_id, status=status)
    except (RedisError, OperationalError, OSError) as error:
        raise HTTPException(status_code=503, detail="Task status storage is unavailable") from error


@router.get("/pages", response_model=list[ParsedPageRead])
def get_pages(session: Session = Depends(get_session)) -> list[ParsedPage]:
    return list(session.exec(select(ParsedPage).order_by(ParsedPage.id)).all())


app.include_router(router)
```

## `lab3/celery_app.py`

```python
from functools import lru_cache

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from redis import Redis

from lab2.task2.database import dispose_engine
from lab3.config import settings


celery_app = Celery(
    "bookcrossing_lab3",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["lab3.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=settings.task_ttl,
    timezone="Europe/Moscow",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=3,
    broker_transport_options={"socket_connect_timeout": 3, "socket_timeout": 3},
    redis_socket_connect_timeout=3,
    redis_socket_timeout=3,
    worker_prefetch_multiplier=1,
)


@lru_cache(maxsize=1)
def get_task_registry() -> Redis:
    return Redis.from_url(settings.celery_result_backend, socket_connect_timeout=3, socket_timeout=3)


def register_task(task_id: str) -> None:
    # Celery называет PENDING и новое, и неизвестное задание. Маркер различает их.
    get_task_registry().set(f"lab3:task:{task_id}", "queued", ex=settings.task_ttl)


def unregister_task(task_id: str) -> None:
    get_task_registry().delete(f"lab3:task:{task_id}")


def task_exists(task_id: str) -> bool:
    return bool(get_task_registry().exists(f"lab3:task:{task_id}"))


@worker_process_init.connect
def reset_worker_connections(**kwargs) -> None:
    # После fork процессы Celery открывают собственные подключения.
    dispose_engine()
    get_task_registry.cache_clear()


@worker_process_shutdown.connect
def close_worker_connections(**kwargs) -> None:
    dispose_engine()
```

## `lab3/config.py`

```python
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    parser_url: str = os.getenv("PARSER_URL", "http://parser:8001").rstrip("/")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
    task_ttl: int = 86_400


settings = Settings()
```

## `lab3/parser_service.py`

```python
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
import requests

from lab2.task2.common import download, extract_page
from lab3.schemas import PagePayload, ParseRequest


app = FastAPI(title="BookCrossing parser service — LR3")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/parse", response_model=PagePayload)
def parse_page(data: ParseRequest) -> PagePayload:
    try:
        return PagePayload.model_validate(asdict(extract_page(data.url, download(data.url))))
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(status_code=502, detail="Could not download or parse the source page") from error
```

## `lab3/schemas.py`

```python
import unicodedata
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALLOWED_HOSTS = {"books.toscrape.com", "quotes.toscrape.com"}


def validate_parser_url(url: str) -> str:
    # Проверяем до urlsplit: он удаляет часть управляющих символов.
    if any(char.isspace() or unicodedata.category(char) in {"Cc", "Cf"} for char in url):
        raise ValueError("URL must not contain spaces or control characters")
    if "#" in url or "\\" in url:
        raise ValueError("URL must not contain a fragment or backslashes")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as error:
        raise ValueError("Invalid URL") from error
    if parts.scheme not in {"http", "https"} or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only books.toscrape.com and quotes.toscrape.com HTTP(S) URLs are allowed")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URL must not contain credentials")
    if port is not None and port != (443 if parts.scheme == "https" else 80):
        raise ValueError("Only the standard port for the URL scheme is allowed")
    return url


class ParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)

    _validate_url = field_validator("url")(validate_parser_url)


class PagePayload(ParseRequest):
    title: str = Field(min_length=1)
    source_host: str
    book_title: str | None = None

    @model_validator(mode="after")
    def check_source_host(self):
        if self.source_host != urlsplit(self.url).hostname:
            raise ValueError("source_host must match URL hostname")
        return self


class ParseResult(BaseModel):
    url: str
    ok: bool = True
    title: str
    page_id: int
    book_id: int | None = None
    error: str | None = None


class TaskAccepted(BaseModel):
    task_id: str
    status: str = "PENDING"


class TaskStatus(TaskAccepted):
    result: ParseResult | None = None
    error: str | None = None
```

## `lab3/service.py`

```python
from dataclasses import asdict

import requests
from sqlalchemy.exc import SQLAlchemyError

from lab2.task2.common import PageData
from lab2.task2.database import save_page
from lab3.config import settings
from lab3.schemas import PagePayload, ParseRequest, ParseResult


class ParseServiceError(RuntimeError):
    """Ошибка обращения к отдельному сервису или его ответа."""


def parse_and_save(url: str) -> ParseResult:
    request = ParseRequest(url=url)
    try:
        response = requests.post(
            f"{settings.parser_url}/parse",
            json=request.model_dump(),
            timeout=(5, 30),
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise ParseServiceError(f"Parser service returned HTTP {response.status_code}")
        page = PagePayload.model_validate(response.json())
        if page.url != request.url:
            raise ParseServiceError("Parser service returned a different source URL")
    except (requests.RequestException, ValueError) as error:
        raise ParseServiceError("Parser service is unavailable or returned invalid data") from error

    try:
        outcome = save_page(PageData(**page.model_dump()))
    except SQLAlchemyError as error:
        # Не раскрываем детали подключения к БД в ответе API или результате задачи.
        raise RuntimeError("Could not save the parsed page") from error
    return ParseResult.model_validate(asdict(outcome))
```

## `lab3/tasks.py`

```python
from lab3.celery_app import celery_app
from lab3.service import parse_and_save


@celery_app.task(name="lab3.parse_page")
def parse_page_task(url: str) -> dict:
    # Не перехватываем исключение: Celery пометит задачу как FAILURE.
    return parse_and_save(url).model_dump(mode="json")
```

## `Dockerfile.api`

```text
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/Lr1:/app/Lr2:/app/Lr3
WORKDIR /app

# Relative requirements include the dependencies of the preceding labs.
COPY Lr1/requirements.txt ./Lr1/requirements.txt
COPY Lr2/requirements.txt ./Lr2/requirements.txt
COPY Lr3/requirements.txt ./Lr3/requirements.txt
RUN pip install --no-cache-dir -r Lr3/requirements.txt

COPY Lr1/app ./Lr1/app
COPY Lr1/migrations ./Lr1/migrations
COPY Lr1/alembic.ini ./Lr1/alembic.ini
COPY Lr2/lab2/__init__.py ./Lr2/lab2/__init__.py
COPY Lr2/lab2/common.py ./Lr2/lab2/common.py
COPY Lr2/lab2/task2 ./Lr2/lab2/task2
COPY Lr3/lab3 ./Lr3/lab3

RUN useradd --create-home appuser
USER appuser
WORKDIR /app/Lr1
CMD ["uvicorn", "lab3.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## `Dockerfile.parser`

```text
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/Lr2:/app/Lr3
WORKDIR /app
COPY Lr3/parser-requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# The HTTP parser has HTML utilities, but no database code or credentials.
COPY Lr2/lab2/__init__.py ./Lr2/lab2/__init__.py
COPY Lr2/lab2/task2/__init__.py ./Lr2/lab2/task2/__init__.py
COPY Lr2/lab2/task2/common.py ./Lr2/lab2/task2/common.py
COPY Lr3/lab3/__init__.py Lr3/lab3/config.py Lr3/lab3/schemas.py Lr3/lab3/parser_service.py ./Lr3/lab3/

RUN useradd --create-home appuser
USER appuser
CMD ["uvicorn", "lab3.parser_service:app", "--host", "0.0.0.0", "--port", "8001"]
```

## `docker-compose.yml`

```yaml
name: bookcrossing-lab3-submission

x-app: &app
  image: bookcrossing-lab3-api:submission
  build:
    context: ..
    dockerfile: Lr3/Dockerfile.api
  environment: &app-env
    DB_URL: postgresql+psycopg2://bookcrossing:${POSTGRES_PASSWORD}@db:5432/bookcrossing_lab3
    SECRET_KEY: ${SECRET_KEY:?}
    PARSER_URL: http://parser:8001
    CELERY_BROKER_URL: redis://redis:6379/0
    CELERY_RESULT_BACKEND: redis://redis:6379/1
    SQL_ECHO: "false"
    TZ: Europe/Moscow

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: bookcrossing
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?}
      POSTGRES_DB: bookcrossing_lab3
      TZ: Europe/Moscow
    command: ["postgres", "-c", "timezone=Europe/Moscow"]
    ports:
      - "127.0.0.1:${POSTGRES_PORT:-5433}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 3s
      retries: 20
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
    restart: unless-stopped

  parser:
    image: bookcrossing-lab3-parser:submission
    build:
      context: ..
      dockerfile: Lr3/Dockerfile.parser
    ports:
      - "127.0.0.1:${PARSER_PORT:-8004}:8001"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2)"]
      interval: 5s
      timeout: 3s
      retries: 20
    restart: unless-stopped

  # Одна миграция перед API и worker исключает гонку двух Alembic-процессов.
  migrate:
    <<: *app
    command: ["alembic", "upgrade", "head"]
    depends_on:
      db:
        condition: service_healthy

  api:
    <<: *app
    ports:
      - "127.0.0.1:${API_PORT:-8003}:8000"
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
      parser:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
      interval: 5s
      timeout: 3s
      retries: 20
    restart: unless-stopped

  worker:
    <<: *app
    command: ["celery", "-A", "lab3.celery_app:celery_app", "worker", "--loglevel=info", "--concurrency=2", "--hostname=lab3@%h"]
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
      parser:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "celery -A lab3.celery_app:celery_app inspect ping -d lab3@$$HOSTNAME --timeout 3 | grep -q pong"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## `parser-requirements.txt`

```text
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.9.2
requests==2.34.2
beautifulsoup4==4.15.0
```

## `requirements.txt`

```text
-r ../Lr2/requirements.txt
celery[redis]==5.6.3
redis==6.4.0
```

## `compose.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$lab_dir/.env" ]]; then
  echo 'Сначала выполни bash setup.sh из папки Lr3.' >&2
  exit 1
fi

# На macOS Docker Desktop может быть установлен без добавления CLI в PATH.
desktop_bin=/Applications/Docker.app/Contents/Resources/bin
if [[ -d "$desktop_bin" ]]; then export PATH="$desktop_bin:$PATH"; fi
if ! command -v docker >/dev/null 2>&1; then
  echo 'Docker CLI не найден. Установи и запусти Docker Desktop.' >&2
  exit 1
fi
compose_cmd=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  desktop_compose=/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose
  if [[ -x "$desktop_compose" ]]; then compose_cmd=("$desktop_compose");
  else echo 'Docker Compose не найден.' >&2; exit 1; fi
fi
exec "${compose_cmd[@]}" --env-file "$lab_dir/.env" -f "$lab_dir/docker-compose.yml" "$@"
```

## `setup.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$lab_dir/.env" ]]; then
  echo 'Lr3/.env уже существует; настройки сохранены.'
  exit 0
fi
umask 077
python_bin="$lab_dir/../.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin=python3; fi
"$python_bin" - "$lab_dir/.env" <<'PY'
from pathlib import Path
import secrets
import sys

# Режим x не перезапишет уже существующий файл даже при одновременном запуске.
with Path(sys.argv[1]).open("x") as output:
    output.write(f"POSTGRES_PASSWORD={secrets.token_urlsafe(24)}\n")
    output.write(f"SECRET_KEY={secrets.token_urlsafe(48)}\n")
    output.write("API_PORT=8003\nPARSER_PORT=8004\nPOSTGRES_PORT=5433\n")
print("Создан Lr3/.env. Значения секретов не выводятся в терминал.")
PY
```

## `.env.example`

```text
# setup.sh создаёт .env со случайными локальными паролем БД и ключом JWT.
POSTGRES_PASSWORD=replace_with_a_random_password
SECRET_KEY=replace_with_a_random_jwt_secret
API_PORT=8003
PARSER_PORT=8004
POSTGRES_PORT=5433
```

## `.dockerignore` в личной папке

```text
# Only runtime source and dependency files enter the build context.
**
!Lr1/
!Lr1/requirements.txt
!Lr1/alembic.ini
!Lr1/app/
!Lr1/app/**
!Lr1/migrations/
!Lr1/migrations/**
!Lr2/
!Lr2/requirements.txt
!Lr2/lab2/
!Lr2/lab2/__init__.py
!Lr2/lab2/common.py
!Lr2/lab2/task2/
!Lr2/lab2/task2/*.py
!Lr3/
!Lr3/*requirements.txt
!Lr3/Dockerfile*
!Lr3/lab3/
!Lr3/lab3/*.py
**/__pycache__/
**/*.pyc
**/.env
**/.env.*
```
