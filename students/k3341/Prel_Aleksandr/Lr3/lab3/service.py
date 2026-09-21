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
