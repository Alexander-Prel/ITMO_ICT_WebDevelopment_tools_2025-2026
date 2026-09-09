# Схемы API

Финальная версия кода. Пути указаны от папки `Lr1`.

## `app/schemas/auth.py`

```python
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.users import UserRead


class RegisterRequest(BaseModel):
    name: str = Field(description="Имя пользователя")
    last_name: Optional[str] = Field(default=None, max_length=100, description="Фамилия, необязательное поле")
    email: str
    password: str
    city: Optional[str] = None
    contact_info: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(TokenResponse):
    user: UserRead


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
```

## `app/schemas/books.py`

```python
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.time import MoscowDatetime


class UserInBook(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    city: Optional[str] = None

    class Config:
        from_attributes = True


class GenreInBook(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class LibraryItemInBook(BaseModel):
    id: int
    user_id: int
    condition: str
    status: str
    comment: Optional[str] = None

    class Config:
        from_attributes = True


# Вход содержит данные книги; ID, создателя и дату назначают БД и сервер.
class BookCreate(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    description: Optional[str] = None


# Ответ показывает не только внешние ключи, но и вложенные сведения по связям.
class BookRead(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None
    description: Optional[str] = None
    created_by_id: int
    created_at: MoscowDatetime
    created_by: Optional[UserInBook] = None
    genres: List[GenreInBook] = Field(default_factory=list)
    library_items: List[LibraryItemInBook] = Field(default_factory=list)

    class Config:
        from_attributes = True


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
```

## `app/schemas/exchange_requests.py`

```python
from typing import Optional

from pydantic import BaseModel

from app.schemas.time import MoscowDatetime


class UserInExchangeRequest(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    city: Optional[str] = None

    class Config:
        from_attributes = True


class BookInExchangeRequest(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


class LibraryItemInExchangeRequest(BaseModel):
    id: int
    user_id: int
    condition: str
    status: str
    comment: Optional[str] = None
    book: Optional[BookInExchangeRequest] = None
    user: Optional[UserInExchangeRequest] = None

    class Config:
        from_attributes = True


# Запрашивается ID экземпляра, а не ID общей карточки книги.
class ExchangeRequestCreate(BaseModel):
    requested_item_id: int
    message: Optional[str] = None


class ExchangeRequestRead(BaseModel):
    id: int
    requester_id: int
    requested_item_id: int
    message: Optional[str] = None
    status: str
    created_at: MoscowDatetime
    resolved_at: Optional[MoscowDatetime] = None
    requester: Optional[UserInExchangeRequest] = None
    requested_item: Optional[LibraryItemInExchangeRequest] = None

    class Config:
        from_attributes = True
```

## `app/schemas/genres.py`

```python
from typing import List, Optional

from pydantic import BaseModel, Field


class BookInGenre(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


class GenreCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GenreRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    books: List[BookInGenre] = Field(default_factory=list)

    class Config:
        from_attributes = True


class GenreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
```

## `app/schemas/library_items.py`

```python
from typing import Optional

from pydantic import BaseModel

from app.schemas.time import MoscowDatetime


class UserInLibraryItem(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    city: Optional[str] = None

    class Config:
        from_attributes = True


class BookInLibraryItem(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        from_attributes = True


# Владельца берём из JWT, начальный статус задаёт сервис; клиент выбирает только книгу и её состояние.
class LibraryItemCreate(BaseModel):
    book_id: int
    condition: str = "good"
    comment: Optional[str] = None


class LibraryItemRead(BaseModel):
    id: int
    user_id: int
    book_id: int
    condition: str
    status: str
    comment: Optional[str] = None
    added_at: MoscowDatetime
    user: Optional[UserInLibraryItem] = None
    book: Optional[BookInLibraryItem] = None

    class Config:
        from_attributes = True


class LibraryItemUpdate(BaseModel):
    condition: Optional[str] = None
    status: Optional[str] = None
    comment: Optional[str] = None
```

## `app/schemas/time.py`

```python
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
```

## `app/schemas/users.py`

```python
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.time import MoscowDatetime


# Вложенные схемы короче полных: книга в профиле не содержит тот же профиль снова.
# Это не даёт построить бесконечную цепочку пользователь -> книга -> пользователь.
class BookInUser(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None

    class Config:
        # Pydantic читает атрибуты ORM-объекта, а не требует готовый словарь.
        from_attributes = True


class LibraryItemInUser(BaseModel):
    id: int
    book_id: int
    condition: str
    status: str
    comment: Optional[str] = None
    book: Optional[BookInUser] = None

    class Config:
        from_attributes = True


class ExchangeRequestInUser(BaseModel):
    id: int
    requested_item_id: int
    status: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    name: str
    last_name: Optional[str] = Field(default=None, max_length=100, description="Фамилия, необязательное поле")
    email: str
    password: str
    city: Optional[str] = None
    contact_info: Optional[str] = None


# В выходной схеме нет password и hashed_password: они не должны попасть в ответ API.
class UserRead(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = Field(default=None, description="Фамилия")
    email: str
    city: Optional[str] = None
    contact_info: Optional[str] = None
    bio: Optional[str] = None
    created_at: MoscowDatetime
    # Фабрика создаёт новый пустой список для каждого экземпляра схемы.
    created_books: List[BookInUser] = Field(default_factory=list)
    library_items: List[LibraryItemInUser] = Field(default_factory=list)
    exchange_requests_sent: List[ExchangeRequestInUser] = Field(default_factory=list)

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = Field(default=None, max_length=100, description="Фамилия. Не передавать для сохранения текущей; null очищает поле")
    email: Optional[str] = None
    city: Optional[str] = None
    contact_info: Optional[str] = None
    bio: Optional[str] = None
```
