from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings


# Engine управляет подключениями; сессия ниже создаётся отдельно для каждого запроса.
engine = create_engine(settings.database_url, echo=settings.sql_echo)


def init_db() -> None:
    # create_all создаёт отсутствующие таблицы, но не обновляет существующие; в API используем Alembic.
    SQLModel.metadata.create_all(engine)


def get_session():
    # FastAPI получает сессию через yield; после запроса with закроет её даже при ошибке.
    # При закрытии незавершённая транзакция откатывается; успешные изменения commit делает сервис.
    with Session(engine) as session:
        yield session
