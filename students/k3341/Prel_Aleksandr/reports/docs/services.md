# Бизнес-логика и авторизация

Финальная версия кода. Пути указаны от папки `Lr1`.

## `app/core/security.py`

```python
from datetime import timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.time import utc_now


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Хэш не расшифровывается: библиотека проверяет, соответствует ли ему введённый пароль.
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = utc_now() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    # JWT подписан, но не зашифрован: пароль и другие секреты в его данные не помещаем.
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
```

## `app/services/auth_service.py`

```python
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest


class AuthService:
    @staticmethod
    def register(session: Session, data: RegisterRequest) -> dict:
        # Email используется для входа, поэтому два аккаунта с ним создать нельзя.
        existing_user = session.exec(select(User).where(User.email == data.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        # В базу передаём только хэш пароля; исходный пароль не сохраняется.
        user = User(
            name=data.name,
            last_name=(data.last_name.strip() or None) if data.last_name is not None else None,
            email=data.email,
            city=data.city,
            contact_info=data.contact_info,
            hashed_password=hash_password(data.password),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # sub содержит ID пользователя, чтобы по токену определить автора следующих запросов.
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer", "user": user}

    @staticmethod
    def login(session: Session, data: LoginRequest) -> dict:
        user = session.exec(select(User).where(User.email == data.email)).first()
        # Одинаковая ошибка для неверного email и пароля не подсказывает, существует ли аккаунт.
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer", "user": user}

    @staticmethod
    def change_password(session: Session, user: User, data: ChangePasswordRequest) -> dict:
        # Одного токена недостаточно: для смены пароля нужно подтвердить старый пароль.
        if not verify_password(data.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Old password is incorrect",
            )

        user.hashed_password = hash_password(data.new_password)
        session.add(user)
        # Уже выданные JWT эта операция не отзывает; они действуют до своего срока окончания.
        session.commit()
        return {"message": "Password changed successfully"}
```

## `app/services/book_service.py`

```python
from fastapi import HTTPException, status
from sqlmodel import Session, or_, select

from app.models import Book, Genre, User
from app.schemas.books import BookCreate, BookUpdate
from app.services.permissions import ensure_book_creator, get_book_or_404


class BookService:
    @staticmethod
    def create(session: Session, data: BookCreate, user: User) -> Book:
        # Если ISBN указан, он должен быть уникальным; отсутствие ISBN допускается.
        if data.isbn:
            existing_book = session.exec(select(Book).where(Book.isbn == data.isbn)).first()
            if existing_book:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Book with this ISBN already exists",
                )

        book = Book(
            title=data.title,
            author=data.author,
            isbn=data.isbn,
            description=data.description,
            created_by_id=user.id,
        )
        # add готовит запись, commit сохраняет её, refresh получает из БД ID и остальные поля.
        session.add(book)
        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def get_all(session: Session, q: str | None = None) -> list[Book]:
        q = q.strip() if q else None
        statement = select(Book).order_by(Book.id)
        if q:
            statement = statement.where(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
        return list(session.exec(statement).all())

    @staticmethod
    def get_by_id(session: Session, book_id: int) -> Book:
        return get_book_or_404(session, book_id)

    @staticmethod
    def update(session: Session, book_id: int, data: BookUpdate, user: User) -> Book:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)

        if data.isbn and data.isbn != book.isbn:
            existing_book = session.exec(select(Book).where(Book.isbn == data.isbn)).first()
            if existing_book:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Book with this ISBN already exists",
                )
            book.isbn = data.isbn

        if data.title:
            book.title = data.title
        if data.author:
            book.author = data.author
        if data.description is not None:
            book.description = data.description

        session.add(book)
        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def remove_genre(session: Session, book_id: int, genre_id: int, user: User) -> Book:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)
        genre = session.get(Genre, genre_id)
        if genre is None or genre not in book.genres:
            raise HTTPException(status_code=404, detail="Book genre link not found")
        # Удаляем только связь с жанром, а не сам жанр и не книгу.
        book.genres.remove(genre)
        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def delete(session: Session, book_id: int, user: User) -> dict:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)
        # Карточка общая: её нельзя удалить, пока на неё ссылаются экземпляры пользователей.
        if book.library_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book cannot be deleted while users have it in libraries",
            )

        session.delete(book)
        session.commit()
        return {"message": "Book deleted successfully"}

    @staticmethod
    def add_genre(session: Session, book_id: int, genre_id: int, user: User) -> Book:
        book = get_book_or_404(session, book_id)
        ensure_book_creator(book, user)

        genre = session.get(Genre, genre_id)
        if not genre:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found")

        # Повторное добавление того же жанра не создаёт вторую связь.
        if genre not in book.genres:
            book.genres.append(genre)
            session.add(book)
            session.commit()
            session.refresh(book)
        return book
```

