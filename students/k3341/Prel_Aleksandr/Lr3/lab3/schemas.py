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
