from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, Field

from app.core.time import as_moscow


# Этот тип меняет представление даты в ответе API, а не момент события в базе.
MoscowDatetime = Annotated[
    # Сначала требуем дату с поясом, затем переводим её в московское представление.
    AwareDatetime,
    AfterValidator(as_moscow),
    Field(
        description="Московское время (Europe/Moscow), ISO 8601 с часовым поясом",
        examples=["2026-09-09T15:25:43.489845+03:00"],
    ),
]