## `app/services/deps.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User


# Отсутствующий токен обработаем сами, чтобы вернуть 401 с понятным сообщением.
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        # Сначала проверяется подпись и срок токена, затем читается ID из поля sub.
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # Действительный токен не должен давать доступ, если аккаунта в базе уже нет.
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User from token was not found",
        )
    return user
```

## `app/services/enums.py`

```python
from enum import Enum

from fastapi import HTTPException, status


def parse_enum(enum_class: type[Enum], value: str, field_name: str):
    try:
        return enum_class(value)
    except ValueError:
        allowed = ", ".join(item.value for item in enum_class)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be one of: {allowed}",
        )
```

## `app/services/exchange_request_service.py`

```python
from fastapi import HTTPException, status
from sqlmodel import Session, or_, select

from app.core.time import utc_now
from app.models import ExchangeRequest, ExchangeRequestStatus, LibraryItem, LibraryItemStatus, User
from app.schemas.exchange_requests import ExchangeRequestCreate
from app.services.permissions import get_library_item_or_404


class ExchangeRequestService:
    @staticmethod
    def create(session: Session, data: ExchangeRequestCreate, user: User) -> ExchangeRequest:
        # Блокировка не даёт одновременно принять обмен и создать заявку на уже занятый экземпляр.
        requested_item = get_library_item_or_404(session, data.requested_item_id, lock=True)

        # Запрашивать можно только чужой экземпляр, который ещё доступен.
        if requested_item.user_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User cannot request own book",
            )
        if requested_item.status != LibraryItemStatus.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book is not available for exchange",
            )

        # Пока решение не принято, у одного читателя не должно быть двух заявок на ту же копию.
        existing_request = session.exec(
            select(ExchangeRequest).where(
                ExchangeRequest.requester_id == user.id,
                ExchangeRequest.requested_item_id == requested_item.id,
                ExchangeRequest.status == ExchangeRequestStatus.pending,
            )
        ).first()
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pending exchange request already exists",
            )

        # Автор берётся из токена: клиент не может отправить заявку от имени другого человека.
        exchange_request = ExchangeRequest(
            requester_id=user.id,
            requested_item_id=requested_item.id,
            message=data.message,
        )
        session.add(exchange_request)
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def get_all(session: Session, user: User) -> list[ExchangeRequest]:
        # Показываем только свои исходящие заявки и входящие на свои экземпляры.
        statement = select(ExchangeRequest).join(LibraryItem).where(
            or_(ExchangeRequest.requester_id == user.id, LibraryItem.user_id == user.id)
        )
        return list(session.exec(statement).all())

    @staticmethod
    def get_my_requests(session: Session, user: User) -> list[ExchangeRequest]:
        return list(
            session.exec(
                select(ExchangeRequest).where(ExchangeRequest.requester_id == user.id)
            ).all()
        )

    @staticmethod
    def get_incoming_requests(session: Session, user: User) -> list[ExchangeRequest]:
        return list(
            session.exec(
                select(ExchangeRequest)
                .join(LibraryItem, ExchangeRequest.requested_item_id == LibraryItem.id)
                .where(LibraryItem.user_id == user.id)
            ).all()
        )

    @staticmethod
    def get_by_id(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = session.get(ExchangeRequest, request_id)
        if not exchange_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange request not found",
            )

        # Знать ID недостаточно: читать заявку могут только её автор и владелец экземпляра.
        owner_id = exchange_request.requested_item.user_id
        if exchange_request.requester_id != user.id and owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only requester or book owner can view this exchange request",
            )
        return exchange_request

    @staticmethod
    def accept(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService._get_for_update(session, request_id, user)
        requested_item = exchange_request.requested_item

        if requested_item.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only book owner can accept exchange request",
            )
        # По заявке можно принять решение только один раз, пока она ожидает ответа.
        if exchange_request.status != ExchangeRequestStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending exchange request can be accepted",
            )

        if requested_item.status != LibraryItemStatus.available:
            raise HTTPException(status_code=400, detail="Book is no longer available")

        # Принятие резервирует копию, но не меняет её владельца и не подтверждает передачу.
        exchange_request.status = ExchangeRequestStatus.accepted
        exchange_request.resolved_at = utc_now()
        requested_item.status = LibraryItemStatus.reserved

        # Один экземпляр нельзя обещать двум людям: остальные ожидающие заявки отклоняем.
        others = session.exec(select(ExchangeRequest).where(
            ExchangeRequest.requested_item_id == requested_item.id,
            ExchangeRequest.id != request_id,
            ExchangeRequest.status == ExchangeRequestStatus.pending,
        )).all()
        for other in others:
            other.status = ExchangeRequestStatus.declined
            other.resolved_at = exchange_request.resolved_at
            session.add(other)

        session.add(requested_item)
        session.add(exchange_request)
        # Решение, резервирование и отклонение остальных заявок сохраняются одной транзакцией.
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def decline(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService._get_for_update(session, request_id, user)
        requested_item = exchange_request.requested_item

        if requested_item.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only book owner can decline exchange request",
            )
        if exchange_request.status != ExchangeRequestStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending exchange request can be declined",
            )

        # Заявка остаётся в истории. Сам экземпляр здесь не резервируем и не удаляем.
        exchange_request.status = ExchangeRequestStatus.declined
        exchange_request.resolved_at = utc_now()

        session.add(exchange_request)
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def cancel(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService._get_for_update(session, request_id, user)
        # Отмена доступна автору заявки, а не владельцу книги; принятую заявку так не отменить.
        if exchange_request.requester_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only requester can cancel exchange request",
            )
        if exchange_request.status != ExchangeRequestStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending exchange request can be cancelled",
            )

        exchange_request.status = ExchangeRequestStatus.cancelled
        exchange_request.resolved_at = utc_now()

        session.add(exchange_request)
        session.commit()
        session.refresh(exchange_request)
        return exchange_request

    @staticmethod
    def _get_for_update(session: Session, request_id: int, user: User) -> ExchangeRequest:
        exchange_request = ExchangeRequestService.get_by_id(session, request_id, user)
        # Заявки на одну копию ждут общую блокировку экземпляра до завершения транзакции.
        get_library_item_or_404(session, exchange_request.requested_item_id, lock=True)
        # Пока мы ждали, другая операция могла изменить заявку: перечитываем её из БД.
        session.refresh(exchange_request)
        return exchange_request
