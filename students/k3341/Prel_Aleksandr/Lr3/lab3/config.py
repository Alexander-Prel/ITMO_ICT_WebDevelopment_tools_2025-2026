import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    parser_url: str = os.getenv("PARSER_URL", "http://parser:8001").rstrip("/")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
    task_ttl: int = 86_400


settings = Settings()
