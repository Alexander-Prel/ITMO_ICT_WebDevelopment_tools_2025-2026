# Код эндпоинтов

Финальная версия кода. Пути указаны от папки `Lr1`.

## `app/main.py`

```python
from fastapi import FastAPI

from app.api.routes import auth, books, exchange_requests, genres, library_items, users
from app.core.config import settings


app = FastAPI(title=settings.app_name)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "BookCrossing API is running"}


# Роутеры объединяются в одно API; их prefix задаёт начальную часть адреса.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(genres.router)
app.include_router(books.router)
app.include_router(library_items.router)
app.include_router(exchange_requests.router)
```

## `app/api/routes/auth.py`

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, MessageResponse, RegisterRequest
from app.services.auth_service import AuthService
from app.services.deps import get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


# response_model оставляет только публичные поля, даже если сервис вернул ORM-пользователя с хэшем.
@router.post("/register", response_model=LoginResponse)
def register(data: RegisterRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    return AuthService.register(session, data)


# Вход принимает JSON, а не форму OAuth2: Swagger Authorize используется уже с готовым токеном.
@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    return AuthService.login(session, data)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return AuthService.change_password(session, current_user, data)
```

## `app/api/routes/books.py`

```python
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.session import get_session
from app.models import Book, User
from app.schemas.auth import MessageResponse
from app.schemas.books import BookCreate, BookRead, BookUpdate
from app.services.book_service import BookService
from app.services.deps import get_current_user


router = APIRouter(prefix="/books", tags=["Books"])


# BookCreate проверяет входной JSON, Depends даёт пользователя и сессию, BookRead описывает ответ.
@router.post("/", response_model=BookRead)
def create_book(
    data: BookCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    # Роутер передаёт запрос сервису; правила создания книги находятся в BookService.
    return BookService.create(session, data, current_user)


@router.get("/", response_model=List[BookRead])
def get_books(
    q: str | None = Query(default=None, description="Поисковая строка: часть названия книги или имени автора. Пробелы по краям игнорируются"),
    session: Session = Depends(get_session),
) -> list[Book]:
    return BookService.get_all(session, q=q)


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, session: Session = Depends(get_session)) -> Book:
    return BookService.get_by_id(session, book_id)


@router.patch("/{book_id}", response_model=BookRead)
def update_book(
    book_id: int,
    data: BookUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    return BookService.update(session, book_id, data, current_user)


@router.delete("/{book_id}", response_model=MessageResponse)
def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return BookService.delete(session, book_id, current_user)


@router.post("/{book_id}/genres/{genre_id}", response_model=BookRead)
def add_genre_to_book(
    book_id: int,
    genre_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    return BookService.add_genre(session, book_id, genre_id, current_user)


@router.delete("/{book_id}/genres/{genre_id}", response_model=BookRead)
def remove_genre_from_book(
    book_id: int,
    genre_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Book:
    return BookService.remove_genre(session, book_id, genre_id, current_user)
```

## `app/api/routes/exchange_requests.py`

```python
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import ExchangeRequest, User
from app.schemas.exchange_requests import ExchangeRequestCreate, ExchangeRequestRead
from app.services.deps import get_current_user
from app.services.exchange_request_service import ExchangeRequestService


router = APIRouter(prefix="/exchange-requests", tags=["Exchange Requests"])


@router.post("/", response_model=ExchangeRequestRead)
def create_exchange_request(
    data: ExchangeRequestCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.create(session, data, current_user)


@router.get("/", response_model=List[ExchangeRequestRead])
def get_exchange_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ExchangeRequest]:
    return ExchangeRequestService.get_all(session, current_user)


@router.get("/me", response_model=List[ExchangeRequestRead])
def get_my_exchange_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ExchangeRequest]:
    return ExchangeRequestService.get_my_requests(session, current_user)


@router.get("/incoming", response_model=List[ExchangeRequestRead])
def get_incoming_exchange_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ExchangeRequest]:
    return ExchangeRequestService.get_incoming_requests(session, current_user)


@router.get("/{request_id}", response_model=ExchangeRequestRead)
def get_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.get_by_id(session, request_id, current_user)


# Для смены статуса есть отдельные действия: клиент не может прислать любой status в JSON.
# Проверки участника, владельца и текущего состояния выполняет сервис.
@router.patch("/{request_id}/accept", response_model=ExchangeRequestRead)
def accept_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.accept(session, request_id, current_user)


@router.patch("/{request_id}/decline", response_model=ExchangeRequestRead)
def decline_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.decline(session, request_id, current_user)


@router.patch("/{request_id}/cancel", response_model=ExchangeRequestRead)
def cancel_exchange_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExchangeRequest:
    return ExchangeRequestService.cancel(session, request_id, current_user)
```

## `app/api/routes/genres.py`

```python
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import Genre
from app.schemas.auth import MessageResponse
from app.schemas.genres import GenreCreate, GenreRead, GenreUpdate
from app.services.genre_service import GenreService


router = APIRouter(prefix="/genres", tags=["Genres"])


@router.post("/", response_model=GenreRead)
def create_genre(data: GenreCreate, session: Session = Depends(get_session)) -> Genre:
    return GenreService.create(session, data)


@router.get("/", response_model=List[GenreRead])
def get_genres(session: Session = Depends(get_session)) -> list[Genre]:
    return GenreService.get_all(session)


@router.get("/{genre_id}", response_model=GenreRead)
def get_genre(genre_id: int, session: Session = Depends(get_session)) -> Genre:
    return GenreService.get_by_id(session, genre_id)


@router.patch("/{genre_id}", response_model=GenreRead)
def update_genre(genre_id: int, data: GenreUpdate, session: Session = Depends(get_session)) -> Genre:
    return GenreService.update(session, genre_id, data)


@router.delete("/{genre_id}", response_model=MessageResponse)
def delete_genre(genre_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    return GenreService.delete(session, genre_id)
```

## `app/api/routes/library_items.py`

```python
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.session import get_session
from app.models import LibraryItem, User
from app.schemas.auth import MessageResponse
from app.schemas.library_items import LibraryItemCreate, LibraryItemRead, LibraryItemUpdate
from app.services.deps import get_current_user
from app.services.library_item_service import LibraryItemService


router = APIRouter(prefix="/library-items", tags=["Library Items"])


@router.post("/", response_model=LibraryItemRead)
def add_book_to_library(
    data: LibraryItemCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> LibraryItem:
    return LibraryItemService.create(session, data, current_user)


@router.get("/", response_model=List[LibraryItemRead])
def get_library_items(session: Session = Depends(get_session)) -> list[LibraryItem]:
    return LibraryItemService.get_all(session)


@router.get("/me", response_model=List[LibraryItemRead])
def get_my_library(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[LibraryItem]:
    return LibraryItemService.get_my_library(session, current_user)


# Query описывает параметры после ? в URL; ограничения limit/offset проверяет FastAPI.
# /me и /search должны находиться раньше общего маршрута /{item_id}.
@router.get("/search", response_model=List[LibraryItemRead])
def search_library_items(
    q: str | None = Query(default=None, description="Поисковая строка: часть названия книги или имени автора. Пробелы по краям игнорируются"),
    city: str | None = Query(default=None, description="Город владельца экземпляра. Пробелы по краям игнорируются"),
    available_only: bool = Query(default=True, description="Показывать только доступные для обмена экземпляры других пользователей"),
    limit: int = Query(default=50, ge=1, le=100, description="Максимальное количество результатов"),
    offset: int = Query(default=0, ge=0, description="Количество результатов, которые нужно пропустить"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[LibraryItem]:
    return LibraryItemService.search(session, current_user, q, city, available_only, limit, offset)


@router.get("/{item_id}", response_model=LibraryItemRead)
def get_library_item(item_id: int, session: Session = Depends(get_session)) -> LibraryItem:
    return LibraryItemService.get_by_id(session, item_id)


@router.patch("/{item_id}", response_model=LibraryItemRead)
def update_library_item(
    item_id: int,
    data: LibraryItemUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> LibraryItem:
    return LibraryItemService.update(session, item_id, data, current_user)


@router.delete("/{item_id}", response_model=MessageResponse)
def delete_library_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return LibraryItemService.delete(session, item_id, current_user)
```

## `app/api/routes/users.py`

```python
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models import User
from app.schemas.auth import MessageResponse
from app.schemas.users import UserRead, UserUpdate
from app.services.deps import get_current_user
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserRead])
def get_users(session: Session = Depends(get_session)) -> list[User]:
    return UserService.get_all(session)


# Фиксированный /me объявлен раньше /{user_id}, иначе слово me может попасть в параметр ID.
@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    return UserService.update(session, current_user, data)


@router.delete("/me", response_model=MessageResponse)
def delete_me(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return UserService.delete(session, current_user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(get_session)) -> User:
    return UserService.get_by_id(session, user_id)
```