```

## `app/services/genre_service.py`

```python
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Genre
from app.schemas.genres import GenreCreate, GenreUpdate


class GenreService:
    @staticmethod
    def create(session: Session, data: GenreCreate) -> Genre:
        existing_genre = session.exec(select(Genre).where(Genre.name == data.name)).first()
        if existing_genre:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Genre with this name already exists",
            )

        genre = Genre(name=data.name, description=data.description)
        session.add(genre)
        session.commit()
        session.refresh(genre)
        return genre

    @staticmethod
    def get_all(session: Session) -> list[Genre]:
        return list(session.exec(select(Genre)).all())

    @staticmethod
    def get_by_id(session: Session, genre_id: int) -> Genre:
        genre = session.get(Genre, genre_id)
        if not genre:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found")
        return genre

    @staticmethod
    def update(session: Session, genre_id: int, data: GenreUpdate) -> Genre:
        genre = GenreService.get_by_id(session, genre_id)
        if data.name and data.name != genre.name:
            existing_genre = session.exec(select(Genre).where(Genre.name == data.name)).first()
            if existing_genre:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Genre with this name already exists",
                )
            genre.name = data.name
        if data.description is not None:
            genre.description = data.description

        session.add(genre)
        session.commit()
        session.refresh(genre)
        return genre

    @staticmethod
    def delete(session: Session, genre_id: int) -> dict:
        genre = GenreService.get_by_id(session, genre_id)
        session.delete(genre)
        session.commit()
        return {"message": "Genre deleted successfully"}
```

## `app/services/library_item_service.py`

```python
from fastapi import HTTPException, status
from sqlmodel import Session, or_, select

from app.models import Book, BookCondition, ExchangeRequestStatus, LibraryItem, LibraryItemStatus, User
from app.schemas.library_items import LibraryItemCreate, LibraryItemUpdate
from app.services.enums import parse_enum
from app.services.permissions import ensure_library_item_owner, get_book_or_404, get_library_item_or_404


