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
