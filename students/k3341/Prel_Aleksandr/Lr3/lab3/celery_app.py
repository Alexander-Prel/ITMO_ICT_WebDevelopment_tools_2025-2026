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