class LibraryItemService:
    @staticmethod
    def create(session: Session, data: LibraryItemCreate, user: User) -> LibraryItem:
        get_book_or_404(session, data.book_id)
        # Карточка книги уже существует; создаём её экземпляр у пользователя из токена.
        item = LibraryItem(
            user_id=user.id,
            book_id=data.book_id,
            condition=parse_enum(BookCondition, data.condition, "condition"),
            status=LibraryItemStatus.available,
            comment=data.comment,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def get_all(session: Session) -> list[LibraryItem]:
        return list(session.exec(select(LibraryItem)).all())

    @staticmethod
    def search(session: Session, user: User, q: str | None, city: str | None,
               available_only: bool, limit: int, offset: int) -> list[LibraryItem]:
        # Случайный пробел при вводе не должен мешать поиску.
        q = q.strip() if q else None
        city = city.strip() if city else None
        # Название берём из карточки книги, город из профиля владельца экземпляра.
        statement = select(LibraryItem).join(Book).join(User, LibraryItem.user_id == User.id)
        # Даже при available_only=False собственные экземпляры не входят в поиск чужих книг.
        statement = statement.where(LibraryItem.user_id != user.id)
        if q:
            statement = statement.where(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
        if city:
            statement = statement.where(User.city.ilike(f"%{city}%"))
        if available_only:
            statement = statement.where(LibraryItem.status == LibraryItemStatus.available)
        return list(session.exec(statement.order_by(LibraryItem.id).offset(offset).limit(limit)).all())

    @staticmethod
    def get_my_library(session: Session, user: User) -> list[LibraryItem]:
        return list(session.exec(select(LibraryItem).where(LibraryItem.user_id == user.id)).all())

    @staticmethod
    def get_by_id(session: Session, item_id: int) -> LibraryItem:
        return get_library_item_or_404(session, item_id)

    @staticmethod
    def update(session: Session, item_id: int, data: LibraryItemUpdate, user: User) -> LibraryItem:
        item = get_library_item_or_404(session, item_id, lock=True)
        ensure_library_item_owner(item, user)

        if data.condition is not None:
            item.condition = parse_enum(BookCondition, data.condition, "condition")
        if data.status is not None:
            new_status = parse_enum(LibraryItemStatus, data.status, "status")
            # Нельзя снова предлагать копию, на которую уже приняли заявку другого читателя.
            if new_status == LibraryItemStatus.available and any(
                request.status == ExchangeRequestStatus.accepted for request in item.exchange_requests
            ):
                raise HTTPException(status_code=409, detail="A copy with an accepted exchange cannot be offered again")
            item.status = new_status
        if data.comment is not None:
            item.comment = data.comment

        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def delete(session: Session, item_id: int, user: User) -> dict:
        item = get_library_item_or_404(session, item_id)
        ensure_library_item_owner(item, user)
        # Сохраняем экземпляр, на который ссылается история заявок, даже завершённых.
        if item.exchange_requests:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Library item cannot be deleted while it has exchange requests",
            )

        session.delete(item)
        session.commit()
        return {"message": "Library item deleted successfully"}
```

## `app/services/permissions.py`

```python
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Book, LibraryItem, User


def get_book_or_404(session: Session, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


def get_library_item_or_404(session: Session, item_id: int, *, lock: bool = False) -> LibraryItem:
    if lock:
        # FOR UPDATE удерживает блокировку строки до commit/rollback.
        # populate_existing обновляет объект в сессии, если его уже читали до ожидания.
        item = session.exec(
            select(LibraryItem).where(LibraryItem.id == item_id)
            .with_for_update().execution_options(populate_existing=True)
        ).first()
    else:
        item = session.get(LibraryItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found",
        )
    return item


def ensure_book_creator(book: Book, user: User) -> None:
    # Создатель общей карточки и владелец конкретного экземпляра могут быть разными людьми.
    if book.created_by_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only book creator can update book metadata",
        )


def ensure_library_item_owner(item: LibraryItem, user: User) -> None:
    if item.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only library item owner can perform this action",
        )
```

## `app/services/user_service.py`

```python
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import User
from app.schemas.users import UserUpdate


class UserService:
    @staticmethod
    def get_all(session: Session) -> list[User]:
        return list(session.exec(select(User)).all())

    @staticmethod
    def get_by_id(session: Session, user_id: int) -> User:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    def update(session: Session, user: User, data: UserUpdate) -> User:
        if data.email and data.email != user.email:
            existing_user = session.exec(select(User).where(User.email == data.email)).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists",
                )
            user.email = data.email

        if data.name:
            user.name = data.name
        # Не передали фамилию: сохраняем прежнюю. Передали null или пробелы: очищаем её.
        if "last_name" in data.model_fields_set:
            user.last_name = (data.last_name.strip() or None) if data.last_name is not None else None
        if data.bio is not None:
            user.bio = data.bio
        if data.city is not None:
            user.city = data.city
        if data.contact_info is not None:
            user.contact_info = data.contact_info

        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def delete(session: Session, user: User) -> dict:
        # Профиль нужен связанным книгам и заявкам: не удаляем вместе с ним чужую историю.
        if user.created_books or user.library_items or user.exchange_requests_sent:
            raise HTTPException(status_code=409, detail="User has related books, library items or exchange requests")
        session.delete(user)
        session.commit()
        return {"message": "User deleted successfully"}
```
